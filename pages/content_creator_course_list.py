import logging
import streamlit as st

from internal.handlers.course import CourseViewHandler, CourseDeleteHandler

logger = logging.getLogger(__name__)


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
                    delete_key = f"delete_{course.id}"
                    confirm_key = f"confirm_{course.id}"
                    
                    # Initialize the confirmation state if not exists
                    if delete_key not in st.session_state:
                        st.session_state[delete_key] = False
                    
                    if not st.session_state[delete_key]:
                        # Show initial delete button
                        if st.button("Delete", key=f"del_btn_{course.id}", type="secondary"):
                            st.session_state[delete_key] = True
                            st.rerun()
                    else:
                        # Show confirmation dialog
                        st.warning(f"Are you sure you want to delete '{course.title}'?")
                        confirm_col1, confirm_col2 = st.columns([1, 1])
                        
                        with confirm_col1:
                            if st.button("Yes, delete", key=f"yes_{course.id}", type="primary"):
                                try:
                                    if await CourseDeleteHandler.delete_course(str(course.id)):
                                        st.success(f"Course '{course.title}' deleted successfully!")
                                        # Reset the state
                                        st.session_state[delete_key] = False
                                        st.rerun()
                                    else:
                                        st.error("Course not found. It may have been already deleted.")
                                except Exception as e:
                                    st.error(f"Error deleting course: {str(e)}")
                                    logger.error(f"Failed to delete course {course.id}: {str(e)}")
                        
                        with confirm_col2:
                            if st.button("No, cancel", key=f"no_{course.id}"):
                                # Reset the state
                                st.session_state[delete_key] = False
                                st.rerun()
    except Exception as e:
        st.error(f"Error loading courses: {str(e)}") 