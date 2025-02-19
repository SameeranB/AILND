import pdb

import streamlit as st
from typing import Optional, List

from internal.handlers.intelligence import IntelligenceHandler
from internal.handlers.section import SectionViewHandler
from internal.repository.course import LessonType, OutlineSection
from pages.quiz_editor import quiz_editor_page

async def get_linkable_sections(course: OutlineSection, current_section: OutlineSection) -> List[OutlineSection]:
    """Get all content sections that can be linked to the current quiz section."""
    linkable_sections = []
    for section in course.outline_sections:
        # Only include content sections that come before this quiz
        if (section.type == LessonType.CONTENT and 
            section.order < current_section.order):
            linkable_sections.append(section)
    return linkable_sections

async def section_editor_page(course_id: str, section_id: str):
    try:
        # Initialize session state for this section if not exists
        if f"content_{section_id}" not in st.session_state:
            st.session_state[f"content_{section_id}"] = None

        # Fetch course and section details
        course, section = await SectionViewHandler.get_section_with_content(course_id, section_id)
        
        # Layout with sidebar and main content
        with st.sidebar:
            st.title("Course Details")
            if st.button("← Back to Course"):
                st.session_state.current_page = "course_detail"
                st.session_state.selected_course_id = course_id
                st.rerun()
                
            st.markdown("---")
            st.markdown(f"**Course:** {course.title}")
            st.markdown(f"**Description:** {course.description}")
            
            st.markdown("---")
            st.markdown("### Section Details")
            st.markdown(f"**Title:** {section.title}")
            st.markdown(f"**Type:** {section.type.value}")
            st.markdown(f"**Duration:** {section.duration} minutes")
            st.markdown("**Topics to Cover:**")
            for topic in section.topics:
                st.markdown(f"- {topic}")
            
            # Add linked sections display in sidebar for quiz sections
            if section.type == LessonType.QUIZ and section.linked_sections:
                st.markdown("---")
                st.markdown("### Linked Sections")
                for linked_id in section.linked_sections:
                    try:
                        _, linked_section = await SectionViewHandler.get_section_with_content(course_id, str(linked_id))
                        st.markdown(f"- {linked_section.title}")
                    except ValueError:
                        st.markdown(f"- Unknown section ({linked_id})")
        
        # Main content area
        st.title(f"Editing: {section.title}")
        
        if section.type == LessonType.QUIZ:
            # Add section linking UI before the quiz editor
            st.header("Link Content Sections")
            st.write("Select the content sections this quiz will test knowledge from:")
            
            # Get linkable sections
            linkable_sections = await get_linkable_sections(course, section)
            
            if not linkable_sections:
                st.warning("No content sections available to link. Add some content sections before this quiz.")
            else:
                # Create a mapping of section IDs to their titles for the multiselect
                section_options = {str(s.id): f"{s.order}. {s.title}" for s in linkable_sections}
                
                # Convert current linked_sections to strings for comparison
                current_linked = [str(id) for id in section.linked_sections] if section.linked_sections else []
                
                # Create multiselect for section linking
                selected_sections = st.multiselect(
                    "Select sections to link",
                    options=list(section_options.keys()),
                    default=current_linked,
                    format_func=lambda x: section_options[x]
                )
                
                # Save button for linked sections
                if st.button("Save Linked Sections"):
                    try:
                        # Convert selected section IDs to integers
                        section.linked_sections = [int(s_id) for s_id in selected_sections]
                        await section.save()
                        st.success("Linked sections updated successfully!")
                    except Exception as e:
                        st.error(f"Error saving linked sections: {str(e)}")
                
                st.markdown("---")  # Visual separator
            
            # Continue with the quiz editor
            await quiz_editor_page(course_id, section_id)
            return
        else:
            # Ensure section has content and get it
            content = await SectionViewHandler.ensure_section_content(section.id)

            if st.button("Generate"):
                try:
                    generated_content = await IntelligenceHandler.generate_section_content(course_id, section_id, content.id)
                    st.session_state[f"content_{section_id}"] = generated_content
                    st.success("Content generated successfully!")
                except Exception as e:
                    st.error(f"Error generating content: {str(e)}")

            # Content editor
            display_content = st.session_state[f"content_{section_id}"] if st.session_state[f"content_{section_id}"] is not None else (content.markdown if content else "")
            new_content = st.text_area(
                "Content (Markdown)",
                value=display_content,
                height=600
            )

            col1, col2 = st.columns([3, 3])
            with col1:
                if st.button("Save"):
                    try:
                        await SectionViewHandler.update_section_content(section.id, new_content)
                        st.session_state[f"content_{section_id}"] = new_content
                        st.success("Content saved successfully!")
                    except Exception as e:
                        st.error(f"Error saving content: {str(e)}")

            # Preview section
            if st.checkbox("Show Preview", value=True):
                st.markdown("---")
                st.markdown("### Preview")
                st.markdown(new_content)

    except ValueError as e:
        st.error(str(e))
        return 