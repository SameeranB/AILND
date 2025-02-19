import asyncio
import streamlit as st
from dotenv import load_dotenv
import os

from internal.utils.db import init_db
from pages.course_editor import course_editor_page
from pages.course_list import course_list_page
from pages.take_content import take_content_page
from pages.take_quiz import take_quiz_page
from pages.metrics import metrics_page
from pages.content_creator_course_list import content_creator_course_list_page
from pages.course_detail import course_detail_page
from pages.section_editor import section_editor_page
from pages.course_index import course_index_page

# Load environment variables
load_dotenv()

# Initialize session state
if "user_role" not in st.session_state:
    st.session_state.user_role = "student"

if "current_page" not in st.session_state:
    st.session_state.current_page = "course_list"

if "event_loop" not in st.session_state:
    st.session_state.event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(st.session_state.event_loop)


def switch_role():
    st.session_state.user_role = (
        "content_creator" if st.session_state.role_switch else "student"
    )


def render_navbar():
    st.sidebar.title("Navigation")

    current_mode = (
        "Student Mode"
        if st.session_state.user_role == "student"
        else "Content Creator Mode"
    )
    is_content_creator = st.sidebar.toggle(
        current_mode,
        value=st.session_state.user_role == "content_creator",
        key="role_switch",
        on_change=switch_role,
    )

    st.sidebar.markdown("---")

    if st.session_state.user_role == "content_creator":
        if st.sidebar.button("Course List", use_container_width=True):
            st.session_state.current_page = "content_creator_course_list"
        if st.sidebar.button("Course Editor", use_container_width=True):
            st.session_state.current_page = "course_editor"
    else:
        if st.sidebar.button("Course List", use_container_width=True):
            st.session_state.current_page = "course_list"
        if st.sidebar.button("Metrics", use_container_width=True):
            st.session_state.current_page = "metrics"


async def main():
    # Project Initialization
    await init_db()

    # Render UI
    render_navbar()

    # Render the appropriate page
    if st.session_state.user_role == "content_creator":
        if st.session_state.current_page == "content_creator_course_list":
            await content_creator_course_list_page()
        elif st.session_state.current_page == "course_editor":
            await course_editor_page()
        elif st.session_state.current_page == "course_detail":
            if "selected_course_id" in st.session_state:
                await course_detail_page(st.session_state.selected_course_id)
            else:
                st.error("No course selected")
                st.session_state.current_page = "content_creator_course_list"
        elif st.session_state.current_page == "section_editor":
            if "selected_course_id" in st.session_state and "selected_section_id" in st.session_state:
                await section_editor_page(st.session_state.selected_course_id, st.session_state.selected_section_id)
            else:
                st.error("No section selected")
                st.session_state.current_page = "course_detail"
    else:
        if st.session_state.current_page == "course_list":
            await course_list_page()
        elif st.session_state.current_page == "course_index":
            await course_index_page()
        elif st.session_state.current_page == "take_content":
            await take_content_page()
        elif st.session_state.current_page == "take_quiz":
            await take_quiz_page()
        elif st.session_state.current_page == "metrics":
            await metrics_page()
        else:
            st.warning("You don't have access to this page with your current role.")


# Streamlit doesn't allow `asyncio.run()` multiple times.
# Instead, use `asyncio.create_task()` with the event loop from session state.
if __name__ == "__main__":
    st.set_page_config(
        page_title="Essential5 Learning Platform",
        page_icon="📚",
        layout="wide"
    )
    st.runtime.scriptrunner.add_script_run_ctx()
    st.runtime.scriptrunner.get_script_run_ctx().gather_usage_stats = False
    
    loop = st.session_state.event_loop
    loop.run_until_complete(main())