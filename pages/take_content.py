import streamlit as st
from internal.handlers.course import CourseViewHandler
from internal.repository.course import LessonType
from internal.handlers.student_progress import StudentProgressHandler
from internal.repository.student_progress import SectionStatus
from internal.handlers.intelligence import IntelligenceHandler

async def initialize_chat():
    """Initialize chat-related session state variables."""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'chatbot_agent' not in st.session_state:
        st.session_state.chatbot_agent = None

async def display_chat_interface(course_id: int, section_id: str):
    """Display the chat interface in the sidebar."""
    with st.sidebar:
        st.title("Course Assistant")
        st.markdown("Ask questions about the course content and get helpful answers!")

        # Create containers for chat components
        chat_container = st.container()
        input_container = st.container()

        # Initialize chatbot if not already done
        if st.session_state.chatbot_agent is None:
            with st.spinner("Initializing course assistant..."):
                st.session_state.chatbot_agent, st.session_state.sys_prompt = await IntelligenceHandler.get_course_chatbot(str(course_id), section_id)

        # Chat input (placed first in code but will appear at bottom)
        with input_container:
            prompt = st.chat_input("Ask a question about the course")

        # Display chat messages in the container
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        # Handle new messages
        if prompt:
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Display user message
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)

            # Get chatbot response
            with chat_container:
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        final_prompt = st.session_state.sys_prompt + "\n\n" + prompt
                        response = st.session_state.chatbot_agent.run(final_prompt)
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})

async def take_content_page():
    """Handle content viewing functionality."""
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
        
        # Display chat interface in sidebar
        await display_chat_interface(course_id, section_id)
        
        # Display section header
        st.header(current_section.title)
        st.write(current_section.description)
        
        # Get section progress
        progress = await StudentProgressHandler.get_section_progress(course_id, section_id)
        
        # Mark section as in progress if not already completed
        if progress[0] != SectionStatus.COMPLETED.value:
            await StudentProgressHandler.start_section(
                course_id,
                section_id,
                st.session_state.current_section_index
            )
        
        # Display content
        if current_section.content:
            st.markdown(current_section.content.markdown)
        else:
            st.warning("No content available for this section.")
        
        # Navigation
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("← Back to Course Index", use_container_width=True):
                st.session_state.current_page = "course_index"
                st.rerun()
        
        with col2:
            if st.session_state.current_section_index < len(sections) - 1:
                next_section = sections[st.session_state.current_section_index + 1]
                if st.button("Mark Complete & Continue →", use_container_width=True):
                    # Mark current section as complete
                    await StudentProgressHandler.mark_section_complete(
                        course_id,
                        section_id
                    )
                    # Move to next section
                    st.session_state.current_section_index += 1
                    
                    # Determine next page based on next section type
                    if next_section.type == LessonType.QUIZ:
                        st.session_state.current_page = "take_quiz"
                    else:
                        st.session_state.current_page = "take_content"
                    st.rerun()
            else:
                if st.button("Complete Course", use_container_width=True):
                    # Mark final section and course as complete
                    await StudentProgressHandler.mark_section_complete(
                        course_id,
                        section_id
                    )
                    await StudentProgressHandler.mark_course_completed(course_id)
                    st.success("Congratulations! You've completed the course!")
                    st.session_state.current_page = "course_index"
                    st.rerun()
                    
    except Exception as e:
        st.error(f"Error in content page: {str(e)}") 