import streamlit as st
from typing import Optional, Dict, Any, List

from internal.handlers.course import CourseCreateHandler
from internal.handlers.intelligence import IntelligenceHandler
from internal.repository.course import LessonType, OutlineSection
from internal.utils.storage import StorageHandler
from pages.content_creator_course_list import content_creator_course_list_page


def initialize_session_state():
    """Initialize all required session state variables"""
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.wizard_step = 1
        st.session_state.course_data = {
            'title': '',
            'description': '',
            'learning_outcomes': '',
            'duration': 1.0,
            'target_audience': '',
            'outline': None
        }
        st.session_state.course_instance = None
        st.session_state.outline_generated = False

async def course_editor_page():
    st.title("Course Editor")
    
    # Initialize session state
    initialize_session_state()
    
    # Debug information
    if st.checkbox("Show Debug Info"):
        st.write("Current Session State:", {
            'wizard_step': st.session_state.wizard_step,
            'course_data': st.session_state.course_data,
            'course_instance': st.session_state.course_instance,
            'outline_generated': st.session_state.outline_generated
        })
    
    # Progress bar
    progress_value = (st.session_state.wizard_step - 1) / 3
    st.progress(progress_value)
    
    # Step 1: Basic Details
    if st.session_state.wizard_step == 1:
        st.header("Step 1: Basic Details")
        
        course_title = st.text_input(
            "Course Title", 
            value=st.session_state.course_data['title']
        )
        course_description = st.text_area(
            "Course Description",
            value=st.session_state.course_data['description']
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("Next", type="primary", use_container_width=True):
                if course_title and course_description:
                    with st.spinner("Creating course..."):
                        # Create the initial course with basic details
                        course = await CourseCreateHandler.init_course(course_title, course_description)
                        if course:
                            st.session_state.course_instance = course
                            st.session_state.course_data.update({
                                'title': course_title,
                                'description': course_description
                            })
                            st.session_state.wizard_step = 2
                            st.rerun()
                else:
                    st.error("Please fill in all required fields")
    
    # Step 2: Learning Outcomes and Details
    elif st.session_state.wizard_step == 2:
        st.header("Step 2: Course Details")
        
        learning_outcomes = st.text_area(
            "Learning Outcomes (One per line)",
            value=st.session_state.course_data.get('learning_outcomes', ''),
            height=150,
            help="Enter each learning outcome on a new line"
        )
        
        uploaded_files = st.file_uploader(
            "Upload Knowledge Graph Documents",
            accept_multiple_files=True,
            help="Upload documents to help generate the course outline"
        )
        
        course_duration = st.number_input(
            "Course Duration (hours)",
            min_value=0.5,
            max_value=100.0,
            value=float(st.session_state.course_data.get('duration', 1.0)),
            step=0.5
        )
        
        target_audience = st.text_area(
            "Target Audience Description",
            value=st.session_state.course_data.get('target_audience', ''),
            help="Describe who this course is intended for"
        )
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Back", use_container_width=True):
                st.session_state.wizard_step = 1
                st.rerun()
        with col2:
            if st.button("Next", type="primary", use_container_width=True):
                if learning_outcomes and target_audience:
                    try:
                        course = st.session_state.course_instance
                        course_id = course.id

                        await CourseCreateHandler.set_course_details(
                            course_id,
                            learning_outcomes,
                            target_audience,
                            course_duration
                        )

                        # Upload knowledge graph documents if any
                        if uploaded_files:
                            StorageHandler().save_files(course_id, files=uploaded_files)

                        st.session_state.course_data.update({
                            'learning_outcomes': learning_outcomes,
                            'uploaded_files': uploaded_files,
                            'duration': course_duration,
                            'target_audience': target_audience
                        })
                        st.session_state.wizard_step = 3
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error updating course: {str(e)}")
                else:
                    st.error("Please fill in all required fields")
    
    # Step 3: Course Outline
    elif st.session_state.wizard_step == 3:
        st.header("Step 3: Course Outline")
        
        if 'outline_generated' not in st.session_state:
            st.session_state.outline_generated = False
        
        if not st.session_state.outline_generated:
            if st.button("Generate Course Outline", type="primary"):
                try:
                    course = st.session_state.course_instance
                    outline: List[OutlineSection] = await IntelligenceHandler.generate_outline(course.id)
                    st.session_state.course_data['outline'] = outline
                    st.session_state.outline_generated = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Error generating outline: {str(e)}")
        
        if st.session_state.outline_generated:
            st.write("Generated Outline (you can edit any section):")
            
            updated_outline = []
            for i, section in enumerate(st.session_state.course_data['outline']):
                with st.expander(f"Section {i+1}: {section.title}", expanded=True):
                    title = st.text_input("Title", section.title, key=f"title_{i}")
                    description = st.text_area("Description", section.description, key=f"desc_{i}")
                    type_options = list(LessonType)
                    # Convert string type to enum if needed
                    section_type = section.type
                    if isinstance(section_type, str):
                        section_type = LessonType(section_type)
                    type_index = type_options.index(section_type)
                    lesson_type = st.selectbox(
                        "Type",
                        options=type_options,
                        index=type_index,
                        key=f"type_{i}"
                    )
                    duration = st.number_input("Duration (minutes)", value=section.duration, key=f"duration_{i}")
                    topics = st.text_area("Topics (One per line)", value="\n".join(section.topics), key=f"topics_{i}")
                    
                    updated_outline.append(
                        OutlineSection(
                            order=i,
                            title=title,
                            description=description,
                            type=lesson_type,
                            duration=duration,
                            topics=topics.split("\n"),
                        )
                    )
            
            st.session_state.course_data['outline'] = updated_outline
            
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Back", use_container_width=True):
                    st.session_state.wizard_step = 2
                    st.rerun()
            with col2:
                if st.button("Create Course", type="primary", use_container_width=True):
                    try:
                        course = st.session_state.course_instance
                        
                        # Update the course outline
                        await CourseCreateHandler.set_course_outline(course.id, st.session_state.course_data['outline'])

                        st.success("Course created successfully!")
                        st.session_state.current_page = "content_creator_course_list"
                        st.rerun()

                    except Exception as e:
                        st.error(f"Error finalizing course: {str(e)}") 