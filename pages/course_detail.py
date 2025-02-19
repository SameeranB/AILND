import streamlit as st
from typing import Optional, List

from internal.handlers.course import CourseViewHandler, CourseCreateHandler
from internal.repository.course import LessonType, OutlineSection, QuizType
from internal.utils.storage import StorageHandler
from internal.handlers.intelligence import IntelligenceHandler
from internal.custom_types.quiz import Quiz, MultipleChoiceQuestion, FillInBlankQuestion
from internal.utils.ppt_generator import generate_ppt_from_markdown
from pages.quiz_editor import display_student_preview

def initialize_session_state():
    """Initialize session state variables for course detail page"""
    if 'course_detail_initialized' not in st.session_state:
        st.session_state.course_detail_initialized = True
        st.session_state.editing_mode = False
        st.session_state.editing_section = None
        st.session_state.section_content = {}
        st.session_state.expanded_sections = set()  # Track expanded sections

async def display_quiz_preview(section: OutlineSection):
    """Display a preview of the quiz for students."""
    if not section.quiz:
        st.warning("This quiz has not been created yet.")
        return
        
    try:
        # First get the quiz data from the database model and await it
        quiz_data = await section.quiz
        if not quiz_data:
            st.warning("Quiz data could not be loaded.")
            return
        
        # Create Quiz object with the correct type
        quiz = Quiz(
            type=QuizType(quiz_data.type.value if hasattr(quiz_data.type, 'value') else quiz_data.type),
            questions=[]
        )
        
        # Get the stored questions from the quiz_data's questions field
        stored_questions = quiz_data.questions
        if not stored_questions:
            st.warning("This quiz has no questions yet.")
            return
            
        # Convert each stored question to the appropriate question object
        for q in stored_questions:
            if quiz.type == QuizType.MULTIPLE_CHOICE:
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
                quiz.questions.append(question)
            
        # Display the quiz using our existing preview function
        if quiz.questions:
            display_student_preview(quiz)
        else:
            st.warning("No valid questions found in this quiz.")
        
    except Exception as e:
        st.error(f"Error displaying quiz: {str(e)}")
        # Log the full error for debugging
        import logging
        logging.error(f"Full error in display_quiz_preview: {str(e)}", exc_info=True)

async def course_detail_page(course_id: str):
    initialize_session_state()
    
    # Fetch course details
    course = await CourseViewHandler.get_course(course_id)
    if not course:
        st.error("Course not found")
        return
    
    # Top navigation bar
    col1, col2, col3 = st.columns([1, 6, 1])
    with col1:
        if st.button("← Back"):
            st.session_state.current_page = "content_creator_course_list"
            st.rerun()
    with col2:
        st.title(course.title)
    with col3:
        if st.button("Edit" if not st.session_state.editing_mode else "View"):
            st.session_state.editing_mode = not st.session_state.editing_mode
            st.rerun()
    
    # Course status indicator
    status = "Published" if course.is_active else "Draft"
    st.markdown(f"**Status:** {status}")
    
    if st.session_state.editing_mode:
        # Edit mode
        with st.form("course_details_form"):
            title = st.text_input("Course Title", value=course.title)
            description = st.text_area("Course Description", value=course.description)
            learning_outcomes = st.text_area(
                "Learning Outcomes (One per line)",
                value="\n".join(course.learning_outcomes),
                height=150
            )
            duration = st.number_input(
                "Course Duration (hours)",
                min_value=0.5,
                max_value=100.0,
                value=float(course.duration),
                step=0.5
            )
            target_audience = st.text_area(
                "Target Audience",
                value=course.target_audience
            )
            
            if st.form_submit_button("Save Changes"):
                try:
                    await CourseCreateHandler.update_course(
                        course_id,
                        title=title,
                        description=description,
                        learning_outcomes=learning_outcomes.split("\n"),
                        duration=duration,
                        target_audience=target_audience
                    )
                    st.success("Course details updated successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error updating course: {str(e)}")
    else:
        # View mode
        st.markdown("### Course Description")
        st.write(course.description)
        
        st.markdown("### Learning Outcomes")
        for outcome in course.learning_outcomes:
            st.markdown(f"- {outcome}")
        
        st.markdown(f"**Duration:** {course.duration} hours")
        st.markdown("### Target Audience")
        st.write(course.target_audience)
    
    # Course Outline Section
    st.markdown("---")
    st.markdown("### Course Outline")

    if len(course.outline_sections) == 0:
        st.info("No outline sections created yet.")
        
        # Add generate outline button
        if st.button("🎯 Generate Course Outline"):
            try:
                with st.spinner("Generating course outline..."):
                    sections = await IntelligenceHandler.generate_outline(course_id)
                    # Save the generated sections
                    for section in sections:
                        section.course_id = course_id
                        await section.save()
                st.success("Course outline generated successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error generating course outline: {str(e)}")
        return

    sections = course.outline_sections
    sections = sorted(sections, key=lambda x: x.order)

    for i, section in enumerate(sections):
        with st.expander(f"Section {i+1}: {section.title}", expanded=st.session_state.editing_section == i):
            if st.session_state.editing_mode:
                # Edit section details
                with st.form(f"section_{i}_form"):
                    title = st.text_input("Title", section.title)
                    description = st.text_area("Description", section.description)
                    type_options = list(LessonType)
                    section_type = section.type if isinstance(section.type, LessonType) else LessonType(section.type)
                    lesson_type = st.selectbox(
                        "Type",
                        options=type_options,
                        index=type_options.index(section_type)
                    )
                    duration = st.number_input("Duration (minutes)", value=section.duration)
                    topics = st.text_area("Topics (One per line)", value="\n".join(section.topics))
                    
                    if st.form_submit_button("Save Section"):
                        try:
                            await CourseViewHandler.update_section_details(
                                section=section,
                                title=title,
                                description=description,
                                lesson_type=lesson_type,
                                duration=duration,
                                topics=topics.split("\n")
                            )
                            st.success("Section updated successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating section: {str(e)}")
            else:
                # View section details
                await display_section(section)
            
            # Section content editor
            st.markdown("#### Section Content")
            if section.type == LessonType.QUIZ:
                # Add an expander for the quiz preview
                if st.checkbox("Show Quiz Preview", key=f"preview_{section.id}"):
                    st.markdown("---")
                    await display_quiz_preview(section)
                
                continue
            else:
                if section.content is None:
                    st.error("Content not found for this section.")
                    continue
            
                # Preview tab
                if st.checkbox("Show Preview", key=f"preview_{section.id}"):
                    st.markdown("#### Content Preview")
                    st.markdown(section.content.markdown)

async def display_section(section: OutlineSection):
    """Display a single section in the course outline."""

    col1, col2 = st.columns([6, 2])
    with col1:
        st.write(f"**Title:** {section.title}")
        st.write(f"**Description:** {section.description}")
        st.write(f"**Duration:** {section.duration} minutes")
        st.write("**Topics:**")
        for topic in section.topics:
            st.write(f"- {topic}")
            
        if section.type == LessonType.QUIZ:
            if section.linked_sections:
                st.write("**Tests knowledge from:**")
                for linked_id in section.linked_sections:
                    linked_section = await OutlineSection.get_or_none(id=linked_id)
                    if linked_section:
                        st.write(f"- {linked_section.title}")
    with col2:
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Edit", key=f"edit_{section.id}"):
                st.session_state.current_page = "section_editor"
                st.session_state.selected_course_id = section.course_id
                st.session_state.selected_section_id = str(section.id)
                st.rerun()
        with col2:
            if st.button("Delete", key=f"delete_{section.id}"):
                if await section.delete():
                    st.success("Section deleted successfully!")
                    st.rerun()
        
        # Add PPT generation button for content sections
        if section.type == LessonType.CONTENT and section.content and section.content.markdown:
            if st.button("Generate PPT", key=f"ppt_{section.id}"):
                try:
                    # Generate PPT
                    pptx_bytes = generate_ppt_from_markdown(section.content.markdown)
                    
                    # Create download button
                    st.download_button(
                        label="Download PPT",
                        data=pptx_bytes,
                        file_name=f"{section.title}.pptx",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    )
                except Exception as e:
                    st.error(f"Error generating PPT: {str(e)}")

