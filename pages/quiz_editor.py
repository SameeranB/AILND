import streamlit as st
from typing import Optional, Tuple, List, Dict, Any
from internal.repository.course import Quiz as QuizModel, QuizType
from internal.custom_types.quiz import Quiz, MultipleChoiceQuestion, FillInBlankQuestion, BaseQuestion
from internal.handlers.intelligence import IntelligenceHandler
from internal.handlers.section import SectionViewHandler
import json

def create_multiple_choice_question() -> Optional[MultipleChoiceQuestion]:
    question = st.text_area("Question")
    options = []
    correct_answer = None
    
    col1, col2 = st.columns([3, 1])
    with col1:
        # Add options
        for i in range(4):  # Default 4 options
            option = st.text_input(f"Option {i + 1}")
            if option:
                options.append(option)
    
    with col2:
        if options:
            correct_answer = st.selectbox(
                "Correct Answer",
                options=range(len(options)),
                format_func=lambda x: f"Option {x + 1}"
            )
    
    justification = st.text_area("Justification (Explain why this is the correct answer)")
    
    if question and options and correct_answer is not None and justification:
        question_obj = MultipleChoiceQuestion(
            question=question,
            options=options,
            correct_answer=correct_answer,
            justification=justification
        )
        return question_obj if question_obj.validate() else None
    return None

def create_fill_in_blank_question() -> Optional[FillInBlankQuestion]:
    st.info("Enter your question and use '_____' (five underscores) where you want the blank to appear. Example: 'The capital of France is _____.'")
    question = st.text_area("Question")
    correct_answer = st.text_input("Correct Answer")
    justification = st.text_area("Justification (Explain why this is the correct answer)")
    
    # Show a preview of how the question will look
    if question:
        st.write("Preview:")
        parts = question.split("_____")
        if len(parts) != 2:
            st.error("Your question must contain exactly one '_____' (five underscores) to mark where the blank should appear.")
        else:
            st.write(parts[0] + "________" + parts[1])
            st.write("\nAnswer options will be shown from a pool of all answers in the quiz.")
    
    if question and correct_answer and justification:
        question_obj = FillInBlankQuestion(
            question=question,
            correct_answer=correct_answer,
            justification=justification
        )
        if not question_obj.validate():
            st.error("Please make sure your question includes exactly one '_____' marker for the blank.")
            return None
        return question_obj
    return None

def display_questions(quiz: Quiz):
    for i, q in enumerate(quiz.questions):
        st.subheader(f"Question {i + 1}")
        
        if isinstance(q, MultipleChoiceQuestion):
            st.write("Question:", q.question)
            st.write("Options:")
            for j, option in enumerate(q.options):
                prefix = "✓" if j == q.correct_answer else "•"
                st.write(f"{prefix} {option}")
        else:  # FillInBlankQuestion
            st.write("Question:", q.question)
            st.write("Answer:", q.correct_answer)
            
        st.write("Justification:", q.justification)
        st.divider()

def display_ai_generated_question(question: Dict[str, Any], quiz_type: QuizType) -> Optional[BaseQuestion]:
    """Display an AI generated question as a card and return it if selected."""
    with st.container():
        st.markdown("---")
        col1, col2 = st.columns([5, 1])
        
        with col1:
            st.write("**Question:**", question["question"])
            
            if quiz_type == QuizType.MULTIPLE_CHOICE:
                st.write("**Options:**")
                for i, option in enumerate(question["options"]):
                    prefix = "✓" if i == question["correct_answer"] else "•"
                    st.write(f"{prefix} {option}")
            else:
                st.write("**Answer:**", question["correct_answer"])
                
            with st.expander("See Justification"):
                st.write(question["justification"])
        
        with col2:
            # Create the appropriate question object based on type
            if quiz_type == QuizType.MULTIPLE_CHOICE:
                new_question = MultipleChoiceQuestion(
                    question=question["question"],
                    options=question["options"],
                    correct_answer=question["correct_answer"],
                    justification=question["justification"]
                )
            else:
                new_question = FillInBlankQuestion(
                    question=question["question"],
                    correct_answer=question["correct_answer"],
                    justification=question["justification"]
                )
                
            if st.button("Add", key=f"add_{hash(question['question'])}"):
                return new_question
    
    return None

def display_student_preview(quiz: Quiz):
    """Display the quiz as it will appear to students."""
    st.markdown("""
        <style>
        .quiz-preview {
            border: 1px solid #ddd;
            padding: 20px;
            border-radius: 10px;
            background-color: #f8f9fa;
        }
        .fill-blank-container {
            display: inline;
            margin: 0 10px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Create a pool of all possible answers for fill in the blank questions
    answer_pool = []
    for q in quiz.questions:
        if isinstance(q, FillInBlankQuestion):
            answer_pool.append(q.correct_answer)
    
    with st.container():
        st.markdown('<div class="quiz-preview">', unsafe_allow_html=True)
        for i, q in enumerate(quiz.questions):
            st.subheader(f"Question {i + 1}")
            
            if isinstance(q, MultipleChoiceQuestion):
                st.write(q.question)
                # Single radio group for all options of this question
                selected = st.radio(
                    f"Select answer for question {i + 1}",
                    options=q.options,
                    key=f"preview_mcq_{i}",  # Unique key for each question
                    label_visibility="collapsed"
                )
                
                # Show check answer button for multiple choice
                if st.button("Check Answer", key=f"check_mcq_{i}"):
                    if selected == q.options[q.correct_answer]:
                        st.success("Correct! " + q.justification)
                    else:
                        st.error(f"Incorrect. The correct answer is: {q.options[q.correct_answer]}\n\n{q.justification}")
                
            else:  # FillInBlankQuestion
                # Split question at the blank marker
                parts = q.question.split("_____")
                if len(parts) == 2:
                    # Display the question with the blank
                    st.write(parts[0] + "_____" + parts[1])
                    
                    # Show all possible answers as a radio group
                    selected = st.radio(
                        f"Select answer for question {i + 1}",
                        options=answer_pool,
                        key=f"preview_blank_{i}",
                        label_visibility="collapsed"
                    )
                    
                    # Show check answer button
                    if st.button("Check Answer", key=f"check_blank_{i}"):
                        if selected == q.correct_answer:
                            st.success("Correct! " + q.justification)
                        else:
                            st.error(f"Incorrect. The correct answer is: {q.correct_answer}\n\n{q.justification}")
                else:
                    st.error(f"Question {i + 1} is not properly formatted. Please contact your instructor.")
            
            st.markdown("---")
        st.markdown('</div>', unsafe_allow_html=True)

def manage_quiz_questions(quiz: Quiz):
    """Display and manage current quiz questions."""
    questions_to_delete = []  # Track questions to delete
    
    for i, q in enumerate(quiz.questions):
        with st.container():
            col1, col2 = st.columns([5, 1])
            
            with col1:
                st.subheader(f"Question {i + 1}")
                st.write("**Question Text:**", q.question)
                
                if isinstance(q, MultipleChoiceQuestion):
                    st.write("**Options:**")
                    for j, option in enumerate(q.options):
                        prefix = "✓" if j == q.correct_answer else "•"
                        st.write(f"{prefix} {option}")
                else:
                    st.write("**Correct Answer:**", q.correct_answer)
                
                with st.expander("See Justification"):
                    st.write(q.justification)
            
            with col2:
                if st.button("Remove", key=f"remove_q_{i}"):
                    questions_to_delete.append(i)
            
            st.markdown("---")
    
    # Process deletions after the loop to avoid index issues
    if questions_to_delete:
        # Delete questions in reverse order to maintain correct indices
        for index in sorted(questions_to_delete, reverse=True):
            quiz.questions.pop(index)
        st.success("Question(s) removed!")
        # No need to call rerun as Streamlit will handle the state update

async def quiz_editor_page(course_id: str, section_id: str):
    st.title("Quiz Editor")
    
    # Initialize session states
    if "quiz" not in st.session_state:
        st.session_state.quiz = Quiz(
            type=QuizType.MULTIPLE_CHOICE,
            questions=[]
        )
        st.session_state.quiz_loaded = False  # Add a flag to track if quiz has been loaded
    
    if "ai_generated_questions" not in st.session_state:
        st.session_state.ai_generated_questions = []
    
    if "show_preview" not in st.session_state:
        st.session_state.show_preview = False
        
    # Get the current section to check if it has an existing quiz
    section_handler = SectionViewHandler()
    try:
        _, section = await section_handler.get_section_with_content(course_id, section_id)
        
        # If section has a quiz and we haven't loaded it yet, load it
        if section.quiz and not st.session_state.quiz_loaded:  # Check the loaded flag instead of questions
            quiz_data = await section.quiz  # Await the quiz relationship
            
            # Convert database quiz to our Quiz object
            st.session_state.quiz = Quiz(
                type=QuizType(quiz_data.type.value if hasattr(quiz_data.type, 'value') else quiz_data.type),
                questions=[]
            )
            
            # Convert stored questions to appropriate objects
            stored_questions = quiz_data.questions
            if isinstance(stored_questions, (list, tuple)):
                for q in stored_questions:
                    if quiz_data.type in [QuizType.MULTIPLE_CHOICE, "multiple_choice"]:
                        question = MultipleChoiceQuestion(
                            question=q["question"],
                            options=q["options"],
                            correct_answer=q["correct_answer"],
                            justification=q["justification"]
                        )
                    else:
                        question = FillInBlankQuestion(
                            question=q["question"],
                            correct_answer=q["correct_answer"],
                            justification=q["justification"]
                        )
                    if question.validate():
                        st.session_state.quiz.questions.append(question)
            
            st.session_state.quiz_loaded = True  # Mark the quiz as loaded
    except ValueError as e:
        st.error(f"Error loading section: {str(e)}")
        return
    except Exception as e:
        st.error(f"Error loading quiz: {str(e)}")
        return
    
    # Quiz type selection
    quiz_type = st.selectbox(
        "Select Quiz Type",
        options=[QuizType.MULTIPLE_CHOICE, QuizType.FILL_IN_THE_BLANK],
        format_func=lambda x: x.value.replace("_", " ").title()
    )
    
    # Update quiz type if changed
    if quiz_type != st.session_state.quiz.type:
        st.session_state.quiz = Quiz(type=quiz_type, questions=[])
        st.session_state.ai_generated_questions = []
        st.rerun()

    # Create tabs for different sections
    editor_tab, preview_tab, manage_tab = st.tabs([
        "📝 Quiz Editor",
        "👀 Student Preview",
        "📋 Question Management"
    ])
    
    with editor_tab:
        # Manual Question Creation Section
        st.header("Create Questions Manually")
        with st.form("new_question"):
            if quiz_type == QuizType.MULTIPLE_CHOICE:
                new_question = create_multiple_choice_question()
            else:
                new_question = create_fill_in_blank_question()
                
            if st.form_submit_button("Add Question"):
                if new_question and new_question.validate():
                    st.session_state.quiz.questions.append(new_question)
                    st.success("Question added successfully!")
                else:
                    st.error("Please fill in all required fields correctly")
        
        # AI Question Generation Section
        st.header("Generate Questions with AI")
        st.write("Generate questions based on the content of linked sections")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            num_questions = st.number_input("Number of questions to generate", min_value=1, max_value=10, value=3)
        
        with col2:
            if st.button("Generate Questions"):
                with st.spinner("Generating questions..."):
                    generated_questions = await IntelligenceHandler.generate_quiz_questions(
                        course_id=course_id,
                        section_id=section_id,
                        quiz_type=quiz_type.value,
                        num_questions=num_questions
                    )
                    
                    if generated_questions:
                        st.session_state.ai_generated_questions = generated_questions
                        st.success(f"Successfully generated {len(generated_questions)} questions!")
                    else:
                        st.error("Failed to generate questions. Please ensure there is content in the linked sections.")
        
        # Display AI Generated Questions
        if st.session_state.ai_generated_questions:
            st.subheader("AI Generated Questions")
            st.write("Review and select questions to add to your quiz:")
            
            for question in st.session_state.ai_generated_questions:
                added_question = display_ai_generated_question(question, quiz_type)
                if added_question:
                    st.session_state.quiz.questions.append(added_question)
                    st.success("Question added to quiz!")
                    st.session_state.ai_generated_questions.remove(question)
                    st.rerun()
    
    with preview_tab:
        st.header("Student Preview")
        st.write("This is how students will see the quiz:")
        if st.session_state.quiz.questions:
            display_student_preview(st.session_state.quiz)
        else:
            st.info("Add some questions to see how the quiz will look to students.")
    
    with manage_tab:
        st.header("Manage Quiz Questions")
        if st.session_state.quiz.questions:
            manage_quiz_questions(st.session_state.quiz)
            
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("Save Quiz"):
                    if st.session_state.quiz.validate():
                        try:
                            # Convert quiz to database format
                            quiz_data = {
                                "type": st.session_state.quiz.type.value,
                                "questions": [q.to_dict() for q in st.session_state.quiz.questions]
                            }
                            
                            # Create or update quiz in database
                            if section.quiz:
                                # Get the actual quiz instance
                                quiz_instance = await section.quiz
                                if quiz_instance:
                                    # Update existing quiz
                                    quiz_instance.type = st.session_state.quiz.type.value  # Use .value here
                                    quiz_instance.questions = quiz_data["questions"]
                                    await quiz_instance.save()
                                else:
                                    # Create new quiz if relation exists but instance doesn't
                                    quiz = await QuizModel.create(
                                        type=st.session_state.quiz.type.value,  # Use .value here
                                        questions=quiz_data["questions"]
                                    )
                                    section.quiz = quiz
                                    await section.save()
                            else:
                                # Create new quiz
                                quiz = await QuizModel.create(
                                    type=st.session_state.quiz.type.value,  # Use .value here
                                    questions=quiz_data["questions"]
                                )
                                # Link quiz to section
                                section.quiz = quiz
                                await section.save()
                            
                            st.success("Quiz saved successfully!")
                        except Exception as e:
                            st.error(f"Error saving quiz: {str(e)}")
                            # Add debug information
                            st.error(f"Quiz type: {st.session_state.quiz.type}")
                            st.error(f"Quiz type value: {st.session_state.quiz.type.value}")
                    else:
                        st.error("Quiz validation failed. Please check all questions are properly formatted.")
            
            with col2:
                if st.button("Clear All Questions"):
                    st.session_state.quiz.questions = []
                    st.session_state.ai_generated_questions = []
                    st.rerun()
        else:
            st.info("No questions in the quiz yet. Add questions using the Quiz Editor tab.")