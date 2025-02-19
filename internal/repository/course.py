from enum import Enum

from tortoise import fields
from tortoise.models import Model

class Course(Model):
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    is_active = fields.BooleanField(default=True)

    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=255)
    description = fields.TextField(null=True)

    learning_outcomes = fields.JSONField(description="List of learning outcomes", null=True)
    target_audience = fields.TextField(null=True)
    duration = fields.FloatField(description="Course duration in hours", null=True)


class LessonType(Enum):
    CONTENT = "content"
    QUIZ = "quiz"


class OutlineSection(Model):
    id = fields.IntField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    order = fields.IntField()
    title = fields.CharField(max_length=255)
    description = fields.TextField()
    type = fields.CharEnumField(LessonType)
    duration = fields.IntField()
    topics = fields.JSONField()

    course: fields.ForeignKeyRelation[Course] = fields.ForeignKeyField("models.Course", related_name="outline_sections")

    quiz: fields.OneToOneRelation["Quiz"] = fields.OneToOneField("models.Quiz", related_name="section", null=True)
    content: fields.OneToOneRelation["Content"] = fields.OneToOneField("models.Content", related_name="section", null=True)

    linked_sections = fields.JSONField(default=[]) 


    class Meta:
        table = "outline_sections"


class QuizType(Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    FILL_IN_THE_BLANK = "fill_in_the_blank"


class Quiz(Model):
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    id = fields.IntField(pk=True)
    type = fields.CharEnumField(QuizType)
    questions = fields.JSONField()

    class Meta:
        table = "quiz"


class Content(Model):
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    id = fields.IntField(pk=True)
    markdown = fields.TextField()