from dataclasses import dataclass
from typing import List, Dict, Any
import json
from internal.repository.course import QuizType


@dataclass
class BaseQuestion:
    question: str
    justification: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "justification": self.justification
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseQuestion':
        return cls(
            question=data["question"],
            justification=data["justification"]
        )


@dataclass
class MultipleChoiceQuestion(BaseQuestion):
    options: List[str]
    correct_answer: int  # Index of the correct answer

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "options": self.options,
            "correct_answer": self.correct_answer
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MultipleChoiceQuestion':
        return cls(
            question=data["question"],
            justification=data["justification"],
            options=data["options"],
            correct_answer=data["correct_answer"]
        )

    def validate(self) -> bool:
        return (
            len(self.options) > 1 and
            0 <= self.correct_answer < len(self.options) and
            bool(self.question.strip()) and
            bool(self.justification.strip())
        )


@dataclass
class FillInBlankQuestion(BaseQuestion):
    correct_answer: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "correct_answer": self.correct_answer
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FillInBlankQuestion':
        return cls(
            question=data["question"],
            justification=data["justification"],
            correct_answer=data["correct_answer"]
        )

    def validate(self) -> bool:
        return (
            "_____" in self.question and
            bool(self.correct_answer.strip()) and
            bool(self.question.strip()) and
            bool(self.justification.strip())
        )


@dataclass
class Quiz:
    type: QuizType
    questions: List[BaseQuestion]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "questions": [q.to_dict() for q in self.questions]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Quiz':
        quiz_type = QuizType(data["type"])
        question_class = MultipleChoiceQuestion if quiz_type == QuizType.MULTIPLE_CHOICE else FillInBlankQuestion
        
        questions = [
            question_class.from_dict(q) for q in data["questions"]
        ]
        
        return cls(type=quiz_type, questions=questions)

    def validate(self) -> bool:
        if not self.questions:
            return False
            
        return all(q.validate() for q in self.questions)
