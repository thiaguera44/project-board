"""SQLAlchemy persistence models for Project Board."""

from sqlalchemy import Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = 'projects'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    description: Mapped[str] = mapped_column(default='')
    is_archived: Mapped[bool] = mapped_column(default=False)


class Task(Base):
    __tablename__ = 'tasks'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    project_id: Mapped[int]
    status: Mapped[str]
    priority: Mapped[str]
    assignee: Mapped[str]
    due_date: Mapped[str]
    estimated_hours: Mapped[float]
    is_archived: Mapped[bool] = mapped_column(default=False)
    recurrence: Mapped[str] = mapped_column(default='none')
    recurrence_end: Mapped[str] = mapped_column(default='')


class ChecklistItem(Base):
    __tablename__ = 'checklist_items'
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int]
    title: Mapped[str]
    is_done: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[str]


class TaskComment(Base):
    __tablename__ = 'task_comments'
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int]
    author: Mapped[str]
    content: Mapped[str]
    created_at: Mapped[str]


class Label(Base):
    __tablename__ = 'labels'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    color: Mapped[str]


class TaskLabel(Base):
    __tablename__ = 'task_labels'
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int]
    label_id: Mapped[int]


class TaskDependency(Base):
    __tablename__ = 'task_dependencies'
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int]
    depends_on_id: Mapped[int]


class Attachment(Base):
    __tablename__ = 'attachments'
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int]
    original_name: Mapped[str]
    stored_name: Mapped[str]
    size: Mapped[int]
    created_at: Mapped[str]


class Entry(Base):
    __tablename__ = 'entries'
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int]
    task_title: Mapped[str]
    hours: Mapped[float]
    note: Mapped[str]
    created_at: Mapped[str]


class History(Base):
    __tablename__ = 'history'
    id: Mapped[int] = mapped_column(primary_key=True)
    task_title: Mapped[str]
    old_status: Mapped[str]
    new_status: Mapped[str]
    created_at: Mapped[str]


class Profile(Base):
    __tablename__ = 'profile'
    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str]


class WorkspaceSettings(Base):
    __tablename__ = 'workspace_settings'
    id: Mapped[int] = mapped_column(primary_key=True)
    board_name: Mapped[str]
    theme: Mapped[str]
    appearance: Mapped[str] = mapped_column(default='light')
    notifications_enabled: Mapped[bool] = mapped_column(default=True)


class ActiveTimer(Base):
    __tablename__ = 'active_timer'
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int]
    started_at: Mapped[str]
    elapsed_seconds: Mapped[float] = mapped_column(default=0)
    paused_at: Mapped[str | None] = mapped_column(nullable=True)


task_label_index = Index('uq_task_label', TaskLabel.task_id, TaskLabel.label_id, unique=True)
task_dependency_index = Index('uq_task_dependency', TaskDependency.task_id, TaskDependency.depends_on_id, unique=True)
timer_task_index = Index('uq_active_timer_task_id', ActiveTimer.task_id, unique=True)
