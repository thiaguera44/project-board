from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
import base64
import binascii
import json
import os
from pathlib import Path
import sys
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.task_rules import dependency_change_creates_cycle, graph_has_cycle, next_recurrence_date

data_dir = os.getenv('PROJECT_BOARD_DATA_DIR')
database_path = Path(data_dir) / 'project_board.db' if data_dir else Path(__file__).resolve().parents[1] / 'project_board.db'
database_path.parent.mkdir(parents=True, exist_ok=True)
attachments_dir = database_path.parent / 'attachments'
attachments_dir.mkdir(parents=True, exist_ok=True)
engine = create_engine(os.getenv('DATABASE_URL', f"sqlite:///{database_path.as_posix()}"), connect_args={'check_same_thread': False})

bundle_root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2]))
web_dir = Path(os.getenv('PROJECT_BOARD_WEB_DIR', str(bundle_root / 'frontend' / 'dist')))
from app.models import (
    ActiveTimer, Attachment, Base, ChecklistItem, Entry, History, Label, Profile,
    Project, RunrunBoardMapping, RunrunIntegrationLog, RunrunSettings, Task, TaskComment, TaskDependency, TaskLabel, WorkspaceSettings,
    task_dependency_index, task_label_index, timer_task_index,
)
from app.schemas import (
    AttachmentInput, BackupPayload, ChecklistInput, ChecklistUpdate, CommentInput,
    EntryInput, LabelInput, ProfileInput, ProjectInput, RunrunAutomationInput, RunrunCredentialsInput, RunrunImportInput, RunrunLinkInput, RunrunPreviewInput, RunrunStatusMappingInput, RunrunUserMappingInput, SettingsInput, TaskInput, TimerInput,
)
from app.runrunit import CredentialStore, RunrunClient, RunrunError
credential_store = CredentialStore(database_path.parent / 'runrunit_credentials.dat')
def dump(row): return {c.name: getattr(row,c.name) for c in row.__table__.columns}
@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        columns = {row[1] for row in connection.exec_driver_sql('PRAGMA table_info(active_timer)')}
        if 'elapsed_seconds' not in columns:
            connection.exec_driver_sql('ALTER TABLE active_timer ADD COLUMN elapsed_seconds FLOAT NOT NULL DEFAULT 0')
        if 'paused_at' not in columns:
            connection.exec_driver_sql('ALTER TABLE active_timer ADD COLUMN paused_at VARCHAR')
        settings_columns = {row[1] for row in connection.exec_driver_sql('PRAGMA table_info(workspace_settings)')}
        if 'appearance' not in settings_columns:
            connection.exec_driver_sql("ALTER TABLE workspace_settings ADD COLUMN appearance VARCHAR NOT NULL DEFAULT 'light'")
        if 'notifications_enabled' not in settings_columns:
            connection.exec_driver_sql('ALTER TABLE workspace_settings ADD COLUMN notifications_enabled BOOLEAN NOT NULL DEFAULT 1')
        project_columns = {row[1] for row in connection.exec_driver_sql('PRAGMA table_info(projects)')}
        if 'is_archived' not in project_columns:
            connection.exec_driver_sql('ALTER TABLE projects ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT 0')
        task_columns = {row[1] for row in connection.exec_driver_sql('PRAGMA table_info(tasks)')}
        if 'is_archived' not in task_columns:
            connection.exec_driver_sql('ALTER TABLE tasks ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT 0')
        if 'recurrence' not in task_columns:
            connection.exec_driver_sql("ALTER TABLE tasks ADD COLUMN recurrence VARCHAR NOT NULL DEFAULT 'none'")
        if 'recurrence_end' not in task_columns:
            connection.exec_driver_sql("ALTER TABLE tasks ADD COLUMN recurrence_end VARCHAR NOT NULL DEFAULT ''")
        if 'runrunit_id' not in project_columns:
            connection.exec_driver_sql('ALTER TABLE projects ADD COLUMN runrunit_id INTEGER')
        if 'runrunit_id' not in task_columns:
            connection.exec_driver_sql('ALTER TABLE tasks ADD COLUMN runrunit_id INTEGER')
        if 'runrunit_board_id' not in task_columns:
            connection.exec_driver_sql('ALTER TABLE tasks ADD COLUMN runrunit_board_id INTEGER')
        if 'runrunit_task_title' not in task_columns:
            connection.exec_driver_sql("ALTER TABLE tasks ADD COLUMN runrunit_task_title VARCHAR NOT NULL DEFAULT ''")
        if 'runrunit_board_name' not in task_columns:
            connection.exec_driver_sql("ALTER TABLE tasks ADD COLUMN runrunit_board_name VARCHAR NOT NULL DEFAULT ''")
        if 'runrunit_origin' not in task_columns:
            connection.exec_driver_sql("ALTER TABLE tasks ADD COLUMN runrunit_origin VARCHAR NOT NULL DEFAULT ''")
        if 'runrunit_last_synced_status' not in task_columns:
            connection.exec_driver_sql("ALTER TABLE tasks ADD COLUMN runrunit_last_synced_status VARCHAR NOT NULL DEFAULT ''")
        if 'runrunit_status_error' not in task_columns:
            connection.exec_driver_sql("ALTER TABLE tasks ADD COLUMN runrunit_status_error VARCHAR NOT NULL DEFAULT ''")
        if 'runrunit_snapshot' not in task_columns:
            connection.exec_driver_sql("ALTER TABLE tasks ADD COLUMN runrunit_snapshot VARCHAR NOT NULL DEFAULT ''")
        entry_columns = {row[1] for row in connection.exec_driver_sql('PRAGMA table_info(entries)')}
        if 'runrunit_synced_at' not in entry_columns:
            connection.exec_driver_sql('ALTER TABLE entries ADD COLUMN runrunit_synced_at VARCHAR')
        if 'runrunit_work_period_id' not in entry_columns:
            connection.exec_driver_sql('ALTER TABLE entries ADD COLUMN runrunit_work_period_id INTEGER')
        if 'runrunit_sync_attempted_at' not in entry_columns:
            connection.exec_driver_sql('ALTER TABLE entries ADD COLUMN runrunit_sync_attempted_at VARCHAR')
        if 'runrunit_sync_error' not in entry_columns:
            connection.exec_driver_sql("ALTER TABLE entries ADD COLUMN runrunit_sync_error VARCHAR NOT NULL DEFAULT ''")
        runrun_settings_columns = {row[1] for row in connection.exec_driver_sql('PRAGMA table_info(runrunit_settings)')}
        if 'last_sync_at' not in runrun_settings_columns:
            connection.exec_driver_sql('ALTER TABLE runrunit_settings ADD COLUMN last_sync_at VARCHAR')
        if 'mapped_user_id' not in runrun_settings_columns:
            connection.exec_driver_sql("ALTER TABLE runrunit_settings ADD COLUMN mapped_user_id VARCHAR NOT NULL DEFAULT ''")
        if 'mapped_user_name' not in runrun_settings_columns:
            connection.exec_driver_sql("ALTER TABLE runrunit_settings ADD COLUMN mapped_user_name VARCHAR NOT NULL DEFAULT ''")
        if 'auto_sync_hours' not in runrun_settings_columns:
            connection.exec_driver_sql('ALTER TABLE runrunit_settings ADD COLUMN auto_sync_hours BOOLEAN NOT NULL DEFAULT 0')
    timer_task_index.create(engine, checkfirst=True)
    task_label_index.create(engine, checkfirst=True)
    task_dependency_index.create(engine, checkfirst=True)
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
@app.get('/timer')
def timer_window():
    page = web_dir / 'timer.html'
    if not page.is_file(): raise HTTPException(404,'Janela do cronômetro não encontrada')
    return FileResponse(page)
@app.get('/api/board')
def board():
    with Session(engine) as s:
        projects = list(s.scalars(select(Project).order_by(Project.id)))
        tasks = list(s.scalars(select(Task).order_by(Task.id)))
        active_project_ids = {row.id for row in projects if not row.is_archived}
        task_labels = list(s.scalars(select(TaskLabel).order_by(TaskLabel.id)))
        dependencies = list(s.scalars(select(TaskDependency).order_by(TaskDependency.id)))
        def task_dump(row):
            return {**dump(row), 'label_ids': [item.label_id for item in task_labels if item.task_id == row.id], 'dependency_ids': [item.depends_on_id for item in dependencies if item.task_id == row.id]}
        result = {
            'projects': [dump(row) for row in projects if not row.is_archived],
            'tasks': [task_dump(row) for row in tasks if not row.is_archived and row.project_id in active_project_ids],
            'archived_projects': [dump(row) for row in projects if row.is_archived],
            'archived_tasks': [task_dump(row) for row in tasks if row.is_archived and row.project_id in active_project_ids],
            'checklist_items': [dump(row) for row in s.scalars(select(ChecklistItem).order_by(ChecklistItem.id))],
            'comments': [dump(row) for row in s.scalars(select(TaskComment).order_by(TaskComment.id))],
            'attachments': [dump(row) for row in s.scalars(select(Attachment).order_by(Attachment.id))],
            'labels': [dump(row) for row in s.scalars(select(Label).order_by(Label.name))],
            'entries': [dump(row) for row in s.scalars(select(Entry).order_by(Entry.id))],
            'history': [dump(row) for row in s.scalars(select(History).order_by(History.id))],
        }
        result['active_timers'] = [dump(timer) for timer in s.scalars(select(ActiveTimer).order_by(ActiveTimer.id))]
        return result
@app.get('/api/profile')
def get_profile():
    with Session(engine) as s:
        row = s.get(Profile, 1)
        return {'display_name': row.display_name if row else ''}
@app.put('/api/profile')
def update_profile(data: ProfileInput):
    with Session(engine) as s:
        row = s.get(Profile, 1) or Profile(id=1)
        row.display_name = data.display_name.strip()
        s.add(row); s.commit()
        return {'display_name': row.display_name}
@app.get('/api/settings')
def get_settings():
    with Session(engine) as s:
        row = s.get(WorkspaceSettings, 1)
        return {
            'board_name': row.board_name if row else 'project-board',
            'theme': row.theme if row else 'azul',
            'appearance': row.appearance if row else 'light',
            'notifications_enabled': row.notifications_enabled if row else True,
        }
@app.put('/api/settings')
def update_settings(data: SettingsInput):
    with Session(engine) as s:
        row = s.get(WorkspaceSettings, 1) or WorkspaceSettings(id=1)
        row.board_name = data.board_name.strip()
        row.theme = data.theme
        row.appearance = data.appearance
        row.notifications_enabled = data.notifications_enabled
        s.add(row); s.commit()
        return dump(row)

def runrun_client():
    credentials = credential_store.load()
    if not credentials: raise HTTPException(409, 'Configure a conexão com o Runrun.it primeiro.')
    return RunrunClient(credentials['app_key'], credentials['user_token'])

def add_runrun_log(operation:str,status:str,message:str):
    with Session(engine) as s:
        s.add(RunrunIntegrationLog(operation=operation,status=status,message=message[:1000],created_at=datetime.now(timezone.utc).isoformat()));s.commit()

def runrun_rows(payload, key):
    if isinstance(payload, list): return payload
    if isinstance(payload, dict): return payload.get(key, payload.get('data', []))
    return []

@app.get('/api/integrations/runrunit')
def runrun_status():
    with Session(engine) as s:
        settings=s.get(RunrunSettings,1)
        imported_board_ids=sorted({row for row in s.scalars(select(Task.runrunit_board_id).where(Task.runrunit_origin=='imported')) if row is not None})
        pending=failed=synced=pending_statuses=0
        for entry in s.scalars(select(Entry)):
            task=s.get(Task,entry.task_id)
            if not task or not task.runrunit_id: continue
            if entry.runrunit_synced_at: synced+=1
            elif entry.runrunit_sync_error: failed+=1
            else: pending+=1
        for task in s.scalars(select(Task)):
            if task.runrunit_id and task.status!=task.runrunit_last_synced_status: pending_statuses+=1
        return {'configured': credential_store.path.is_file(), 'board_id': settings.board_id if settings else None, 'board_name': settings.board_name if settings else '', 'last_sync_at':settings.last_sync_at if settings else None, 'mapped_user_id':settings.mapped_user_id if settings else '', 'mapped_user_name':settings.mapped_user_name if settings else '', 'auto_sync_hours':settings.auto_sync_hours if settings else False, 'pending_hours': pending, 'failed_hours': failed, 'synced_hours': synced, 'pending_statuses':pending_statuses, 'imported_board_ids': imported_board_ids}

@app.get('/api/integrations/runrunit/hours')
def runrun_hour_records():
    with Session(engine) as s:
        result=[]
        for entry in s.scalars(select(Entry).order_by(Entry.id.desc())):
            task=s.get(Task,entry.task_id)
            if not task or not task.runrunit_id: continue
            state='sent' if entry.runrunit_synced_at else ('failed' if entry.runrunit_sync_error else 'pending')
            result.append({**dump(entry),'state':state,'remote_task_id':task.runrunit_id,'remote_task_title':task.runrunit_task_title or task.title})
        return result

@app.get('/api/integrations/runrunit/history')
def runrun_history():
    with Session(engine) as s: return [dump(row) for row in s.scalars(select(RunrunIntegrationLog).order_by(RunrunIntegrationLog.id.desc()).limit(100))]

@app.put('/api/integrations/runrunit')
def configure_runrun(data: RunrunCredentialsInput):
    client=RunrunClient(data.app_key.strip(),data.user_token.strip())
    try: client.test()
    except RunrunError as exc: raise HTTPException(502,str(exc)) from exc
    credential_store.save(data.app_key,data.user_token)
    return {'ok':True,'configured':True}

@app.get('/api/integrations/runrunit/boards')
def runrun_boards():
    try: rows=runrun_rows(runrun_client().boards(),'boards')
    except RunrunError as exc: raise HTTPException(502,str(exc)) from exc
    return [{'id':row.get('id'),'name':row.get('name') or row.get('title') or f"Quadro {row.get('id')}"} for row in rows if row.get('id')]

@app.get('/api/integrations/runrunit/users')
def runrun_users():
    try: rows=runrun_rows(runrun_client().users(),'users')
    except RunrunError as exc: raise HTTPException(502,str(exc)) from exc
    result=[]
    for row in rows:
        user_id=row.get('id') or row.get('user_id')
        if user_id is not None: result.append({'id':str(user_id),'name':row.get('name') or row.get('user_name') or row.get('email') or str(user_id)})
    return sorted(result,key=lambda row:str(row['name']).casefold())

@app.put('/api/integrations/runrunit/user-mapping')
def save_runrun_user_mapping(data:RunrunUserMappingInput):
    user_id=data.user_id.strip();user_name=data.user_name.strip()
    if user_id:
        users=runrun_users();matched=next((row for row in users if row['id']==user_id),None)
        if not matched: raise HTTPException(422,'O usuário selecionado não foi encontrado no Runrun.it.')
        user_name=matched['name']
    with Session(engine) as s:
        row=s.get(RunrunSettings,1) or RunrunSettings(id=1)
        row.mapped_user_id=user_id;row.mapped_user_name=user_name;s.add(row);s.commit()
        return {'user_id':user_id,'user_name':user_name}

@app.put('/api/integrations/runrunit/automation')
def save_runrun_automation(data:RunrunAutomationInput):
    with Session(engine) as s:
        row=s.get(RunrunSettings,1) or RunrunSettings(id=1)
        row.auto_sync_hours=data.auto_sync_hours;s.add(row);s.commit()
        return {'auto_sync_hours':row.auto_sync_hours}

@app.get('/api/integrations/runrunit/boards/{board_id}/stages')
def runrun_stages(board_id:int):
    try: rows=runrun_rows(runrun_client().stages(board_id),'stages')
    except RunrunError as exc: raise HTTPException(502,str(exc)) from exc
    return [{'id':row.get('id'),'name':row.get('name') or f"Etapa {row.get('id')}",'stage_group':row.get('stage_group') or 'opened'} for row in rows if row.get('id')]

@app.get('/api/integrations/runrunit/boards/{board_id}/status-mapping')
def get_runrun_status_mapping(board_id:int):
    with Session(engine) as s:
        row=s.get(RunrunBoardMapping,board_id)
        return dump(row) if row else {'board_id':board_id,'enabled':False,'todo_stage_id':None,'doing_stage_id':None,'waiting_stage_id':None,'done_stage_id':None}

@app.put('/api/integrations/runrunit/boards/{board_id}/status-mapping')
def save_runrun_status_mapping(board_id:int,data:RunrunStatusMappingInput):
    values=data.model_dump()
    if data.enabled and any(values[key] is None for key in ('todo_stage_id','doing_stage_id','waiting_stage_id','done_stage_id')):
        raise HTTPException(422,'Selecione uma etapa do Runrun.it para cada coluna local.')
    try: valid_ids={row['id'] for row in runrun_stages(board_id)}
    except HTTPException: raise
    chosen={value for key,value in values.items() if key.endswith('_stage_id') and value is not None}
    if not chosen.issubset(valid_ids): raise HTTPException(422,'Uma das etapas selecionadas não pertence a este quadro.')
    with Session(engine) as s:
        row=s.get(RunrunBoardMapping,board_id) or RunrunBoardMapping(board_id=board_id)
        for key,value in values.items(): setattr(row,key,value)
        s.add(row);s.commit();s.refresh(row);return dump(row)

def sync_one_runrun_status(task_id:int):
    with Session(engine) as s:
        task=s.get(Task,task_id)
        if not task or not task.runrunit_id or not task.runrunit_board_id: return False
        mapping=s.get(RunrunBoardMapping,task.runrunit_board_id)
        if not mapping or not mapping.enabled: return False
        stage_id=getattr(mapping,f'{task.status}_stage_id')
        if not stage_id: return False
        try:
            runrun_client().move_task(task.runrunit_id,stage_id)
            task.runrunit_last_synced_status=task.status;task.runrunit_status_error='';s.add(task);s.commit();return True
        except RunrunError as exc:
            task.runrunit_status_error=str(exc)[:1000];s.add(task);s.commit();return False

@app.post('/api/integrations/runrunit/sync-statuses')
def sync_runrun_statuses():
    with Session(engine) as s: ids=[task.id for task in s.scalars(select(Task)) if task.runrunit_id and task.status!=task.runrunit_last_synced_status]
    sent=sum(1 for task_id in ids if sync_one_runrun_status(task_id))
    failed=len(ids)-sent;add_runrun_log('status','success' if not failed else 'error',f'{sent} status enviados; {failed} falharam.')
    return {'ok':not failed,'sent':sent,'failed':failed}

def imported_status(row, closed_stages):
    state=str(row.get('state') or '').lower()
    if state in {'closed','done','completed'} or row.get('board_stage_id') in closed_stages: return 'done'
    if state in {'working_on','working','in_progress'}: return 'doing'
    stage=str(row.get('board_stage_name') or '').lower()
    if 'esper' in stage or 'aguard' in stage: return 'waiting'
    return 'todo'

@app.post('/api/integrations/runrunit/preview')
def preview_runrun_board(data: RunrunPreviewInput):
    client=runrun_client()
    try:
        remote_projects=runrun_rows(client.projects(),'projects')
        stages=runrun_rows(client.stages(data.board_id),'stages')
        remote_tasks=client.tasks(data.board_id)
    except RunrunError as exc: raise HTTPException(502,str(exc)) from exc
    project_data={row.get('id'):row for row in remote_projects}
    closed_stages={row.get('id') for row in stages if str(row.get('stage_group') or '').lower() in {'closed','done'}}
    tasks=[]
    for row in remote_tasks:
        remote_id=row.get('id')
        if not remote_id: continue
        status=imported_status(row,closed_stages)
        if not data.include_completed and status=='done': continue
        project=project_data.get(row.get('project_id'),{})
        tasks.append({
            'id':remote_id,'title':str(row.get('title') or 'Tarefa do Runrun.it'),
            'project_id':row.get('project_id'),'project_name':project.get('name') or row.get('project_name') or 'Sem projeto',
            'status':status,'due_date':str(row.get('desired_date') or row.get('due_date') or '')[:10],
            'already_imported':False,
        })
    remote_by_id={row.get('id'):row for row in remote_tasks}
    with Session(engine) as s:
        local_by_remote={row.runrunit_id:row for row in s.scalars(select(Task)) if row.runrunit_id is not None}
        profile=s.get(Profile,1);fallback=profile.display_name if profile else 'Runrun.it'
        for task in tasks:
            local=local_by_remote.get(task['id']);task['already_imported']=local is not None;task['changes']=[];task['conflicts']=[]
            if not local: continue
            remote=remote_by_id[task['id']];assignments=remote.get('assignments') or []
            assignee=remote.get('responsible_name') or remote.get('user_name') or (assignments[0].get('user_name') if assignments and isinstance(assignments[0],dict) else '') or fallback
            expected={'title':task['title'],'status':task['status'],'due_date':task['due_date'],'estimated_hours':max(0,float(remote.get('time_estimated') or remote.get('estimated_seconds') or 0)/3600),'assignee':str(assignee)[:80],'priority':'critical' if remote.get('is_urgent') else 'medium'}
            task['changes']=[key for key,value in expected.items() if getattr(local,key)!=value]
            try: snapshot=json.loads(local.runrunit_snapshot) if local.runrunit_snapshot else {}
            except (TypeError,ValueError): snapshot={}
            task['conflicts']=[key for key in task['changes'] if key in snapshot and getattr(local,key)!=snapshot[key] and expected[key]!=snapshot[key]]
    scanned=len(tasks)
    if data.incremental: tasks=[task for task in tasks if not task['already_imported'] or task['changes']]
    tasks.sort(key=lambda row:(str(row['project_name']).casefold(),str(row['title']).casefold()))
    return {'tasks':tasks,'total':len(tasks),'scanned':scanned,'incremental':data.incremental,'completed_hidden':sum(1 for row in remote_tasks if imported_status(row,closed_stages)=='done') if not data.include_completed else 0}

@app.post('/api/integrations/runrunit/link')
def link_runrun_task(data: RunrunLinkInput):
    client=runrun_client()
    try:
        remote_tasks=client.tasks(data.board_id)
        stages=runrun_rows(client.stages(data.board_id),'stages')
    except RunrunError as exc: raise HTTPException(502,str(exc)) from exc
    remote=next((row for row in remote_tasks if row.get('id')==data.runrunit_task_id),None)
    if not remote: raise HTTPException(404,'A tarefa selecionada não foi encontrada no Runrun.it.')
    with Session(engine) as s:
        task=s.get(Task,data.task_id)
        if not task: raise HTTPException(404,'Tarefa local não encontrada.')
        duplicate=s.scalar(select(Task).where((Task.runrunit_id==data.runrunit_task_id)&(Task.id!=data.task_id)))
        if duplicate: raise HTTPException(409,f'A tarefa do Runrun.it já está vinculada a “{duplicate.title}”.')
        task.runrunit_id=data.runrunit_task_id;task.runrunit_board_id=data.board_id
        task.runrunit_task_title=str(remote.get('title') or f'Tarefa {data.runrunit_task_id}')[:200]
        closed={row.get('id') for row in stages if str(row.get('stage_group') or '').lower() in {'closed','done'}}
        task.runrunit_board_name=data.board_name.strip()[:200];task.runrunit_origin='linked'
        task.runrunit_last_synced_status=imported_status(remote,closed);task.runrunit_status_error=''
        s.add(task);s.commit();s.refresh(task)
        pending=sum(1 for row in s.scalars(select(Entry).where(Entry.task_id==task.id)) if not row.runrunit_synced_at)
        return {'ok':True,'task':dump(task),'pending_hours':pending}

@app.delete('/api/integrations/runrunit/link/{task_id}')
def unlink_runrun_task(task_id: int):
    with Session(engine) as s:
        task=s.get(Task,task_id)
        if not task: raise HTTPException(404,'Tarefa local não encontrada.')
        task.runrunit_id=None;task.runrunit_board_id=None;task.runrunit_task_title='';task.runrunit_board_name='';task.runrunit_origin='';task.runrunit_last_synced_status='';task.runrunit_status_error=''
        s.add(task);s.commit()
        return {'ok':True}

@app.post('/api/integrations/runrunit/import')
def import_runrun_board(data: RunrunImportInput):
    client=runrun_client()
    try:
        remote_projects=runrun_rows(client.projects(),'projects')
        stages=runrun_rows(client.stages(data.board_id),'stages')
        remote_tasks=client.tasks(data.board_id)
    except RunrunError as exc: raise HTTPException(502,str(exc)) from exc
    selected_ids=set(data.task_ids) if data.task_ids is not None else None
    if selected_ids is not None: remote_tasks=[row for row in remote_tasks if row.get('id') in selected_ids]
    project_data={row.get('id'):row for row in remote_projects}
    closed_stages={row.get('id') for row in stages if str(row.get('stage_group') or '').lower() in {'closed','done'}}
    created_projects=created_tasks=updated_tasks=0
    backup_created=engine.url.database!=':memory:'
    if backup_created:
        backups=database_path.parent/'automatic_backups';backups.mkdir(parents=True,exist_ok=True)
        path=backups/f"before_runrunit_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
        path.write_text(json.dumps(export_backup(),ensure_ascii=False,indent=2),encoding='utf-8')
        for old in sorted(backups.glob('before_runrunit_*.json'),reverse=True)[10:]: old.unlink(missing_ok=True)
    with Session(engine) as s:
        profile=s.get(Profile,1)
        settings=s.get(RunrunSettings,1)
        fallback_assignee=(settings.mapped_user_name if settings and settings.mapped_user_name else '') or (profile.display_name if profile else 'Runrun.it')
        local_projects={row.runrunit_id:row for row in s.scalars(select(Project)) if row.runrunit_id}
        for remote in remote_tasks:
            remote_project_id=remote.get('project_id')
            local_project=local_projects.get(remote_project_id)
            if not local_project:
                source=project_data.get(remote_project_id,{})
                name=source.get('name') or remote.get('project_name') or data.board_name or 'Runrun.it'
                local_project=Project(name=str(name)[:120],description=str(source.get('description') or '')[:2000],is_archived=False,runrunit_id=remote_project_id)
                s.add(local_project);s.flush();local_projects[remote_project_id]=local_project;created_projects+=1
            remote_id=remote.get('id')
            if not remote_id: continue
            task=s.scalar(select(Task).where(Task.runrunit_id==remote_id));existing=task is not None
            if existing: updated_tasks+=1
            else: task=Task();created_tasks+=1
            assignments=remote.get('assignments') or []
            assignee=remote.get('responsible_name') or remote.get('user_name') or (assignments[0].get('user_name') if assignments and isinstance(assignments[0],dict) else '') or fallback_assignee
            due=str(remote.get('desired_date') or remote.get('due_date') or '')[:10]
            seconds=remote.get('time_estimated') or remote.get('estimated_seconds') or 0
            incoming={'title':str(remote.get('title') or 'Tarefa do Runrun.it')[:200],'status':imported_status(remote,closed_stages),'priority':'critical' if remote.get('is_urgent') else 'medium','assignee':str(assignee)[:80],'due_date':due if len(due)==10 else '','estimated_hours':max(0,float(seconds or 0)/3600)}
            task.project_id=local_project.id
            for field,value in incoming.items():
                if not existing or field in data.update_fields: setattr(task,field,value)
            task.is_archived=False;task.recurrence='none';task.recurrence_end=''
            task.runrunit_id=remote_id;task.runrunit_board_id=data.board_id
            task.runrunit_task_title=incoming['title'];task.runrunit_board_name=data.board_name.strip();task.runrunit_origin='imported';task.runrunit_last_synced_status=incoming['status'];task.runrunit_status_error='';task.runrunit_snapshot=json.dumps(incoming,ensure_ascii=False);s.add(task)
        settings=s.get(RunrunSettings,1) or RunrunSettings(id=1)
        settings.board_id=data.board_id;settings.board_name=data.board_name.strip();settings.last_sync_at=datetime.now(timezone.utc).isoformat();s.add(settings);s.commit()
    add_runrun_log('import','success',f'{created_tasks} tarefas adicionadas e {updated_tasks} atualizadas no quadro {data.board_name or data.board_id}.')
    return {'ok':True,'projects_created':created_projects,'tasks_created':created_tasks,'tasks_updated':updated_tasks,'backup_created':backup_created}

@app.delete('/api/integrations/runrunit/import/{board_id}')
def remove_runrun_import(board_id: int):
    attachment_paths=[]
    with Session(engine) as s:
        tasks=list(s.scalars(select(Task).where((Task.runrunit_board_id==board_id)&(Task.runrunit_origin=='imported'))))
        task_ids=[task.id for task in tasks]
        if task_ids and s.scalar(select(ActiveTimer).where(ActiveTimer.task_id.in_(task_ids))):
            raise HTTPException(409,'Pare ou descarte os cronômetros das tarefas importadas antes de removê-las.')
        project_ids={task.project_id for task in tasks}
        for task in tasks:
            for model in (ChecklistItem,TaskComment,TaskLabel):
                for row in s.scalars(select(model).where(model.task_id==task.id)): s.delete(row)
            for row in s.scalars(select(TaskDependency).where((TaskDependency.task_id==task.id)|(TaskDependency.depends_on_id==task.id))): s.delete(row)
            for attachment in s.scalars(select(Attachment).where(Attachment.task_id==task.id)):
                attachment_paths.append(attachments_dir/attachment.stored_name);s.delete(attachment)
            s.delete(task)
        s.flush();projects_removed=projects_kept=0
        for project_id in project_ids:
            project=s.get(Project,project_id)
            if not project or project.runrunit_id is None: continue
            remaining=list(s.scalars(select(Task).where(Task.project_id==project_id)))
            if remaining:
                if not any(task.runrunit_id for task in remaining): project.runrunit_id=None
                s.add(project);projects_kept+=1
            else: s.delete(project);projects_removed+=1
        settings=s.get(RunrunSettings,1)
        if settings and settings.board_id==board_id:
            settings.board_id=None;settings.board_name='';s.add(settings)
        s.commit()
    for path in attachment_paths: path.unlink(missing_ok=True)
    return {'ok':True,'tasks_removed':len(tasks),'projects_removed':projects_removed,'projects_kept':projects_kept}

def send_runrun_hours(task_id: int | None = None, failed_only: bool = False):
    client=runrun_client();sent=0;errors=[]
    with Session(engine) as s:
        entries=list(s.scalars(select(Entry).order_by(Entry.id)))
        for entry in entries:
            if task_id is not None and entry.task_id!=task_id: continue
            task=s.get(Task,entry.task_id)
            if not task or not task.runrunit_id or entry.runrunit_synced_at: continue
            if failed_only and not entry.runrunit_sync_error: continue
            attempted_at=datetime.now(timezone.utc).isoformat()
            try:
                response=client.add_manual_work(task.runrunit_id,max(1,round(entry.hours*3600)),entry.created_at[:10])
                entry.runrunit_synced_at=attempted_at
                entry.runrunit_work_period_id=response.get('id') if isinstance(response,dict) else None
                entry.runrunit_sync_attempted_at=attempted_at;entry.runrunit_sync_error=''
                s.add(entry);s.commit();sent+=1
            except RunrunError as exc:
                s.rollback()
                failed=s.get(Entry,entry.id);failed.runrunit_sync_attempted_at=attempted_at;failed.runrunit_sync_error=str(exc)[:1000]
                s.add(failed);s.commit();errors.append({'entry_id':entry.id,'message':str(exc)})
        add_runrun_log('hours','success' if not errors else 'error',f'{sent} registros de horas enviados; {len(errors)} falharam.')
        return {'ok':not errors,'sent':sent,'errors':errors}

@app.post('/api/integrations/runrunit/sync-hours')
def sync_runrun_hours(task_id: int | None = None): return send_runrun_hours(task_id)

@app.post('/api/integrations/runrunit/retry-hours')
def retry_runrun_hours(): return send_runrun_hours(failed_only=True)

@app.post('/api/integrations/runrunit/tasks/{task_id}/sync-hours')
def sync_runrun_task_hours(task_id: int): return sync_runrun_hours(task_id)
@app.get('/api/backup')
def export_backup():
    with Session(engine) as s:
        profile = s.get(Profile, 1)
        settings = s.get(WorkspaceSettings, 1)
        attachment_rows = list(s.scalars(select(Attachment).order_by(Attachment.id)))
        attachment_backup = []
        for row in attachment_rows:
            path = attachments_dir / row.stored_name
            attachment_backup.append({**dump(row), 'content_base64': base64.b64encode(path.read_bytes()).decode('ascii') if path.is_file() else ''})
        return {
            'format_version': 1,
            'exported_at': datetime.now(timezone.utc).isoformat(),
            'profile': {'display_name': profile.display_name} if profile else None,
            'settings': {
                'board_name': settings.board_name if settings else 'project-board',
                'theme': settings.theme if settings else 'azul',
                'appearance': settings.appearance if settings else 'light',
                'notifications_enabled': settings.notifications_enabled if settings else True,
            },
            'projects': [dump(row) for row in s.scalars(select(Project).order_by(Project.id))],
            'tasks': [dump(row) for row in s.scalars(select(Task).order_by(Task.id))],
            'checklist_items': [dump(row) for row in s.scalars(select(ChecklistItem).order_by(ChecklistItem.id))],
            'comments': [dump(row) for row in s.scalars(select(TaskComment).order_by(TaskComment.id))],
            'attachments': attachment_backup,
            'labels': [dump(row) for row in s.scalars(select(Label).order_by(Label.id))],
            'task_labels': [dump(row) for row in s.scalars(select(TaskLabel).order_by(TaskLabel.id))],
            'task_dependencies': [dump(row) for row in s.scalars(select(TaskDependency).order_by(TaskDependency.id))],
            'entries': [dump(row) for row in s.scalars(select(Entry).order_by(Entry.id))],
            'history': [dump(row) for row in s.scalars(select(History).order_by(History.id))],
            'active_timers': [dump(row) for row in s.scalars(select(ActiveTimer).order_by(ActiveTimer.id))],
        }
@app.post('/api/backup/restore')
def restore_backup(data: BackupPayload):
    def unique_ids(rows, label):
        ids = [row.id for row in rows]
        if len(ids) != len(set(ids)):
            raise HTTPException(422, f'O backup contém identificadores duplicados em {label}.')
    unique_ids(data.projects, 'projetos'); unique_ids(data.tasks, 'tarefas')
    unique_ids(data.checklist_items, 'checklist'); unique_ids(data.comments, 'comentários'); unique_ids(data.attachments, 'anexos'); unique_ids(data.labels, 'etiquetas'); unique_ids(data.task_labels, 'vínculos de etiquetas'); unique_ids(data.task_dependencies, 'dependências')
    unique_ids(data.entries, 'horas'); unique_ids(data.history, 'histórico'); unique_ids(data.active_timers, 'cronômetros')
    project_ids = {row.id for row in data.projects}
    task_ids = {row.id for row in data.tasks}
    if any(row.project_id not in project_ids for row in data.tasks):
        raise HTTPException(422, 'O backup contém tarefas ligadas a projetos inexistentes.')
    if any(row.task_id not in task_ids for row in data.checklist_items):
        raise HTTPException(422, 'O backup contém itens de checklist ligados a tarefas inexistentes.')
    if any(row.task_id not in task_ids for row in data.comments):
        raise HTTPException(422, 'O backup contém comentários ligados a tarefas inexistentes.')
    if any(row.task_id not in task_ids for row in data.attachments):
        raise HTTPException(422, 'O backup contém anexos ligados a tarefas inexistentes.')
    attachment_contents = {}
    for row in data.attachments:
        if row.stored_name != Path(row.stored_name).name or row.stored_name in attachment_contents: raise HTTPException(422, 'O backup contém nomes de anexos inválidos.')
        try: content = base64.b64decode(row.content_base64, validate=True)
        except (ValueError, binascii.Error): raise HTTPException(422, 'O backup contém um anexo inválido.')
        if len(content) != row.size or len(content) > 20*1024*1024: raise HTTPException(422, 'O tamanho de um anexo do backup é inválido.')
        attachment_contents[row.stored_name] = content
    label_ids = {row.id for row in data.labels}
    if any(row.task_id not in task_ids or row.label_id not in label_ids for row in data.task_labels):
        raise HTTPException(422, 'O backup contém vínculos de etiquetas inválidos.')
    if len({(row.task_id,row.label_id) for row in data.task_labels}) != len(data.task_labels):
        raise HTTPException(422, 'O backup contém etiquetas duplicadas na mesma tarefa.')
    if any(row.task_id not in task_ids or row.depends_on_id not in task_ids or row.task_id==row.depends_on_id for row in data.task_dependencies):
        raise HTTPException(422, 'O backup contém dependências de tarefas inválidas.')
    if len({(row.task_id,row.depends_on_id) for row in data.task_dependencies}) != len(data.task_dependencies):
        raise HTTPException(422, 'O backup contém dependências duplicadas.')
    dependency_graph:dict[int,list[int]]={}
    for row in data.task_dependencies: dependency_graph.setdefault(row.task_id,[]).append(row.depends_on_id)
    if graph_has_cycle(dependency_graph):
        raise HTTPException(422, 'O backup contém um ciclo entre dependências de tarefas.')
    if any(row.task_id not in task_ids for row in data.active_timers):
        raise HTTPException(422, 'O backup contém cronômetros ligados a tarefas inexistentes.')
    archived_project_ids = {row.id for row in data.projects if row.is_archived}
    archived_task_ids = {row.id for row in data.tasks if row.is_archived or row.project_id in archived_project_ids}
    if any(row.task_id in archived_task_ids for row in data.active_timers):
        raise HTTPException(422, 'O backup contém cronômetros em tarefas arquivadas.')
    if len({row.task_id for row in data.active_timers}) != len(data.active_timers):
        raise HTTPException(422, 'O backup contém mais de um cronômetro para a mesma tarefa.')
    with Session(engine) as s:
        try:
            for model in (ActiveTimer, Attachment, TaskDependency, TaskLabel, TaskComment, ChecklistItem, Label, Entry, History, Task, Project, Profile, WorkspaceSettings):
                for row in s.scalars(select(model)):
                    s.delete(row)
            s.flush()
            s.add_all(Project(**row.model_dump()) for row in data.projects)
            s.add_all(Task(**row.model_dump()) for row in data.tasks)
            s.add_all(ChecklistItem(**row.model_dump()) for row in data.checklist_items)
            s.add_all(TaskComment(**row.model_dump()) for row in data.comments)
            s.add_all(Attachment(**row.model_dump(exclude={'content_base64'})) for row in data.attachments)
            s.add_all(Label(**row.model_dump()) for row in data.labels)
            s.add_all(TaskLabel(**row.model_dump()) for row in data.task_labels)
            s.add_all(TaskDependency(**row.model_dump()) for row in data.task_dependencies)
            s.add_all(Entry(**row.model_dump()) for row in data.entries)
            s.add_all(History(**row.model_dump()) for row in data.history)
            s.add_all(ActiveTimer(**row.model_dump()) for row in data.active_timers)
            if data.profile:
                s.add(Profile(id=1, display_name=data.profile.display_name.strip()))
            s.add(WorkspaceSettings(id=1, **data.settings.model_dump()))
            s.commit()
        except Exception:
            s.rollback()
            raise
    for path in attachments_dir.iterdir():
        if path.is_file(): path.unlink()
    for stored_name, content in attachment_contents.items():
        (attachments_dir / Path(stored_name).name).write_bytes(content)
    return {'ok': True, 'projects': len(data.projects), 'tasks': len(data.tasks), 'entries': len(data.entries), 'checklist_items': len(data.checklist_items)}
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
@app.post('/api/projects/{project_id}/archive')
def archive_project(project_id:int):
    with Session(engine) as s:
        row=s.get(Project,project_id)
        if not row: raise HTTPException(404,'Projeto não encontrado')
        task_ids=list(s.scalars(select(Task.id).where(Task.project_id==project_id)))
        if task_ids and s.scalar(select(ActiveTimer).where(ActiveTimer.task_id.in_(task_ids))):
            raise HTTPException(409,'Pare ou descarte os cronômetros deste projeto antes de arquivá-lo.')
        row.is_archived=True; s.commit()
        return {'ok':True}
@app.post('/api/projects/{project_id}/restore')
def restore_project(project_id:int):
    with Session(engine) as s:
        row=s.get(Project,project_id)
        if not row: raise HTTPException(404,'Projeto não encontrado')
        row.is_archived=False; s.commit()
        return {'ok':True}
def dependency_cycle(session, task_id:int, dependency_ids:list[int]):
    links=[(link.task_id,link.depends_on_id) for link in session.scalars(select(TaskDependency))]
    return dependency_change_creates_cycle(links,task_id,dependency_ids)

def save_task(data,task_id=None):
    status_changed=False
    with Session(engine) as s:
        project=s.get(Project,data.project_id)
        if not project or project.is_archived: raise HTTPException(404,'Projeto não encontrado')
        label_ids=list(dict.fromkeys(data.label_ids))
        dependency_ids=list(dict.fromkeys(data.dependency_ids))
        if any(not s.get(Label,label_id) for label_id in label_ids):
            raise HTTPException(422,'Uma das etiquetas selecionadas não existe.')
        if any(not s.get(Task,dependency_id) for dependency_id in dependency_ids):
            raise HTTPException(422,'Uma das tarefas dependentes não existe.')
        row=s.get(Task,task_id) if task_id else Task()
        if row is None: raise HTTPException(404,'Tarefa não encontrada')
        if task_id and (task_id in dependency_ids or dependency_cycle(s,task_id,dependency_ids)):
            raise HTTPException(422,'Esta dependência criaria um ciclo entre as tarefas.')
        if data.status=='done' and any(s.get(Task,dependency_id).status!='done' for dependency_id in dependency_ids):
            raise HTTPException(409,'Conclua as tarefas das quais esta depende antes de finalizá-la.')
        if data.recurrence != 'none' and not data.due_date:
            raise HTTPException(422,'Informe um prazo para usar a recorrência.')
        if data.recurrence_end and data.due_date and data.recurrence_end < data.due_date:
            raise HTTPException(422,'A data final da recorrência deve ser igual ou posterior ao prazo.')
        create_next = bool(task_id and row.status != 'done' and data.status == 'done' and data.recurrence != 'none')
        source_checklist = list(s.scalars(select(ChecklistItem).where(ChecklistItem.task_id==task_id))) if create_next else []
        status_changed=bool(task_id and row.status!=data.status)
        if status_changed:
            s.add(History(task_title=data.title,old_status=row.status,new_status=data.status,created_at=datetime.now(timezone.utc).isoformat()))
        values=data.model_dump(); values.pop('label_ids',None); values.pop('dependency_ids',None)
        values['due_date']=data.due_date.isoformat() if data.due_date else ''
        values['recurrence_end']=data.recurrence_end.isoformat() if data.recurrence_end else ''
        for k,v in values.items(): setattr(row,k,v)
        s.add(row); s.flush()
        for link in s.scalars(select(TaskLabel).where(TaskLabel.task_id==row.id)):
            s.delete(link)
        s.flush()
        s.add_all(TaskLabel(task_id=row.id,label_id=label_id) for label_id in label_ids)
        for link in s.scalars(select(TaskDependency).where(TaskDependency.task_id==row.id)):
            s.delete(link)
        s.flush()
        s.add_all(TaskDependency(task_id=row.id,depends_on_id=dependency_id) for dependency_id in dependency_ids)
        if create_next and data.due_date:
            next_due = next_recurrence_date(data.due_date, data.recurrence)
            if next_due and (not data.recurrence_end or next_due <= data.recurrence_end):
                next_task = Task(
                    title=data.title, project_id=data.project_id, status='todo', priority=data.priority,
                    assignee=data.assignee, due_date=next_due.isoformat(), estimated_hours=data.estimated_hours,
                    is_archived=False, recurrence=data.recurrence,
                    recurrence_end=data.recurrence_end.isoformat() if data.recurrence_end else '',
                )
                s.add(next_task); s.flush()
                s.add_all(TaskLabel(task_id=next_task.id,label_id=label_id) for label_id in label_ids)
                s.add_all(TaskDependency(task_id=next_task.id,depends_on_id=dependency_id) for dependency_id in dependency_ids)
                created_at=datetime.now(timezone.utc).isoformat()
                s.add_all(ChecklistItem(task_id=next_task.id,title=item.title,is_done=False,created_at=created_at) for item in source_checklist)
        s.commit(); s.refresh(row);saved_id=row.id
        result={**dump(row),'label_ids':label_ids,'dependency_ids':dependency_ids}
    if status_changed:
        sync_one_runrun_status(saved_id)
        with Session(engine) as s: result.update(dump(s.get(Task,saved_id)))
    return result
@app.post('/api/tasks',status_code=201)
def create_task(data:TaskInput): return save_task(data)
@app.put('/api/tasks/{task_id}')
def update_task(task_id:int,data:TaskInput): return save_task(data,task_id)
@app.delete('/api/tasks/{task_id}')
def delete_task(task_id:int):
    with Session(engine) as s:
        row=s.get(Task,task_id)
        if not row: raise HTTPException(404,'Tarefa não encontrada')
        timer=s.scalar(select(ActiveTimer).where(ActiveTimer.task_id==task_id))
        if timer: raise HTTPException(409,'Pare ou descarte o cronômetro antes de excluir esta tarefa.')
        for item in s.scalars(select(ChecklistItem).where(ChecklistItem.task_id==task_id)):
            s.delete(item)
        for comment in s.scalars(select(TaskComment).where(TaskComment.task_id==task_id)):
            s.delete(comment)
        attachment_paths=[]
        for attachment in s.scalars(select(Attachment).where(Attachment.task_id==task_id)):
            attachment_paths.append(attachments_dir/attachment.stored_name);s.delete(attachment)
        for link in s.scalars(select(TaskLabel).where(TaskLabel.task_id==task_id)):
            s.delete(link)
        for link in s.scalars(select(TaskDependency).where((TaskDependency.task_id==task_id)|(TaskDependency.depends_on_id==task_id))):
            s.delete(link)
        s.delete(row); s.commit()
        for path in attachment_paths: path.unlink(missing_ok=True)
        return {'ok':True}
@app.post('/api/tasks/{task_id}/archive')
def archive_task(task_id:int):
    with Session(engine) as s:
        row=s.get(Task,task_id)
        if not row: raise HTTPException(404,'Tarefa não encontrada')
        if s.scalar(select(ActiveTimer).where(ActiveTimer.task_id==task_id)):
            raise HTTPException(409,'Pare ou descarte o cronômetro antes de arquivar esta tarefa.')
        row.is_archived=True; s.commit()
        return {'ok':True}
@app.post('/api/tasks/{task_id}/restore')
def restore_task(task_id:int):
    with Session(engine) as s:
        row=s.get(Task,task_id)
        if not row: raise HTTPException(404,'Tarefa não encontrada')
        project=s.get(Project,row.project_id)
        if not project or project.is_archived:
            raise HTTPException(409,'Restaure o projeto desta tarefa primeiro.')
        row.is_archived=False; s.commit()
        return {'ok':True}
@app.post('/api/tasks/{task_id}/checklist',status_code=201)
def create_checklist_item(task_id:int,data:ChecklistInput):
    with Session(engine) as s:
        task=s.get(Task,task_id)
        project=s.get(Project,task.project_id) if task else None
        if not task or task.is_archived or not project or project.is_archived: raise HTTPException(404,'Tarefa não encontrada')
        row=ChecklistItem(task_id=task_id,title=data.title.strip(),is_done=False,created_at=datetime.now(timezone.utc).isoformat())
        s.add(row); s.commit(); s.refresh(row)
        return dump(row)
@app.put('/api/checklist/{item_id}')
def update_checklist_item(item_id:int,data:ChecklistUpdate):
    with Session(engine) as s:
        row=s.get(ChecklistItem,item_id)
        if not row: raise HTTPException(404,'Item do checklist não encontrado')
        row.title=data.title.strip(); row.is_done=data.is_done
        s.commit(); s.refresh(row)
        return dump(row)
@app.delete('/api/checklist/{item_id}')
def delete_checklist_item(item_id:int):
    with Session(engine) as s:
        row=s.get(ChecklistItem,item_id)
        if not row: raise HTTPException(404,'Item do checklist não encontrado')
        s.delete(row); s.commit()
        return {'ok':True}
@app.post('/api/tasks/{task_id}/comments',status_code=201)
def create_comment(task_id:int,data:CommentInput):
    with Session(engine) as s:
        task=s.get(Task,task_id)
        if not task: raise HTTPException(404,'Tarefa não encontrada')
        row=TaskComment(task_id=task_id,author=data.author.strip(),content=data.content.strip(),created_at=datetime.now(timezone.utc).isoformat())
        s.add(row); s.commit(); s.refresh(row)
        return dump(row)
@app.delete('/api/comments/{comment_id}')
def delete_comment(comment_id:int):
    with Session(engine) as s:
        row=s.get(TaskComment,comment_id)
        if not row: raise HTTPException(404,'Comentário não encontrado')
        s.delete(row); s.commit()
        return {'ok':True}
@app.post('/api/tasks/{task_id}/attachments',status_code=201)
def create_attachment(task_id:int,data:AttachmentInput):
    original_name=Path(data.original_name).name.strip()
    if not original_name: raise HTTPException(422,'Nome do arquivo inválido.')
    try: content=base64.b64decode(data.content_base64,validate=True)
    except (ValueError,binascii.Error): raise HTTPException(422,'Conteúdo do arquivo inválido.')
    if not content: raise HTTPException(422,'O arquivo está vazio.')
    if len(content)>20*1024*1024: raise HTTPException(413,'O arquivo ultrapassa o limite de 20 MB.')
    with Session(engine) as s:
        if not s.get(Task,task_id): raise HTTPException(404,'Tarefa não encontrada')
        stored_name=f'{uuid4().hex}{Path(original_name).suffix[:20]}'
        row=Attachment(task_id=task_id,original_name=original_name,stored_name=stored_name,size=len(content),created_at=datetime.now(timezone.utc).isoformat())
        (attachments_dir/stored_name).write_bytes(content)
        try: s.add(row);s.commit();s.refresh(row)
        except Exception:
            (attachments_dir/stored_name).unlink(missing_ok=True);raise
        return dump(row)
@app.get('/api/attachments/{attachment_id}')
def download_attachment(attachment_id:int):
    with Session(engine) as s:
        row=s.get(Attachment,attachment_id)
        if not row: raise HTTPException(404,'Anexo não encontrado')
        path=attachments_dir/row.stored_name
        if not path.is_file(): raise HTTPException(404,'Arquivo do anexo não encontrado')
        return FileResponse(path,filename=row.original_name)
@app.delete('/api/attachments/{attachment_id}')
def delete_attachment(attachment_id:int):
    with Session(engine) as s:
        row=s.get(Attachment,attachment_id)
        if not row: raise HTTPException(404,'Anexo não encontrado')
        path=attachments_dir/row.stored_name;s.delete(row);s.commit();path.unlink(missing_ok=True);return {'ok':True}
def save_label(data,label_id=None):
    with Session(engine) as s:
        row=s.get(Label,label_id) if label_id else Label()
        if row is None: raise HTTPException(404,'Etiqueta não encontrada')
        name=data.name.strip()
        duplicate=s.scalar(select(Label).where(Label.name==name,Label.id!=label_id if label_id else True))
        if duplicate: raise HTTPException(409,'Já existe uma etiqueta com este nome.')
        row.name=name; row.color=data.color.lower(); s.add(row); s.commit(); s.refresh(row)
        return dump(row)
@app.post('/api/labels',status_code=201)
def create_label(data:LabelInput): return save_label(data)
@app.put('/api/labels/{label_id}')
def update_label(label_id:int,data:LabelInput): return save_label(data,label_id)
@app.delete('/api/labels/{label_id}')
def delete_label(label_id:int):
    with Session(engine) as s:
        row=s.get(Label,label_id)
        if not row: raise HTTPException(404,'Etiqueta não encontrada')
        for link in s.scalars(select(TaskLabel).where(TaskLabel.label_id==label_id)):
            s.delete(link)
        s.delete(row); s.commit()
        return {'ok':True}
def save_entry(data:EntryInput, entry_id=None):
    with Session(engine) as s:
        task=s.get(Task,data.task_id)
        if not task: raise HTTPException(404,'Tarefa não encontrada')
        row=s.get(Entry,entry_id) if entry_id else Entry(created_at=datetime.now(timezone.utc).isoformat())
        if row is None: raise HTTPException(404,'Registro de horas não encontrado')
        row.task_id=data.task_id
        row.task_title=task.title
        row.hours=data.hours
        row.note=data.note
        if data.work_date:
            row.created_at=datetime.combine(data.work_date,datetime.min.time(),tzinfo=timezone.utc).replace(hour=12).isoformat()
        s.add(row); s.commit(); s.refresh(row)
        return dump(row)
@app.post('/api/entries',status_code=201)
def create_entry(data:EntryInput): return save_entry(data)
@app.put('/api/entries/{entry_id}')
def update_entry(entry_id:int,data:EntryInput): return save_entry(data,entry_id)
@app.delete('/api/entries/{entry_id}')
def delete_entry(entry_id:int):
    with Session(engine) as s:
        row=s.get(Entry,entry_id)
        if not row: raise HTTPException(404,'Registro de horas não encontrado')
        s.delete(row); s.commit()
        return {'ok':True}

@app.post('/api/timer/start',status_code=201)
def start_timer(data: TimerInput):
    with Session(engine) as s:
        task=s.get(Task,data.task_id)
        project=s.get(Project,task.project_id) if task else None
        if not task or task.is_archived or not project or project.is_archived: raise HTTPException(404,'Tarefa não encontrada')
        if s.scalar(select(ActiveTimer).where(ActiveTimer.task_id==data.task_id)):
            raise HTTPException(409,'Esta tarefa já tem um cronômetro em andamento.')
        timer=ActiveTimer(task_id=data.task_id,started_at=datetime.now(timezone.utc).isoformat(),elapsed_seconds=0,paused_at=None)
        s.add(timer)
        try: s.commit()
        except IntegrityError:
            s.rollback()
            raise HTTPException(409,'Esta tarefa já tem um cronômetro em andamento.')
        s.refresh(timer)
        return dump(timer)

def timer_elapsed_seconds(timer: ActiveTimer, now: datetime) -> float:
    elapsed = timer.elapsed_seconds
    if timer.paused_at is None:
        elapsed += max(0,(now-datetime.fromisoformat(timer.started_at)).total_seconds())
    return max(0,elapsed)

@app.post('/api/timer/{task_id}/pause')
def pause_timer(task_id:int):
    with Session(engine) as s:
        timer=s.scalar(select(ActiveTimer).where(ActiveTimer.task_id==task_id))
        if not timer: raise HTTPException(404,'Nenhum cronômetro nesta tarefa')
        if timer.paused_at is not None: raise HTTPException(409,'Este cronômetro já está pausado')
        now=datetime.now(timezone.utc)
        timer.elapsed_seconds=timer_elapsed_seconds(timer,now)
        timer.paused_at=now.isoformat()
        s.commit(); s.refresh(timer)
        return dump(timer)

@app.post('/api/timer/{task_id}/resume')
def resume_timer(task_id:int):
    with Session(engine) as s:
        timer=s.scalar(select(ActiveTimer).where(ActiveTimer.task_id==task_id))
        if not timer: raise HTTPException(404,'Nenhum cronômetro nesta tarefa')
        if timer.paused_at is None: raise HTTPException(409,'Este cronômetro já está contando')
        timer.started_at=datetime.now(timezone.utc).isoformat()
        timer.paused_at=None
        s.commit(); s.refresh(timer)
        return dump(timer)

@app.post('/api/timer/{task_id}/stop')
def stop_timer(task_id:int):
    with Session(engine) as s:
        timer=s.scalar(select(ActiveTimer).where(ActiveTimer.task_id==task_id))
        if not timer: raise HTTPException(404,'Nenhum cronômetro em andamento nesta tarefa')
        task=s.get(Task,task_id)
        if not task: raise HTTPException(404,'Tarefa não encontrada')
        now=datetime.now(timezone.utc)
        elapsed=timer_elapsed_seconds(timer,now)
        minutes=max(1,int((elapsed+30)//60))
        entry=Entry(task_id=task.id,task_title=task.title,hours=minutes/60,note='Cronômetro',created_at=now.isoformat())
        s.add(entry); s.delete(timer); s.commit(); s.refresh(entry);entry_id=entry.id
        settings=s.get(RunrunSettings,1);auto_sync=bool(settings and settings.auto_sync_hours and task.runrunit_id)
    if auto_sync: send_runrun_hours(task_id)
    with Session(engine) as s: return dump(s.get(Entry,entry_id))

@app.delete('/api/timer/{task_id}')
def discard_timer(task_id:int):
    with Session(engine) as s:
        timer=s.scalar(select(ActiveTimer).where(ActiveTimer.task_id==task_id))
        if not timer: raise HTTPException(404,'Nenhum cronômetro em andamento nesta tarefa')
        s.delete(timer); s.commit()
        return {'ok':True}

if web_dir.is_dir():
    app.mount('/assets', StaticFiles(directory=web_dir / 'assets'), name='assets')
