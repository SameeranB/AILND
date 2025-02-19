import streamlit as st
from internal.handlers.course import CourseViewHandler
from internal.handlers.student_progress import StudentProgressHandler
from internal.repository.course import LessonType
from internal.repository.student_progress import SectionStatus

async def course_index_page():
    st.title("Course Overview")
    
    if 'selected_course_id' not in st.session_state:
        st.warning("Please select a course from the course list")
        st.session_state.current_page = "course_list"
        st.rerun()
        return
    
    try:
        # Fetch course data
        course = await CourseViewHandler.get_course(st.session_state.selected_course_id)
        if not course:
            st.error("Course not found")
            st.session_state.current_page = "course_list"
            st.rerun()
            return
            
        # Get course progress
        course_id = int(course.id)
        progress = await StudentProgressHandler.get_course_progress(course_id)
        
        # Course Header
        st.header(course.title)
        st.write(course.description)
        
        # Progress tracking
        sections = sorted(course.outline_sections, key=lambda x: x.order)
        if not sections:
            st.info("This course has no content yet.")
            return
            
        completed_sections = sum(1 for section in sections 
                               if progress.section_status.get(str(section.id)) == SectionStatus.COMPLETED.value)
        progress_value = completed_sections / len(sections)
        st.progress(progress_value)
        st.write(f"Progress: {completed_sections}/{len(sections)} sections completed")
        
        # Display sections
        st.markdown("## Course Sections")
        for i, section in enumerate(sections):
            section_id = str(section.id)
            status = progress.section_status.get(section_id, SectionStatus.NOT_STARTED.value)
            
            # Create a container for each section
            with st.container():
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    # Show section title with status indicator
                    status_emoji = "✅" if status == SectionStatus.COMPLETED.value else "🔄" if status == SectionStatus.IN_PROGRESS.value else "⏳"
                    st.markdown(f"### {status_emoji} Section {i + 1}: {section.title}")
                    st.write(section.description)
                    
                    # If it's a quiz section, show attempts
                    if section.type == LessonType.QUIZ:
                        _, attempts = await StudentProgressHandler.get_section_progress(course_id, section_id)
                        if attempts:
                            st.markdown("**Previous Attempts:**")
                            for j, attempt in enumerate(attempts, 1):
                                st.write(f"Attempt {j}: {attempt.score:.1f}% ({attempt.completed_at.strftime('%Y-%m-%d %H:%M')})")
                
                with col2:
                    # Button to start/continue section
                    if st.button("Open Section", key=f"section_{i}", use_container_width=True):
                        st.session_state.current_section_index = i
                        # Route to appropriate page based on section type
                        if section.type == LessonType.QUIZ:
                            st.session_state.current_page = "take_quiz"
                        else:
                            st.session_state.current_page = "take_content"
                        st.rerun()
                
                st.markdown("---")
        
    except Exception as e:
        st.error(f"Error loading course index: {str(e)}") 