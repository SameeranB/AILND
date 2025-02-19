from typing import Dict, List, Optional
from datetime import datetime
from tortoise import fields, models
from enum import Enum

class SectionStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class StudentCourseTracker(models.Model):
    """Tracks a student's progress in a course"""
    id = fields.UUIDField(pk=True)
    course_id = fields.IntField()
    last_accessed = fields.DatetimeField(auto_now=True)
    current_section_index = fields.IntField(default=0)
    completed = fields.BooleanField(default=False)
    completed_at = fields.DatetimeField(null=True)
    
    # Store section completion status
    section_status = fields.JSONField(default=dict)  # Dict[str, SectionStatus]
    
    # Store quiz attempts and results
    quiz_results = fields.JSONField(default=dict)  # Dict[str, List[QuizAttempt]]
    
    class Meta:
        table = "student_course_tracker"

class QuizAttempt:
    """Represents a single quiz attempt"""
    def __init__(
        self,
        quiz_id: str,
        score: float,
        completed_at: datetime,
        answers: Dict[str, str],  # question_index -> answer
        incorrect_questions: List[int]  # list of question indices that were wrong
    ):
        self.quiz_id = quiz_id
        self.score = score
        self.completed_at = completed_at
        self.answers = answers
        self.incorrect_questions = incorrect_questions
        
    def to_dict(self) -> dict:
        return {
            "quiz_id": self.quiz_id,
            "score": self.score,
            "completed_at": self.completed_at.isoformat(),
            "answers": self.answers,
            "incorrect_questions": self.incorrect_questions
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'QuizAttempt':
        return cls(
            quiz_id=data["quiz_id"],
            score=data["score"],
            completed_at=datetime.fromisoformat(data["completed_at"]),
            answers=data["answers"],
            incorrect_questions=data["incorrect_questions"]
        )

class StudentProgressRepository:
    @staticmethod
    async def get_or_create_progress(course_id: int) -> StudentCourseTracker:
        """Get or create a progress tracker for the course"""
        progress, _ = await StudentCourseTracker.get_or_create(
            course_id=course_id,
            defaults={
                "section_status": {},
                "quiz_results": {}
            }
        )
        return progress
    
    @staticmethod
    async def update_section_status(
        progress: StudentCourseTracker,
        section_id: str,
        status: SectionStatus
    ) -> None:
        """Update the status of a section"""
        progress.section_status[section_id] = status.value
        await progress.save()
    
    @staticmethod
    async def add_quiz_attempt(
        progress: StudentCourseTracker,
        section_id: str,
        attempt: QuizAttempt
    ) -> None:
        """Add a new quiz attempt"""
        if section_id not in progress.quiz_results:
            progress.quiz_results[section_id] = []
            
        # Convert attempt to dict for storage
        progress.quiz_results[section_id].append(attempt.to_dict())
        await progress.save()
    
    @staticmethod
    async def get_quiz_attempts(
        progress: StudentCourseTracker,
        section_id: str
    ) -> List[QuizAttempt]:
        """Get all quiz attempts for a section"""
        attempts_data = progress.quiz_results.get(section_id, [])
        return [QuizAttempt.from_dict(data) for data in attempts_data]
    
    @staticmethod
    async def mark_course_completed(progress: StudentCourseTracker) -> None:
        """Mark the course as completed"""
        progress.completed = True
        progress.completed_at = datetime.utcnow()
        await progress.save()
    
    @staticmethod
    async def get_section_status(
        progress: StudentCourseTracker,
        section_id: str
    ) -> SectionStatus:
        """Get the status of a section"""
        return SectionStatus(progress.section_status.get(section_id, SectionStatus.NOT_STARTED.value))
    
    @staticmethod
    async def update_current_section(
        progress: StudentCourseTracker,
        section_index: int
    ) -> None:
        """Update the current section index"""
        progress.current_section_index = section_index
        await progress.save() 