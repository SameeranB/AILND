import logging
from typing import Optional, Tuple

from internal.repository.course import Course, OutlineSection, Content, LessonType

logger = logging.getLogger(__name__)

class SectionViewHandler:
    @staticmethod
    async def get_section_with_content(course_id: str, section_id: str) -> Tuple[Course, OutlineSection]:
        """Get a section and its content, ensuring the section belongs to the specified course.
        
        Args:
            course_id: The ID of the course
            section_id: The ID of the section
            
        Returns:
            Tuple[Course, OutlineSection]: The course and section objects
            
        Raises:
            ValueError: If course or section is not found
        """
        course = await Course.get_or_none(id=course_id)
        if not course:
            raise ValueError(f"Course with ID {course_id} not found")
            
        await course.fetch_related('outline_sections')
        section = next((s for s in course.outline_sections if str(s.id) == section_id), None)
        if not section:
            raise ValueError(f"Section with ID {section_id} not found in course {course_id}")
            
        await section.fetch_related('content')
        return course, section

    @staticmethod
    async def ensure_section_content(section_id: int) -> Content:
        """Ensure a section has content, creating it if it doesn't exist.
        
        Args:
            section: The section to ensure content for
            
        Returns:
            Content: The section's content object
        """
        section = await OutlineSection.get_or_none(id=section_id)
        await section.fetch_related('content')

        if section.content is None:
            try:
                # Create new content
                content = await Content.create(
                    markdown="# New Section\nStart writing your content here..."
                )
                section.content = content
                await section.save()

                return section.content
            except Exception as e:
                logger.error(f"Error creating content for section {section.id}: {str(e)}")
                raise ValueError(f"Failed to create content for section: {str(e)}")
            
        return section.content

    @staticmethod
    async def update_section_content(section_id: int, markdown_content: str) -> None:
        """Update the content of a section.
        
        Args:
            section: The section to update
            markdown_content: The new markdown content
            
        Raises:
            ValueError: If there's an error updating the content
        """
        section = await OutlineSection.get_or_none(id=section_id)
        if section is None:
            raise ValueError(f"Section with ID {section_id} not found")

        try:
            await section.fetch_related('content')
            if section.content is None:
                # If no content exists, create it
                content = await Content.create(
                    markdown=markdown_content
                )
                section.content = content
                await section.save()
                logger.info(f"Created new content for section {section.id}")
            else:
                # Update existing content
                section.content.markdown = markdown_content
                await section.content.save()
                logger.info(f"Updated content for section {section.id}")
        except Exception as e:
            logger.error(f"Error updating content for section {section.id}: {str(e)}")
            raise ValueError(f"Failed to update section content: {str(e)}") 