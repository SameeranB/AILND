from datetime import datetime
from typing import Dict, List, Optional, Tuple

from internal.repository.student_progress import (
    StudentProgressRepository,
    StudentCourseTracker,
    QuizAttempt,
    SectionStatus
)

class StudentProgressHandler:
    @staticmethod
    async def get_course_progress(course_id: str) -> StudentCourseTracker:
        """Get or initialize course progress"""
        return await StudentProgressRepository.get_or_create_progress(course_id)
    
    @staticmethod
    async def mark_section_complete(
        course_id: str,
        section_id: str,
        is_quiz: bool = False,
        quiz_data: Optional[Dict] = None
    ) -> None:
        """Mark a section as complete and handle quiz data if present"""
        progress = await StudentProgressRepository.get_or_create_progress(course_id)
        
        # Update section status
        await StudentProgressRepository.update_section_status(
            progress,
            section_id,
            SectionStatus.COMPLETED
        )
        
        # Handle quiz data if this is a quiz section
        if is_quiz and quiz_data:
            # Ensure all required fields are present and of correct type
            if not all(key in quiz_data for key in ["quiz_id", "score", "answers", "incorrect_questions"]):
                raise ValueError("Missing required fields in quiz_data")
                
            attempt = QuizAttempt(
                quiz_id=str(quiz_data["quiz_id"]),  # Ensure string
                score=float(quiz_data["score"]),    # Ensure float
                completed_at=datetime.utcnow(),
                answers=quiz_data["answers"],
                incorrect_questions=quiz_data["incorrect_questions"]
            )
            
            # Add the attempt to the progress tracker
            await StudentProgressRepository.add_quiz_attempt(progress, section_id, attempt)
    
    @staticmethod
    async def start_section(
        course_id: str,
        section_id: str,
        section_index: int
    ) -> None:
        """Mark a section as in progress"""
        progress = await StudentProgressRepository.get_or_create_progress(course_id)
        
        # Update section status
        await StudentProgressRepository.update_section_status(
            progress,
            section_id,
            SectionStatus.IN_PROGRESS
        )
        
        # Update current section
        await StudentProgressRepository.update_current_section(progress, section_index)
    
    @staticmethod
    async def get_quiz_history(
        course_id: str,
        section_id: str
    ) -> List[QuizAttempt]:
        """Get all quiz attempts for a section"""
        progress = await StudentProgressRepository.get_or_create_progress(course_id)
        return await StudentProgressRepository.get_quiz_attempts(progress, section_id)
    
    @staticmethod
    async def mark_course_completed(course_id: str) -> None:
        """Mark the entire course as completed"""
        progress = await StudentProgressRepository.get_or_create_progress(course_id)
        await StudentProgressRepository.mark_course_completed(progress)
    
    @staticmethod
    async def get_section_progress(
        course_id: str,
        section_id: str
    ) -> Tuple[SectionStatus, List[QuizAttempt]]:
        """Get section status and quiz attempts if any"""
        progress = await StudentProgressRepository.get_or_create_progress(course_id)
        status = await StudentProgressRepository.get_section_status(progress, section_id)
        attempts = await StudentProgressRepository.get_quiz_attempts(progress, section_id)
        return status, attempts
    
    @staticmethod
    async def get_current_section(course_id: str) -> int:
        """Get the current section index"""
        progress = await StudentProgressRepository.get_or_create_progress(course_id)
        return progress.current_section_index 