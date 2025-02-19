import streamlit as st

from internal.handlers.course import CourseViewHandler, CourseDeleteHandler


async def content_creator_course_list_page():
    st.title("Course Management")
    
    # Add new course button at the top
    if st.button("Create New Course", type="primary"):
        st.session_state.current_page = "course_editor"
        st.session_state.editing_course = None  # New course mode
    
    try:
        # Fetch all courses from the API
        courses = await CourseViewHandler.list_courses()
        
        if not courses:
            st.info("No courses created yet. Click 'Create New Course' to get started.")
            return
            
        # Display courses in a table format for better management
        for i, course in enumerate(courses):
            with st.expander(f"{course.title} ({course.is_active and 'Published' or 'Draft'})"):
                st.write(f"**Description:** {course.description}")
                st.write(f"**Duration:** {course.duration or 'N/A'} hours")
                st.write(f"**Target Audience:** {course.target_audience or 'N/A'}")
                
                col1, col2, col3 = st.columns([1, 1, 1])
                with col1:
                    if st.button("View Details", key=f"view_{i}"):
                        st.session_state.current_page = "course_detail"
                        st.session_state.selected_course_id = course.id
                        st.rerun()
                with col2:
                    if st.button("Preview", key=f"preview_{i}"):
                        st.session_state.current_page = "take_course"
                        st.session_state.selected_course = course
                        st.rerun()
                with col3:
                    if st.button("Delete", key=f"delete_{i}", type="secondary"):
                        if st.button(f"Confirm delete {course.title}?", key=f"confirm_delete_{i}"):
                            try:
                                await CourseDeleteHandler.delete_course(course.id)
                                st.success(f"Course '{course.title}' deleted successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error deleting course: {str(e)}")
    except Exception as e:
        st.error(f"Error loading courses: {str(e)}") 