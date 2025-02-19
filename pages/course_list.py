import streamlit as st

from internal.handlers.course import CourseViewHandler


async def course_list_page():
    st.title("Available Courses")
    
    try:
        # Fetch all courses from the API using the shared event loop
        courses = await CourseViewHandler.list_courses()
        
        if not courses:
            st.info("No courses available yet.")
            return
        
        # Display courses in a grid
        col1, col2 = st.columns(2)
        
        for i, course in enumerate(courses):
            with (col1 if i % 2 == 0 else col2):
                with st.container():
                    st.subheader(course.title)
                    st.write(course.description)
                    st.write(f"Duration: {course.duration or 'N/A'} hours")
                    # TODO: Add progress tracking
                    st.progress(0)  # Placeholder for progress
                    if st.button("View Course", key=f"view_{i}"):
                        # Store course ID and navigate to course index
                        st.session_state.selected_course_id = str(course.id)
                        st.session_state.current_page = "course_index"
                        st.rerun()
    except Exception as e:
        st.error(f"Error loading courses: {str(e)}") 