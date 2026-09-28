"""Validation contracts used by the API and backup format."""

from datetime import date
from typing import Literal
from pydantic import BaseModel, Field


class ProfileInput(BaseModel):
    display_name: str = Field(min_length=1, max_length=80, pattern=r'.*\S.*')

class SettingsInput(BaseModel):
    board_name: str = Field(min_length=1, max_length=40, pattern=r'.*\S.*')
    theme: Literal['azul','verde','roxo','terracota','grafite'] = 'azul'
    appearance: Literal['light','dark'] = 'light'
    notifications_enabled: bool = True

class TimerInput(BaseModel): task_id: int
class ProjectInput(BaseModel):
    name: str = Field(min_length=1, max_length=120, pattern=r'.*\S.*')
    description: str = Field(default='', max_length=2000)
class TaskInput(BaseModel):
    title: str = Field(min_length=1, max_length=200, pattern=r'.*\S.*')
    project_id: int
    status: Literal['todo','doing','waiting','done'] = 'todo'
    priority: Literal['critical','high','medium','low'] = 'medium'
    assignee: str = Field(min_length=1, max_length=80, pattern=r'.*\S.*')
    due_date: date | None = None
    estimated_hours: float = Field(default=0, ge=0, le=100000)
    recurrence: Literal['none','daily','weekly','monthly'] = 'none'
    recurrence_end: date | None = None
    label_ids: list[int] = []
    dependency_ids: list[int] = []
class EntryInput(BaseModel):
    task_id: int
    hours: float = Field(gt=0, le=24)
    note: str = Field(default='', max_length=1000)
class ChecklistInput(BaseModel): title: str = Field(min_length=1, max_length=200, pattern=r'.*\S.*')
class ChecklistUpdate(ChecklistInput): is_done: bool
class CommentInput(BaseModel):
    author: str = Field(min_length=1, max_length=80, pattern=r'.*\S.*')
    content: str = Field(min_length=1, max_length=4000, pattern=r'.*\S.*')
class LabelInput(BaseModel):
    name: str = Field(min_length=1, max_length=40, pattern=r'.*\S.*')
    color: str = Field(pattern=r'^#[0-9A-Fa-f]{6}$')
class AttachmentInput(BaseModel):
    original_name: str = Field(min_length=1, max_length=255, pattern=r'.*\S.*')
    content_base64: str

class BackupProject(BaseModel):
    id: int = Field(gt=0); name: str = Field(min_length=1,max_length=120); description: str = Field(default='',max_length=2000); is_archived: bool = False
class BackupTask(BaseModel):
    id: int = Field(gt=0); title: str = Field(min_length=1,max_length=200); project_id: int = Field(gt=0); status: Literal['todo','doing','waiting','done']; priority: Literal['critical','high','medium','low']; assignee: str = Field(min_length=1,max_length=80); due_date: str = Field(default='',pattern=r'^$|^\d{4}-\d{2}-\d{2}$'); estimated_hours: float = Field(ge=0,le=100000); is_archived: bool = False; recurrence: Literal['none','daily','weekly','monthly'] = 'none'; recurrence_end: str = Field(default='',pattern=r'^$|^\d{4}-\d{2}-\d{2}$')
class BackupChecklistItem(BaseModel):
    id: int = Field(gt=0); task_id: int = Field(gt=0); title: str = Field(min_length=1,max_length=200); is_done: bool = False; created_at: str
class BackupComment(BaseModel):
    id: int = Field(gt=0); task_id: int = Field(gt=0); author: str = Field(min_length=1,max_length=80); content: str = Field(min_length=1,max_length=4000); created_at: str
class BackupLabel(BaseModel):
    id: int = Field(gt=0); name: str = Field(min_length=1,max_length=40); color: str = Field(pattern=r'^#[0-9A-Fa-f]{6}$')
class BackupTaskLabel(BaseModel): id: int = Field(gt=0); task_id: int = Field(gt=0); label_id: int = Field(gt=0)
class BackupTaskDependency(BaseModel): id: int = Field(gt=0); task_id: int = Field(gt=0); depends_on_id: int = Field(gt=0)
class BackupAttachment(BaseModel):
    id: int = Field(gt=0); task_id: int = Field(gt=0); original_name: str = Field(min_length=1,max_length=255); stored_name: str = Field(min_length=1,max_length=255); size: int = Field(ge=0,le=20*1024*1024); created_at: str; content_base64: str = ''
class BackupEntry(BaseModel):
    id: int = Field(gt=0); task_id: int = Field(gt=0); task_title: str = Field(min_length=1,max_length=200); hours: float = Field(gt=0,le=24); note: str = Field(default='',max_length=1000); created_at: str
class BackupHistory(BaseModel):
    id: int = Field(gt=0); task_title: str = Field(min_length=1,max_length=200); old_status: Literal['todo','doing','waiting','done']; new_status: Literal['todo','doing','waiting','done']; created_at: str
class BackupTimer(BaseModel):
    id: int = Field(gt=0); task_id: int = Field(gt=0); started_at: str; elapsed_seconds: float = Field(ge=0); paused_at: str | None = None
class BackupPayload(BaseModel):
    format_version: Literal[1]
    exported_at: str
    profile: ProfileInput | None = None
    settings: SettingsInput = SettingsInput(board_name='project-board')
    projects: list[BackupProject] = []; tasks: list[BackupTask] = []; checklist_items: list[BackupChecklistItem] = []; comments: list[BackupComment] = []; labels: list[BackupLabel] = []; task_labels: list[BackupTaskLabel] = []; task_dependencies: list[BackupTaskDependency] = []; attachments: list[BackupAttachment] = []; entries: list[BackupEntry] = []; history: list[BackupHistory] = []; active_timers: list[BackupTimer] = []
