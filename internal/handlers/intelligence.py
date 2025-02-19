import logging
import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from smolagents import CodeAgent, HfApiModel, ToolCallingAgent, tool, LiteLLMModel

from internal.handlers.course import CourseViewHandler
from internal.intelligence.tools.retriever import RetrieverTool
from internal.utils.storage import StorageHandler

from langchain.docstore.document import Document

from smolagents import Tool

import json
from openai import api_key
from smolagents import ToolCallingAgent
from typing import List, Dict, Any, Tuple
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from internal.repository.course import LessonType, OutlineSection, Course, Content
from internal.handlers.section import SectionViewHandler

logger = logging.getLogger(__name__)

# Get OpenAI API key from environment
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")


class FormatCourseOutlineTool(Tool):
    name = "format_course_outline"
    description = """
    Formats a list of course sections into a structured JSON array. Each section should include:
    - 'title': The title of the section.
    - 'description': A brief description of the section.
    - 'type': The type of content ('quiz' or 'content').
    - 'duration': The duration of the section in minutes.
    - 'topics_to_cover': Topics to be covered in the section.
    - 'linked_sections': For quiz sections, an array of section IDs that this quiz should test knowledge from.
    """
    inputs = {
        "sections": {
            "type": "array",
            "description": "A list of dictionaries, each representing a course section with the keys: 'title', 'description', 'type', 'duration', 'topics_to_cover', and 'linked_sections' for quiz sections.",
            "items": {
                "type": "object",
                "properties": {
                    "order": {
                        "type": "number",
                        "description": "The order of the section in the course",
                    },
                    "title": {
                        "type": "string",
                        "description": "The title of the section",
                    },
                    "description": {
                        "type": "string",
                        "description": "A brief description of the section",
                    },
                    "type": {
                        "type": "string",
                        "description": "The type of content ('quiz' or 'content')",
                        "enum": ["quiz", "content"],
                    },
                    "duration": {
                        "type": "number",
                        "description": "The duration of the section in minutes",
                    },
                    "topics_to_cover": {
                        "type": "array",
                        "description": "Topics to be covered in the section.",
                        "items": {"type": "string"},
                    },
                    "linked_sections": {
                        "type": "array",
                        "description": "For quiz sections, an array of section order IDs that this quiz should test knowledge from.",
                        "items": {"type": "number"},
                    },
                },
                "required": [
                    "order",
                    "title",
                    "description",
                    "type",
                    "duration",
                    "topics_to_cover",
                    "linked_sections",
                ],
            },
        }
    }
    output_type = "array"

    def forward(self, sections: list) -> list:
        """
        Args:
            sections (list): A list of dictionaries, each containing:
                - 'title' (str): The title of the section.
                - 'description' (str): A brief description of the section.
                - 'type' (str): The type of content ('quiz' or 'content').
                - 'duration' (str): The duration of the section.
                - 'topics_to_cover' (str): Topics to be covered in the section.
                - 'linked_sections' (list): For quiz sections, array of section IDs to test.

        Returns:
            list: A list of formatted sections in the specified JSON structure.
        """
        formatted_sections = []
        for section in sections:
            formatted_section = {
                "order": section.get("order", 0),
                "title": section.get("title", ""),
                "description": section.get("description", ""),
                "type": section.get("type", "content"),
                "duration": section.get("duration", ""),
                "topics_to_cover": section.get("topics_to_cover", ""),
                "linked_sections": section.get("linked_sections", []) if section.get("type") == "quiz" else [],
            }
            formatted_sections.append(formatted_section)
        return formatted_sections


class QuestionGeneratorTool(Tool):
    name = "question_generator"
    description = """
    Generates quiz questions based on course content. You can generate both multiple choice and fill-in-the-blank questions.
    Each question should test understanding of key concepts and include a justification for the correct answer.
    """
    inputs = {
        "quiz_type": {
            "type": "string",
            "description": "The type of questions to generate ('multiple_choice' or 'fill_in_the_blank')",
            "enum": ["multiple_choice", "fill_in_the_blank"]
        },
        "num_questions": {
            "type": "number",
            "description": "Number of questions to generate"
        },
        "content": {
            "type": "string",
            "description": "The course content to base questions on"
        }
    }
    output_type = "array"

    def forward(self, quiz_type: str, num_questions: int, content: str) -> list:
        system_prompt = """You are an expert quiz question generator. Generate {num_questions} {quiz_type} questions based on the provided content.

For multiple choice questions, follow this format:
{
    "question": "Question text",
    "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
    "correct_answer": 0,  # Index of correct option
    "justification": "Explanation of why this is correct"
}

For fill in the blank questions, follow this format:
{
    "question": "Question text with _____ for the blank",
    "correct_answer": "The correct word or phrase",
    "justification": "Explanation of why this is correct"
}

Ensure questions:
1. Test understanding, not just memorization
2. Are clear and unambiguous
3. Have detailed justifications
4. For multiple choice: all options are plausible
5. For fill in blank: blank placement is meaningful"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Content to base questions on:\n\n{content}\n\nGenerate {num_questions} {quiz_type} questions."}
        ]

        response = self.llm.create(
            messages=messages,
            response_format={ "type": "json" },
            temperature=0.7
        )

        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            logger.error("Failed to parse AI response as JSON")
            return []


class IntelligenceHandler:
    @staticmethod
    async def generate_outline(course_id: str) -> List[OutlineSection]:
        course = await CourseViewHandler.get_course(course_id)

        learning_outcomes = "\n".join(course.learning_outcomes)
        target_audience = course.target_audience
        duration = course.duration

        retriever_tool = await IntelligenceHandler.get_docs_retrieval_tool(course_id)

        prompt = f"""
        You are a course outline generator. Your task is to generate a course outline based on the provided information.
        You must return ONLY a JSON array containing the course sections, with no additional text or explanation.
        Each section in the array must follow this exact format:
        {{
            "order": number (section order),
            "title": string,
            "description": string,
            "type": "content" or "quiz",
            "duration": number (in minutes),
            "topics_to_cover": array of strings,
            "linked_sections": array of numbers (for quiz sections only, references the order numbers of content sections this quiz should test)
        }}
        ENSURE that the JSON array is the only output in the response. No other text should be present.

        You may call the `format_course_outline` tool to confirm the output is in the correct format.

        The total duration of all sections must sum to {duration} hours.
        
        Outline Creation Guidelines:
        - The outline must have well placed quizzes to test the students' knowledge after they have learned a new concept.
        - Each quiz should test knowledge from the 1-2 content sections that precede it.
        - Each quiz's linked_sections should contain the order numbers of the content sections it is testing.
        - Each test should not cover more than 2 topics.
        - The time allocated for each section should be proportional to the complexity and importance of the topic in relation to the provided learning outcomes.
        
        Expected Learning Outcomes:
        {learning_outcomes}
        
        Target Audience:
        {target_audience}
        
        Course Duration: {duration} hours
        """

        model = LiteLLMModel(
            model_id="openai/gpt-4o",
            api_key=OPENAI_API_KEY,
        )

        agent = ToolCallingAgent(
            tools=[retriever_tool, FormatCourseOutlineTool()],
            model=model,
            max_steps=10,
            verbosity_level=2,
            planning_interval=3,
        )

        try:
            # Run the agent and get the output
            agent_output = agent.run(prompt)

            # If the output is a string (JSON), parse it
            if isinstance(agent_output, str):
                try:
                    agent_output = json.loads(agent_output)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing JSON output: {str(e)}")
                    raise ValueError("Invalid JSON output from agent")

            # Validate and format the output
            if not isinstance(agent_output, list):
                raise ValueError("Expected list output from agent")

            # Convert each section to OutlineSection
            output = []
            for section in agent_output:
                # Ensure topics_to_cover is always a list
                topics = section.get("topics_to_cover", [])
                if isinstance(topics, str):
                    topics = [topics]

                # Convert type string to enum
                section_type = section.get("type", "content")
                try:
                    section_type = LessonType(section_type)
                except ValueError:
                    section_type = LessonType.CONTENT  # Default to content if invalid

                outline_section = OutlineSection(
                    order=int(section.get("order", 0)),
                    title=str(section.get("title", "")),
                    description=str(section.get("description", "")),
                    type=section_type,
                    duration=int(section.get("duration", 0)),
                    topics=topics,
                )

                output.append(outline_section)

            return output

        except Exception as e:
            logger.error(f"Error in agent execution: {str(e)}")
            # Return a minimal valid structure in case of error
            return [
                OutlineSection(
                    order=0,
                    title="Introduction",
                    description="Course introduction and overview",
                    type=LessonType.CONTENT,
                    duration=60,
                    topics=["Course overview"],
                )
            ]

    @staticmethod
    async def generate_section_content(course_id, section_id, content_id) -> str:
        course = await Course.get_or_none(id=course_id)
        if not course:
            raise ValueError(f"Course with ID {course_id} not found")

        section = await OutlineSection.get_or_none(id=section_id)
        if not section:
            raise ValueError(
                f"Section with ID {section_id} not found in course {course_id}"
            )

        content = await Content.get_or_none(id=content_id)
        if not content:
            raise ValueError(
                f"Content with ID {content_id} not found in section {section_id}"
            )

        if section.type == LessonType.QUIZ:
            return "Quiz content editing is not implemented in this version."

        # Context
        course_title = course.title
        target_audience = course.target_audience

        section_title = section.title
        section_description = section.description
        section_duration = section.duration
        section_topics = "\n".join(section.topics)

        existing_content = content.markdown if content else ""

        # Retrieval tool
        retriever_tool = await IntelligenceHandler.get_docs_retrieval_tool(course_id)

        # Word Limit Calculation
        reading_speed = 200  # Words per minute
        word_limit = section_duration * reading_speed

        # Prompt
        prompt = f"""
        You are a skilled educational content creator tasked with writing the section "{section_title}" for the course "{course_title}".
        Your goal is to create **textbook-grade**, comprehensive content that thoroughly teaches the topics to students with no prior knowledge.

        **Target Audience:**
        {target_audience}

        **Section Details:**
        - **Title:** {section_title}
        - **Description:** {section_description}
        - **Duration:** {section_duration} minutes
        - **Topics to Cover:**
        {section_topics}
        
        **Procedure to Follow:**
        1. Design the structure of the section ensuring that each topic is covered and expanded appropriately.
        2. For each section and subsection, query the Retriever Tool to gather relevant information.
        3. Fill the content for a section with detailed explanations, examples, and real-world applications.
        4. Continue with the next section.

        **Instructions:**
        - **Clarity and Coherence**: Ensure that the content is clear, coherent, and logically structured with a narrative flow.
        - **Depth and Detail**: Provide in-depth explanations, definitions, and descriptions for each topic. Assume the reader is learning this for the first time. Expand on the topics sufficiently, this is their primary source of learning this topic.
        - **Educational Approach**: Use clear language, logical progression, and include examples, analogies, and diagrams (described in text) where appropriate to enhance understanding.
        - **Format**:
          - Write in **Markdown** format using appropriate headings (`#`, `##`, `###`), lists, code blocks, and emphasis where needed.
          - Include **tables** or **charts** if they help convey information (describe them in Markdown).
        - **Use of Provided Materials**: When making queries to the Retriever Tool, ensure that your queries are small and focused to get the most relevant information. Feel free to make multiple queries if needed.
        - **Length**: The content **must be {word_limit} words long**. The content should be comprehensive enough to cover all topics thoroughly.
        - **Avoid**:
          - Do not include any external meta-commentary or instructions.
          - Do not mention the prompt or that you are an AI language model.
          - Do not include any other text or explanations in your response other than the content itself.

        Take your time to create high-quality educational content that will engage and educate the students effectively. Make as many queries to the Retriever Tool as needed to gather the necessary information. Take as many steps as needed to complete the task.
        """

        model = LiteLLMModel(
            model_id="openai/gpt-4o-2024-08-06",
            api_key=OPENAI_API_KEY,
        )

        agent = ToolCallingAgent(
            tools=[retriever_tool],
            model=model,
            max_steps=15,
            verbosity_level=2,
            planning_interval=2,
        )

        agent_output = agent.run(prompt)

        return agent_output

    @staticmethod
    async def get_docs_retrieval_tool(course_id: str) -> RetrieverTool:
        """Get a RetrieverTool instance for the given course.
        
        This will either load an existing vector store from disk or create a new one
        if none exists.
        
        Args:
            course_id: The ID of the course to get the retriever for
            
        Returns:
            RetrieverTool instance
        """
        return RetrieverTool.from_course_id(course_id)

    @staticmethod
    async def generate_quiz_questions(
        course_id: str,
        section_id: str,
        quiz_type: str,
        num_questions: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Generate quiz questions using AI based on course content.
        
        Args:
            course_id: The ID of the course
            section_id: The ID of the current section
            quiz_type: Type of questions to generate ('multiple_choice' or 'fill_in_the_blank')
            num_questions: Number of questions to generate (default: 3)
            
        Returns:
            List of generated questions in the appropriate format
        """
        # Get section handler
        section_handler = SectionViewHandler()
        
        try:
            # Get the current section and course
            course, section = await section_handler.get_section_with_content(course_id, section_id)
            
            # Get content from linked sections
            content_texts = []
            section_titles = []
            for linked_section_id in section.linked_sections:
                try:
                    _, linked_section = await section_handler.get_section_with_content(course_id, str(linked_section_id))
                    if linked_section and linked_section.content:
                        content_texts.append(linked_section.content.markdown)
                        section_titles.append(linked_section.title)
                except ValueError:
                    logger.warning(f"Could not find linked section {linked_section_id}")
                    continue
            
            if not content_texts:
                logger.warning("No content found in linked sections")
                return []
                
            # Get retriever tool for additional context
            retriever = await IntelligenceHandler.get_docs_retrieval_tool(course_id)
            
            # Combine all content
            combined_content = "\n\n".join(content_texts)
            
            # Create the prompt
            prompt = f"""
            You are an expert quiz question generator for an educational platform. Your task is to create {num_questions} {quiz_type} questions
            based on the content from the following sections:
            {", ".join(section_titles)}

            The questions should test the student's understanding of the key concepts covered in these sections.
            You must return ONLY a JSON array containing the questions, with no additional text or explanation.

            For multiple choice questions, each question in the array must follow this exact format:
            {{
                "question": "Clear and specific question text",
                "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
                "correct_answer": 0,  # Index of the correct option (0-3)
                "justification": "Detailed explanation of why this is the correct answer"
            }}

            For fill in the blank questions, each question must follow this exact format:
            {{
                "question": "Question text with _____ where the blank should be",
                "correct_answer": "The correct word or phrase",
                "justification": "Detailed explanation of why this is the correct answer"
            }}

            Question Creation Guidelines:
            1. Questions should test understanding, not just memorization
            2. All questions must be clear and unambiguous
            3. Include detailed justifications that explain the concept
            4. For multiple choice:
               - All options should be plausible
               - Avoid obvious wrong answers
               - Options should be of similar length
            5. For fill in blank:
               - Blank placement should be meaningful
               - The answer should be specific and unambiguous
               - Avoid blanks that could have multiple valid answers

            Here is the content to base the questions on:

            {combined_content}

            You MUST return ONLY a JSON array containing the questions, with no additional text or explanation. No need for 'Final answer' or anything like that.
            """

            # Create question generator tool with appropriate model
            model = LiteLLMModel(
                model_id="openai/gpt-4o-2024-08-06",
                api_key=OPENAI_API_KEY,
            )

            agent = ToolCallingAgent(
                tools=[retriever],
                model=model,
                max_steps=5,
                verbosity_level=2,
                planning_interval=2,
            )

            try:
                # Run the agent and get the output
                agent_output = agent.run(prompt)

                # If the output is a string (JSON), parse it
                if isinstance(agent_output, str):
                    try:
                        questions = json.loads(agent_output)
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing JSON output: {str(e)}")
                        return []

                # Validate the output format
                if not isinstance(questions, list):
                    logger.error("Expected list output from agent")
                    return []

                # Validate each question
                valid_questions = []
                for q in questions:
                    if quiz_type == "multiple_choice":
                        if all(key in q for key in ["question", "options", "correct_answer", "justification"]):
                            if isinstance(q["options"], list) and len(q["options"]) >= 2:
                                if 0 <= q["correct_answer"] < len(q["options"]):
                                    valid_questions.append(q)
                    else:  # fill_in_the_blank
                        if all(key in q for key in ["question", "correct_answer", "justification"]):
                            if "_____" in q["question"]:
                                valid_questions.append(q)

                return valid_questions

            except Exception as e:
                logger.error(f"Error in agent execution: {str(e)}")
                return []
            
        except ValueError as e:
            logger.error(f"Error getting section content: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error generating questions: {str(e)}")
            return []

    @staticmethod
    async def get_course_chatbot(course_id: str, section_id: str) -> Tuple[ToolCallingAgent, str]:
        """Get a chatbot agent for the given course.
        
        Args:
            course_id: The ID of the course
            section_id: The ID of the section
            
        Returns:
            Tuple of (ToolCallingAgent instance configured for chat, system prompt)
        """
        try:
            course = await Course.get_or_none(id=course_id)
            if not course:
                raise ValueError(f"Course with ID {course_id} not found")

            section = await OutlineSection.get_or_none(id=section_id)
            if not section:
                raise ValueError(
                    f"Section with ID {section_id} not found in course {course_id}"
                )

            # Context
            course_title = course.title
            section_title = section.title
            section_description = section.description
            section_duration = section.duration
            section_topics = "\n".join(section.topics) if section.topics else ""

            # Get retriever tool
            retriever_tool = await IntelligenceHandler.get_docs_retrieval_tool(course_id)

            # Create model
            model = LiteLLMModel(
                model_id="openai/gpt-4o",
                api_key=OPENAI_API_KEY,
            )
            
            # Create chatbot agent
            agent = ToolCallingAgent(
                tools=[retriever_tool],
                model=model,
                max_steps=3,
            )

            # Get content from linked sections for quiz sections
            content_text = ""
            linked_sections_info = []
            
            if section.type == LessonType.QUIZ:
                # For quiz sections, get content from linked sections
                if hasattr(section, 'linked_sections') and section.linked_sections:
                    for linked_id in section.linked_sections:
                        try:
                            linked_section = await OutlineSection.get_or_none(id=linked_id)
                            if linked_section:
                                linked_sections_info.append(f"- {linked_section.title}")
                                if linked_section.content_id:
                                    content = await Content.get_or_none(id=linked_section.content_id)
                                    if content and content.markdown:
                                        content_text += f"\n\n### {linked_section.title}\n{content.markdown}"
                        except Exception as e:
                            logger.error(f"Error getting linked section {linked_id}: {str(e)}")
                            continue
            else:
                # For content sections, get their own content
                if section.content_id:
                    try:
                        content = await Content.get_or_none(id=section.content_id)
                        if content and content.markdown:
                            content_text = content.markdown
                    except Exception as e:
                        logger.error(f"Error getting content for section {section_id}: {str(e)}")

            # Build the system prompt
            system_prompt = f"""
            You are a learning assistant for a course. The user will ask you questions about the course content.
            You must answer the questions based on the course content.
            You must return your response in Markdown format.

            Course Title: {course_title}

            Section Title: {section_title}
            Section Description: {section_description}
            Section Duration: {section_duration} minutes
            Section Topics: {section_topics}
            """

            if section.type == LessonType.QUIZ and linked_sections_info:
                system_prompt += "\nThis quiz covers content from the following sections:\n" + "\n".join(linked_sections_info) + "\n"

            if content_text:
                system_prompt += f"\nHere is the relevant content:\n{content_text}\n"
            
            system_prompt += """
            Use the retriever tool to find relevant information and help answer the user's questions.
            Keep your responses educational and engaging.
            Focus on explaining concepts clearly and providing examples when helpful.
            If asked about quiz answers, explain the reasoning behind why an answer is correct or incorrect.

            User Input:
            """

            return agent, system_prompt
            
        except Exception as e:
            logger.error(f"Error creating chatbot: {str(e)}")
            # Create a basic agent with minimal context as fallback
            agent = ToolCallingAgent(
                tools=[retriever_tool],
                model=model,
                max_steps=3
            )
            basic_prompt = f"""
            You are a learning assistant for a course. The user will ask you questions about the course content.
            Use the retriever tool to find relevant information and help answer the user's questions.
            Keep your responses educational and engaging.

            User Input:
            """
            return agent, basic_prompt
