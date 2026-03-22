from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    JURY = "jury"
    STUDENT = "student"


class ScholarshipStatus(StrEnum):
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"
    DONE = "done"


class ScholarshipStageType(StrEnum):
    APPLICATION = "application"
    REVIEW = "review"
    EXAM = "exam"
    INTERVIEW = "interview"
    FINAL_DECISION = "final_decision"
    APPEAL = "appeal"


class ColumnFieldType(StrEnum):
    TEXT = "text"
    TEXTAREA = "textarea"
    FILE = "file"
    NUMBER = "number"
    DATE = "date"
    SELECT = "select"
    URL = "url"


class ApplicationStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    WINNER = "winner"
    REJECTED = "rejected"


class AchievementType(StrEnum):
    PAPER = "paper"
    AWARD = "award"
    PROJECT = "project"
    CERT = "cert"
    OLYMPIAD = "olympiad"
    OTHER = "other"


class AIJobType(StrEnum):
    COLUMN_GEN = "column_gen"
    APP_ANALYSIS = "app_analysis"
    REVIEW_GEN = "review_gen"


class AIJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class LLMProvider(StrEnum):
    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    DEEPSEEK = "deepseek"


class StageTaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELED = "canceled"


class AppealStatus(StrEnum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
