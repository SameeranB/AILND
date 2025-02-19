import logging
import pdb
from typing import List, Optional, Dict, Any

from internal.repository.course import Course, OutlineSection, LessonType, Quiz, Content

logger = logging.getLogger(__name__)

class CourseViewHandler:
    @staticmethod
    async def list_courses():
        """Get all courses"""
        return await Course.all()

    @staticmethod
    async def get_course(course_id: str) -> Course:
        """Retrieves a course by its ID with all related data

        Args:
            course_id: The ID of the course to retrieve

        Returns:
            Course: The course instance with all related data loaded

        Raises:
            ValueError: If course is not found
        """
        course = await Course.get_or_none(id=course_id)
        if not course:
            raise ValueError(f"Course with ID {course_id} not found")
            
        # Load all related data
        await course.fetch_related('outline_sections')

        for section in course.outline_sections:
            await section.fetch_related('content')


        return course
        
    @staticmethod
    async def update_section_details(
        section: OutlineSection,
        title: str,
        description: str,
        lesson_type: LessonType,
        duration: int,
        topics: List[str]
    ) -> None:
        """Update the details of a section.
        
        Args:
            section: The section to update
            title: New section title
            description: New section description
            lesson_type: New section type
            duration: New duration in minutes
            topics: New list of topics
            
        Raises:
            Exception: If there's an error saving the section
        """
        section.title = title
        section.description = description
        section.type = lesson_type
        section.duration = duration
        section.topics = topics
        await section.save()
        
    @staticmethod
    async def update_section_content(
        section: OutlineSection,
        content: str
    ) -> None:
        """Update the content of a section.
        
        Args:
            section: The section to update
            content: New markdown content
            
        Raises:
            ValueError: If section has no content
            Exception: If there's an error saving the content
        """
        if section.content is None:
            raise ValueError("Section has no content")
            
        section.content.markdown = content
        await section.content.save()

class CourseCreateHandler:
    @staticmethod
    async def init_course(title: str, description: str) -> Course:
        """Initialize a new course with basic details."""
        return await Course.create(
            title=title,
            description=description,
            learning_outcomes=[],
            duration=1.0,
            target_audience=""
        )

    @staticmethod
    async def update_course(
        course_id: str,
        title: str,
        description: str,
        learning_outcomes: List[str],
        duration: float,
        target_audience: str
    ) -> None:
        """Update course details."""
        course = await Course.get(id=course_id)
        course.title = title
        course.description = description
        course.learning_outcomes = learning_outcomes
        course.duration = duration
        course.target_audience = target_audience
        await course.save()

    @staticmethod
    async def set_course_details(
        course_id: str,
        learning_outcomes: str,
        target_audience: str,
        duration: float
    ) -> None:
        """Set additional course details."""
        course = await Course.get(id=course_id)
        course.learning_outcomes = learning_outcomes.split("\n")
        course.target_audience = target_audience
        course.duration = duration
        await course.save()

    @staticmethod
    async def set_course_outline(course_id: str, outline: List[OutlineSection]) -> None:
        """Set the course outline."""
        course = await Course.get(id=course_id)
        for section in outline:
            section.course = course
            await section.save()

class CourseDeleteHandler:
    @staticmethod
    async def delete_course(course_id: str) -> bool:
        """Delete a course and all its related data

        Args:
            course_id: The ID of the course to delete

        Returns:
            bool: True if course was deleted, False if course was not found
            
        Raises:
            Exception: If there's an error during deletion
        """
        try:
            logger.info(f"Attempting to delete course with ID: {course_id}")
            
            course = await Course.get_or_none(id=course_id)
            if not course:
                logger.warning(f"Course with ID {course_id} not found")
                return False

            logger.info(f"Found course: {course.title} (ID: {course_id})")
            
            # Fetch related sections
            await course.fetch_related('outline_sections')
            logger.info(f"Found {len(course.outline_sections)} sections to delete")
            
            # Delete related data for each section
            for section in course.outline_sections:
                try:
                    logger.info(f"Processing section {section.id}: {section.title}")
                    
                    # Delete quiz if exists
                    if section.quiz_id:
                        logger.info(f"Deleting quiz {section.quiz_id}")
                        await Quiz.filter(id=section.quiz_id).delete()
                    
                    # Delete content if exists
                    if section.content_id:
                        logger.info(f"Deleting content {section.content_id}")
                        await Content.filter(id=section.content_id).delete()
                    
                    # Delete the section
                    logger.info(f"Deleting section {section.id}")
                    await section.delete()
                except Exception as e:
                    logger.error(f"Error deleting section {section.id}: {str(e)}")
                    raise Exception(f"Failed to delete section {section.id}: {str(e)}")

            # Finally delete the course
            logger.info(f"Deleting course {course_id}")
            await course.delete()
            logger.info(f"Successfully deleted course {course_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error in delete_course: {str(e)}")
            raise Exception(f"Failed to delete course: {str(e)}")