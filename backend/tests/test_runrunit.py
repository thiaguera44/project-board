import asyncio
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import main
from app.models import ActiveTimer, Entry


class FakeRunrunClient:
    def __init__(self): self.sent=[];self.moved=[];self.fail_next=False;self.task_title='Preparar entrega'
    def projects(self): return [{'id': 20, 'name': 'Portal do cliente', 'description': 'Projeto remoto'}]
    def users(self): return [{'id':'user-1','name':'Ana Runrun'}]
    def stages(self, board_id): return [{'id': 9, 'stage_group': 'closed'}]
    def tasks(self, board_id):
        return [
            {'id': 101, 'title': self.task_title, 'project_id': 20, 'board_stage_id': 2, 'state': 'working_on', 'desired_date': '2026-10-20', 'time_estimated': 7200, 'is_urgent': True, 'user_name': 'Ana'},
            {'id': 102, 'title': 'Validar entrega', 'project_id': 20, 'board_stage_id': 9, 'state': 'closed'},
        ]
    def add_manual_work(self, task_id, seconds, date_to_apply):
        if self.fail_next:
            self.fail_next=False
            raise main.RunrunError('Falha temporária')
        self.sent.append((task_id,seconds,date_to_apply))
        return {'id': 800 + len(self.sent)}
    def move_task(self, task_id, board_stage_id):
        self.moved.append((task_id,board_stage_id));return {'id':task_id,'board_stage_id':board_stage_id}


class RunrunIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine('sqlite:///:memory:',connect_args={'check_same_thread':False})
        self.engine_patch=patch.object(main,'engine',self.engine);self.engine_patch.start()
        self.lifespan=main.lifespan(main.app);asyncio.run(self.lifespan.__aenter__())
        self.client=FakeRunrunClient();self.client_patch=patch.object(main,'runrun_client',return_value=self.client);self.client_patch.start()
    def tearDown(self):
        self.client_patch.stop();asyncio.run(self.lifespan.__aexit__(None,None,None));self.engine_patch.stop();self.engine.dispose()

    def test_import_is_repeatable_and_hours_are_sent_once(self):
        payload=main.RunrunImportInput(board_id=7,board_name='Operações')
        first=main.import_runrun_board(payload)
        second=main.import_runrun_board(payload)
        self.assertEqual((first['projects_created'],first['tasks_created'],first['tasks_updated']),(1,2,0))
        self.assertEqual((second['projects_created'],second['tasks_created'],second['tasks_updated']),(0,0,2))
        board=main.board()
        self.assertEqual(len(board['projects']),1);self.assertEqual(len(board['tasks']),2)
        self.assertEqual(board['tasks'][0]['status'],'doing');self.assertEqual(board['tasks'][1]['status'],'done')
        entry=main.create_entry(main.EntryInput(task_id=board['tasks'][0]['id'],hours=1.5,note='Execução'))
        with Session(self.engine) as session:
            row=session.get(Entry,entry['id']);row.created_at=datetime(2026,10,21,tzinfo=timezone.utc).isoformat();session.commit()
        self.assertEqual(main.sync_runrun_hours()['sent'],1)
        self.assertEqual(main.sync_runrun_hours()['sent'],0)
        self.assertEqual(self.client.sent,[(101,5400,'2026-10-21')])
        synced=main.board()['entries'][0]
        self.assertIsNotNone(synced['runrunit_synced_at']);self.assertEqual(synced['runrunit_work_period_id'],801)
        removed=main.remove_runrun_import(7)
        self.assertEqual((removed['tasks_removed'],removed['projects_removed']),(2,1))
        self.assertEqual(main.board()['tasks'],[])
        self.assertEqual(len(main.board()['entries']),1)

    def test_preview_hides_completed_and_imports_only_selection(self):
        preview=main.preview_runrun_board(main.RunrunPreviewInput(board_id=7))
        self.assertEqual([task['id'] for task in preview['tasks']],[101])
        self.assertEqual(preview['completed_hidden'],1)
        complete=main.preview_runrun_board(main.RunrunPreviewInput(board_id=7,include_completed=True))
        self.assertEqual({task['id'] for task in complete['tasks']},{101,102})
        result=main.import_runrun_board(main.RunrunImportInput(board_id=7,board_name='Operações',task_ids=[102]))
        self.assertEqual(result['tasks_created'],1)
        board=main.board()
        self.assertEqual([task['runrunit_id'] for task in board['tasks']],[102])
        self.assertEqual(board['tasks'][0]['status'],'done')

    def test_reimport_compares_and_updates_only_selected_fields(self):
        main.import_runrun_board(main.RunrunImportInput(board_id=7,board_name='Operações',task_ids=[101]))
        task=main.board()['tasks'][0]
        main.update_task(task['id'],main.TaskInput(title='Título local',project_id=task['project_id'],status='todo',priority='low',assignee='Pessoa local'))
        preview=main.preview_runrun_board(main.RunrunPreviewInput(board_id=7,include_completed=True))
        remote=next(row for row in preview['tasks'] if row['id']==101)
        self.assertTrue({'title','status','assignee','priority'}.issubset(set(remote['changes'])))
        main.import_runrun_board(main.RunrunImportInput(board_id=7,board_name='Operações',task_ids=[101],update_fields=['title']))
        updated=main.board()['tasks'][0]
        self.assertEqual(updated['title'],'Preparar entrega')
        self.assertEqual((updated['status'],updated['assignee'],updated['priority']),('todo','Pessoa local','low'))

    def test_incremental_preview_returns_only_new_or_changed_tasks(self):
        main.import_runrun_board(main.RunrunImportInput(board_id=7,board_name='Operações'))
        unchanged=main.preview_runrun_board(main.RunrunPreviewInput(board_id=7,include_completed=True,incremental=True))
        self.assertEqual((unchanged['scanned'],unchanged['total']),(2,0))
        task=main.board()['tasks'][0]
        main.update_task(task['id'],main.TaskInput(title='Alterada localmente',project_id=task['project_id'],status=task['status'],priority=task['priority'],assignee=task['assignee'],due_date=task['due_date'] or None,estimated_hours=task['estimated_hours']))
        changed=main.preview_runrun_board(main.RunrunPreviewInput(board_id=7,include_completed=True,incremental=True))
        self.assertEqual(changed['total'],1)
        self.assertEqual(changed['tasks'][0]['changes'],['title'])
        self.assertIsNotNone(main.runrun_status()['last_sync_at'])

    def test_local_task_can_be_linked_synced_and_unlinked(self):
        project=main.create_project(main.ProjectInput(name='Projeto local'))
        task=main.create_task(main.TaskInput(title='Tarefa criada aqui',project_id=project['id'],assignee='Ana'))
        other=main.create_task(main.TaskInput(title='Outra tarefa',project_id=project['id'],assignee='Ana'))
        main.create_entry(main.EntryInput(task_id=task['id'],hours=2,note='Trabalho anterior'))
        linked=main.link_runrun_task(main.RunrunLinkInput(task_id=task['id'],board_id=7,board_name='Operações',runrunit_task_id=101))
        self.assertEqual(linked['task']['runrunit_task_title'],'Preparar entrega')
        self.assertEqual(linked['task']['runrunit_origin'],'linked')
        self.assertEqual(linked['pending_hours'],1)
        with self.assertRaises(HTTPException) as raised:
            main.link_runrun_task(main.RunrunLinkInput(task_id=other['id'],board_id=7,board_name='Operações',runrunit_task_id=101))
        self.assertEqual(raised.exception.status_code,409)
        self.assertEqual(main.sync_runrun_task_hours(task['id'])['sent'],1)
        self.assertEqual(self.client.sent[0][:2],(101,7200))
        main.unlink_runrun_task(task['id'])
        local=next(row for row in main.board()['tasks'] if row['id']==task['id'])
        self.assertIsNone(local['runrunit_id'])
        self.assertEqual(len(main.board()['entries']),1)

    def test_failed_hour_is_listed_and_can_be_retried_separately(self):
        main.import_runrun_board(main.RunrunImportInput(board_id=7,board_name='Operações',task_ids=[101]))
        task=main.board()['tasks'][0]
        entry=main.create_entry(main.EntryInput(task_id=task['id'],hours=.5,note='Revisão'))
        self.client.fail_next=True
        result=main.sync_runrun_hours()
        self.assertEqual(result['sent'],0);self.assertEqual(len(result['errors']),1)
        record=main.runrun_hour_records()[0]
        self.assertEqual((record['id'],record['state']),(entry['id'],'failed'))
        self.assertEqual(record['runrunit_sync_error'],'Falha temporária')
        status=main.runrun_status()
        self.assertEqual((status['pending_hours'],status['failed_hours'],status['synced_hours']),(0,1,0))
        retried=main.retry_runrun_hours()
        self.assertEqual(retried['sent'],1)
        self.assertEqual(main.runrun_hour_records()[0]['state'],'sent')

    def test_status_mapping_can_sync_task_moves_automatically(self):
        main.import_runrun_board(main.RunrunImportInput(board_id=7,board_name='Operações',task_ids=[101]))
        saved=main.save_runrun_status_mapping(7,main.RunrunStatusMappingInput(enabled=True,todo_stage_id=9,doing_stage_id=9,waiting_stage_id=9,done_stage_id=9))
        self.assertTrue(saved['enabled'])
        task=main.board()['tasks'][0]
        updated=main.update_task(task['id'],main.TaskInput(title=task['title'],project_id=task['project_id'],status='done',priority=task['priority'],assignee=task['assignee']))
        self.assertEqual(self.client.moved,[(101,9)])
        self.assertEqual(updated['runrunit_last_synced_status'],'done')
        self.assertEqual(main.runrun_status()['pending_statuses'],0)

    def test_local_profile_can_be_mapped_to_runrun_user(self):
        saved=main.save_runrun_user_mapping(main.RunrunUserMappingInput(user_id='user-1',user_name=''))
        self.assertEqual(saved,{'user_id':'user-1','user_name':'Ana Runrun'})
        status=main.runrun_status()
        self.assertEqual((status['mapped_user_id'],status['mapped_user_name']),('user-1','Ana Runrun'))

    def test_timer_hours_can_be_sent_automatically(self):
        main.import_runrun_board(main.RunrunImportInput(board_id=7,board_name='Operações',task_ids=[101]))
        task=main.board()['tasks'][0]
        main.save_runrun_automation(main.RunrunAutomationInput(auto_sync_hours=True))
        main.start_timer(main.TimerInput(task_id=task['id']))
        with Session(self.engine) as session:
            timer=session.scalar(main.select(ActiveTimer));timer.elapsed_seconds=3600;timer.paused_at=datetime.now(timezone.utc).isoformat();session.commit()
        entry=main.stop_timer(task['id'])
        self.assertIsNotNone(entry['runrunit_synced_at'])
        self.assertEqual(self.client.sent[0][:2],(101,3600))

    def test_preview_identifies_local_and_remote_conflict(self):
        main.import_runrun_board(main.RunrunImportInput(board_id=7,board_name='Operações',task_ids=[101]))
        task=main.board()['tasks'][0]
        main.update_task(task['id'],main.TaskInput(title='Título local',project_id=task['project_id'],status=task['status'],priority=task['priority'],assignee=task['assignee'],due_date=task['due_date'],estimated_hours=task['estimated_hours']))
        self.client.task_title='Título remoto'
        preview=main.preview_runrun_board(main.RunrunPreviewInput(board_id=7,include_completed=True))
        self.assertIn('title',preview['tasks'][0]['conflicts'])


if __name__ == '__main__': unittest.main()
