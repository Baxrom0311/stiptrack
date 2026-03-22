from app.models.ai_job import AIJob
from app.models.application import Application, ApplicationStatusLog, ApplicationValue, StudentAchievement
from app.models.base import Base
from app.models.evaluation import Evaluation
from app.models.scholarship import JuryAssignment, Scholarship, ScholarshipColumn, ScholarshipTemplate
from app.models.user import User
from app.models.workflow import Appeal, ScholarshipStage, StageTask

__all__ = [
    "AIJob",
    "Application",
    "ApplicationStatusLog",
    "ApplicationValue",
    "Appeal",
    "Base",
    "Evaluation",
    "JuryAssignment",
    "ScholarshipStage",
    "Scholarship",
    "ScholarshipColumn",
    "ScholarshipTemplate",
    "StageTask",
    "StudentAchievement",
    "User",
]
