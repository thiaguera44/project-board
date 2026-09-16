from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
import os
from pathlib import Path
from typing import Literal
import sys
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

data_dir = os.getenv('PROJECT_BOARD_DATA_DIR')
database_path = Path(data_dir) / 'project_board.db' if data_dir else Path(__file__).resolve().parents[1] / 'project_board.db'
database_path.parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(os.getenv('DATABASE_URL', f"sqlite:///{database_path.as_posix()}"), connect_args={'check_same_thread': False})

bundle_root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2]))
web_dir = Path(os.getenv('PROJECT_BOARD_WEB_DIR', str(bundle_root / 'frontend' / 'dist')))
class Base(DeclarativeBase): pass
class Project(Base):
    __tablename__ = 'projects'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    description: Mapped[str] = mapped_column(default='')
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
class ProjectInput(BaseModel):
    name: str = Field(min_length=1, max_length=120, pattern=r'.*\S.*')
    description: str = Field(default='', max_length=2000)
class TaskInput(BaseModel):
    title: str = Field(min_length=1, max_length=200, pattern=r'.*\S.*')
    project_id: int
    status: Literal['todo','doing','waiting','done'] = 'todo'
    priority: Literal['critical','high','medium','low'] = 'medium'
    assignee: str = Field(default='Thiago', max_length=80)
    due_date: date | None = None
    estimated_hours: float = Field(default=0, ge=0, le=100000)
class EntryInput(BaseModel):
    task_id: int
    hours: float = Field(gt=0, le=24)
    note: str = Field(default='', max_length=1000)
def dump(row): return {c.name: getattr(row,c.name) for c in row.__table__.columns}
@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    yield
app = FastAPI(title='Project Board API', lifespan=lifespan)
@app.middleware('http')
async def desktop_origin_check(request: Request, call_next):
    if os.getenv('PROJECT_BOARD_DESKTOP') == '1' and request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
        origin = request.headers.get('origin')
        if origin and origin != str(request.base_url).rstrip('/'):
            return JSONResponse({'detail': 'Origem não permitida'}, status_code=403)
    return await call_next(request)

@app.get('/')
def home():
    index = web_dir / 'index.html'
    return FileResponse(index) if index.is_file() else {'message':'Project Board API'}
@app.get('/api/board')
def board():
    with Session(engine) as s:
        return {key:[dump(r) for r in s.scalars(select(model).order_by(model.id))] for key,model in [('projects',Project),('tasks',Task),('entries',Entry),('history',History)]}
def save_project(data, project_id=None):
    with Session(engine) as s:
        row = s.get(Project,project_id) if project_id else Project()
        if row is None: raise HTTPException(404,'Projeto não encontrado')
        for k,v in data.model_dump().items(): setattr(row,k,v)
        s.add(row); s.commit(); s.refresh(row)
        return dump(row)
@app.post('/api/projects',status_code=201)
def create_project(data: ProjectInput): return save_project(data)
@app.put('/api/projects/{project_id}')
def update_project(project_id:int,data:ProjectInput): return save_project(data,project_id)
@app.delete('/api/projects/{project_id}')
def delete_project(project_id:int):
    with Session(engine) as s:
        row=s.get(Project,project_id)
        if not row: raise HTTPException(404,'Projeto não encontrado')
        if s.scalar(select(Task).where(Task.project_id==project_id)): raise HTTPException(409,'Remova ou transfira as tarefas deste projeto primeiro.')
        s.delete(row); s.commit()
        return {'ok':True}
def save_task(data,task_id=None):
    with Session(engine) as s:
        if not s.get(Project,data.project_id): raise HTTPException(404,'Projeto não encontrado')
        row=s.get(Task,task_id) if task_id else Task()
        if row is None: raise HTTPException(404,'Tarefa não encontrada')
        if task_id and row.status!=data.status:
            s.add(History(task_title=data.title,old_status=row.status,new_status=data.status,created_at=datetime.now(timezone.utc).isoformat()))
        values=data.model_dump(); values['due_date']=data.due_date.isoformat() if data.due_date else ''
        for k,v in values.items(): setattr(row,k,v)
        s.add(row); s.commit(); s.refresh(row)
        return dump(row)
@app.post('/api/tasks',status_code=201)
def create_task(data:TaskInput): return save_task(data)
@app.put('/api/tasks/{task_id}')
def update_task(task_id:int,data:TaskInput): return save_task(data,task_id)
@app.delete('/api/tasks/{task_id}')
def delete_task(task_id:int):
    with Session(engine) as s:
        row=s.get(Task,task_id)
        if not row: raise HTTPException(404,'Tarefa não encontrada')
        s.delete(row); s.commit()
        return {'ok':True}
@app.post('/api/entries',status_code=201)
def create_entry(data:EntryInput):
    with Session(engine) as s:
        task=s.get(Task,data.task_id)
        if not task: raise HTTPException(404,'Tarefa não encontrada')
        row=Entry(**data.model_dump(),task_title=task.title,created_at=datetime.now(timezone.utc).isoformat())
        s.add(row); s.commit(); s.refresh(row)
        return dump(row)

if web_dir.is_dir():
    app.mount('/assets', StaticFiles(directory=web_dir / 'assets'), name='assets')
