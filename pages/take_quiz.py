import streamlit as st
from internal.handlers.course import CourseViewHandler
from internal.repository.course import QuizType
from internal.custom_types.quiz import Quiz, MultipleChoiceQuestion, FillInBlankQuestion
from internal.handlers.student_progress import StudentProgressHandler
from internal.handlers.intelligence import IntelligenceHandler
from typing import Tuple, Dict, List, Optional
from datetime import datetime

async def initialize_chat():
    """Initialize chat-related session state variables."""
    # Initialize chat messages if not exists
    if 'quiz_messages' not in st.session_state:
        st.session_state.quiz_messages = {}
    
    # Reset chatbot agent if it exists but is in an error state
    if 'quiz_chatbot_agent' in st.session_state and st.session_state.quiz_chatbot_agent is not None:
        try:
            # Test if the agent is still functional
            test_prompt = "test"
            st.session_state.quiz_chatbot_agent.run(test_prompt)
        except Exception:
            st.session_state.quiz_chatbot_agent = None
            st.session_state.quiz_sys_prompt = None
    
    # Initialize or reset other chat-related state
    if 'quiz_chatbot_agent' not in st.session_state:
        st.session_state.quiz_chatbot_agent = None
    if 'quiz_sys_prompt' not in st.session_state:
        st.session_state.quiz_sys_prompt = None
    if 'active_discussion_question' not in st.session_state:
        st.session_state.active_discussion_question = None

async def display_chat_interface(course_id: int, section_id: str, question_index: int, question_data: dict, user_answer: str, quiz_type: QuizType):
    """Display the chat interface in the sidebar for quiz discussion."""
    with st.sidebar:
        st.title("Question Discussion")
        
        # Initialize messages for this question if not exists
        if question_index not in st.session_state.quiz_messages:
            st.session_state.quiz_messages[question_index] = []

        try:
            # Initialize chatbot if not already done
            if st.session_state.quiz_chatbot_agent is None:
                with st.spinner("Initializing discussion assistant..."):
                    st.session_state.quiz_chatbot_agent, st.session_state.quiz_sys_prompt = await IntelligenceHandler.get_course_chatbot(str(course_id), section_id)

            # Format the initial message about the question
            if quiz_type == QuizType.MULTIPLE_CHOICE:
                selected_answer = question_data["options"][int(user_answer)]
                correct_answer = question_data["options"][question_data["correct_answer"]]
            else:
                selected_answer = user_answer
                correct_answer = question_data["correct_answer"]

            # Send initial question context if this is the first message
            if not st.session_state.quiz_messages[question_index]:
                initial_prompt = f"""
Question: {question_data['question']}
Your Answer: {selected_answer}
Correct Answer: {correct_answer}
Explanation: {question_data['justification']}

Please provide a more detailed explanation of why this answer is correct and help me understand the concept better.
"""
                # Add system message to chat history
                st.session_state.quiz_messages[question_index].append({"role": "user", "content": initial_prompt})
                
                # Get initial response
                with st.spinner("Preparing detailed explanation..."):
                    # Build the complete conversation history
                    conversation = st.session_state.quiz_sys_prompt + "\n\nConversation history:\n"
                    for msg in st.session_state.quiz_messages[question_index]:
                        conversation += f"\n{msg['role'].upper()}: {msg['content']}\n"
                    conversation += f"\nASSISTANT: "
                    
                    response = st.session_state.quiz_chatbot_agent.run(conversation)
                    st.session_state.quiz_messages[question_index].append({"role": "assistant", "content": response})
                    st.rerun()  # Ensure the new messages are displayed

            # Display chat messages
            for message in st.session_state.quiz_messages[question_index]:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # Chat input
            if prompt := st.chat_input("Ask a follow-up question"):
                # Add user message to chat history
                st.session_state.quiz_messages[question_index].append({"role": "user", "content": prompt})
                
                # Display user message
                with st.chat_message("user"):
                    st.markdown(prompt)

                # Get chatbot response
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        # Build the complete conversation history
                        conversation = st.session_state.quiz_sys_prompt + "\n\nConversation history:\n"
                        for msg in st.session_state.quiz_messages[question_index]:
                            conversation += f"\n{msg['role'].upper()}: {msg['content']}\n"
                        conversation += f"\nASSISTANT: "
                        
                        response = st.session_state.quiz_chatbot_agent.run(conversation)
                        st.markdown(response)
                        st.session_state.quiz_messages[question_index].append({"role": "assistant", "content": response})
                        st.rerun()  # Ensure the new messages are displayed

            # Add a close button
            if st.button("Close Discussion", use_container_width=True):
                st.session_state.active_discussion_question = None
                st.rerun()

        except Exception as e:
            st.error(f"Error in chat interface: {str(e)}")
            import traceback
            st.error(f"Traceback: {traceback.format_exc()}")
            # Reset chat state on error
            st.session_state.quiz_chatbot_agent = None
            st.session_state.active_discussion_question = None

def display_question(index: int, question_data: dict, quiz_type: QuizType, show_feedback: bool = False) -> str:
    """Display a single quiz question and return the answer."""
    st.markdown(f"### Question {index+1}")
    
    if quiz_type == QuizType.MULTIPLE_CHOICE:
        question = MultipleChoiceQuestion(
            question=question_data["question"],
            options=question_data["options"],
            correct_answer=question_data["correct_answer"],
            justification=question_data["justification"]
        )
        st.write(question.question)
        answer = st.radio(
            "Choose your answer:",
            options=question.options,
            key=f"q_{index}",
            index=st.session_state.quiz_answers.get(str(index), 0)
        )
        answer_index = question.options.index(answer)
        st.session_state.quiz_answers[str(index)] = answer_index
        
        if show_feedback:
            if answer_index == question.correct_answer:
                st.success("Correct!")
            else:
                st.error(f"Incorrect. The correct answer was: {question.options[question.correct_answer]}")
            
            # Create columns for explanation and discuss button
            col1, col2 = st.columns([5, 1])
            with col1:
                st.info(f"Explanation: {question.justification}")
            with col2:
                if st.button("Discuss", key=f"discuss_{index}"):
                    st.session_state.active_discussion_question = index
                    st.rerun()
            
        return str(answer_index)
        
    else:  # Fill in the blank
        question = FillInBlankQuestion(
            question=question_data["question"],
            correct_answer=question_data["correct_answer"],
            justification=question_data["justification"]
        )
        st.write(question.question)
        answer = st.text_input(
            "Your answer:",
            key=f"q_{index}",
            value=st.session_state.quiz_answers.get(str(index), "")
        )
        st.session_state.quiz_answers[str(index)] = answer
        
        if show_feedback:
            if answer.strip().lower() == question.correct_answer.strip().lower():
                st.success("Correct!")
            else:
                st.error(f"Incorrect. The correct answer was: {question.correct_answer}")
            
            # Create columns for explanation and discuss button
            col1, col2 = st.columns([5, 1])
            with col1:
                st.info(f"Explanation: {question.justification}")
            with col2:
                if st.button("Discuss", key=f"discuss_{index}"):
                    st.session_state.active_discussion_question = index
                    st.rerun()
            
        return answer

async def calculate_quiz_score(quiz_data, answers: Dict[str, str]) -> Tuple[float, List[int]]:
    """Calculate quiz score from answers."""
    if not quiz_data or not quiz_data.questions:
        st.error("No quiz data or questions available for scoring")
        return 0.0, []
        
    correct_answers = 0
    total_questions = len(quiz_data.questions)
    incorrect_questions = []
    
    quiz_type = QuizType(quiz_data.type.value if hasattr(quiz_data.type, 'value') else quiz_data.type)
    
    for i, q in enumerate(quiz_data.questions):
        answer = answers.get(str(i))
        
        if not answer:
            incorrect_questions.append(i)
            continue
            
        if quiz_type == QuizType.MULTIPLE_CHOICE:
            if int(answer) == q["correct_answer"]:
                correct_answers += 1
            else:
                incorrect_questions.append(i)
        else:  # Fill in the blank
            if answer.strip().lower() == q["correct_answer"].strip().lower():
                correct_answers += 1
            else:
                incorrect_questions.append(i)
                
    score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
    return score, incorrect_questions

async def display_quiz(section, show_feedback: bool = False) -> Tuple[float, Dict, List[int]]:
    """Display a quiz for students to take and return their score percentage and answer data."""
    if not section.quiz:
        st.warning("This quiz has not been created yet.")
        return 0, {}, []
        
    try:
        quiz_data = await section.quiz
        if not quiz_data or not quiz_data.questions:
            st.warning("Quiz data could not be loaded or has no questions.")
            return 0, {}, []
            
        quiz_type = QuizType(quiz_data.type.value if hasattr(quiz_data.type, 'value') else quiz_data.type)
        
        if 'quiz_answers' not in st.session_state:
            st.session_state.quiz_answers = {}
            
        answers = {}
        
        for i, question in enumerate(quiz_data.questions):
            answer = display_question(i, question, quiz_type, show_feedback)
            answers[str(i)] = answer
            st.markdown("---")
            
        score, incorrect_questions = await calculate_quiz_score(quiz_data, answers)
        return score, answers, incorrect_questions
            
    except Exception as e:
        st.error(f"Error displaying quiz: {str(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return 0, {}, []

async def save_quiz_attempt(course_id: int, section_id: str, score: float, answers: Dict, incorrect_questions: List[int]) -> bool:
    """Save a quiz attempt to the backend."""
    try:
        quiz_data = {
            "quiz_id": section_id,
            "score": float(score),
            "answers": answers,
            "incorrect_questions": incorrect_questions
        }
        
        await StudentProgressHandler.mark_section_complete(
            course_id,
            section_id,
            is_quiz=True,
            quiz_data=quiz_data
        )
        return True
    except Exception as e:
        st.error(f"Failed to save quiz attempt: {str(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return False

def handle_navigation(sections: List, current_index: int, course_id: int):
    """Handle navigation between sections and course completion."""
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("← Back to Course Index", use_container_width=True):
            st.session_state.current_page = "course_index"
            st.rerun()
    
    with col2:
        if st.session_state.quiz_submitted:
            if current_index < len(sections) - 1:
                if st.button("Continue to Next Section →", use_container_width=True):
                    st.session_state.current_section_index += 1
                    st.session_state.quiz_submitted = False
                    st.session_state.quiz_answers = {}
                    st.session_state.current_page = "take_content"
                    st.rerun()
            else:
                if st.button("Complete Course", use_container_width=True):
                    StudentProgressHandler.mark_course_completed(course_id)
                    st.success("Congratulations! You've completed the course!")
                    st.session_state.current_page = "course_index"
                    st.rerun()

def display_previous_attempts(attempts: List):
    """Display previous quiz attempts."""
    if attempts:
        st.markdown("### Previous Attempts")
        st.markdown("---")
        for i, attempt in enumerate(attempts, 1):
            col1, col2 = st.columns([1, 2])
            with col1:
                st.write(f"**Attempt {i}:**")
            with col2:
                st.write(f"Score: {attempt.score:.1f}%")
                st.write(f"Completed: {attempt.completed_at.strftime('%Y-%m-%d %H:%M')}")
            st.markdown("---")

async def take_quiz_page():
    """Handle quiz-taking functionality."""
    # Initialize chat
    await initialize_chat()
    
    if 'selected_course_id' not in st.session_state or 'current_section_index' not in st.session_state:
        st.warning("Please select a course and section first")
        st.session_state.current_page = "course_index"
        st.rerun()
        return
        
    try:
        # Fetch course data
        course = await CourseViewHandler.get_course(st.session_state.selected_course_id)
        if not course:
            st.error("Course not found")
            st.session_state.current_page = "course_index"
            st.rerun()
            return
            
        # Get current section
        sections = sorted(course.outline_sections, key=lambda x: x.order)
        current_section = sections[st.session_state.current_section_index]
        section_id = str(current_section.id)
        course_id = int(course.id)
        
        # Display section header
        st.header(f"Quiz: {current_section.title}")
        st.write(current_section.description)
        
        # Show previous attempts
        status, attempts = await StudentProgressHandler.get_section_progress(course_id, section_id)
        display_previous_attempts(attempts)
        
        # Initialize quiz state
        if 'quiz_submitted' not in st.session_state:
            st.session_state.quiz_submitted = False
            st.session_state.quiz_score = 0
        
        # Display quiz and get score
        score, answers, incorrect_questions = await display_quiz(
            current_section, 
            show_feedback=st.session_state.quiz_submitted
        )
        
        # Show submit button if not submitted
        if not st.session_state.quiz_submitted:
            if st.button("Submit Quiz"):
                if await save_quiz_attempt(course_id, section_id, score, answers, incorrect_questions):
                    st.session_state.quiz_submitted = True
                    st.session_state.quiz_score = score
                    st.rerun()
        else:
            st.success(f"Quiz completed! Score: {score:.1f}%")
            
            # Display chat interface if a question is selected for discussion
            if st.session_state.active_discussion_question is not None:
                quiz_data = await current_section.quiz
                question_index = st.session_state.active_discussion_question
                question_data = quiz_data.questions[question_index]
                user_answer = answers[str(question_index)]
                quiz_type = QuizType(quiz_data.type.value if hasattr(quiz_data.type, 'value') else quiz_data.type)
                
                await display_chat_interface(
                    course_id,
                    section_id,
                    question_index,
                    question_data,
                    user_answer,
                    quiz_type
                )
        
        # Handle navigation
        handle_navigation(sections, st.session_state.current_section_index, course_id)
                        
    except Exception as e:
        st.error(f"Error in quiz page: {str(e)}") 