import asyncio
import unittest
from datetime import date
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine

from app import main


class BackupTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False})
        self.engine_patch = patch.object(main, 'engine', self.engine)
        self.engine_patch.start()
        self.lifespan = main.lifespan(main.app)
        asyncio.run(self.lifespan.__aenter__())

    def tearDown(self):
        asyncio.run(self.lifespan.__aexit__(None, None, None))
        self.engine_patch.stop()
        self.engine.dispose()

    def test_export_and_restore_complete_backup(self):
        main.update_profile(main.ProfileInput(display_name='Ana'))
        main.update_settings(main.SettingsInput(board_name='Equipe', theme='roxo', appearance='dark'))
        project = main.create_project(main.ProjectInput(name='Aplicativo', description='Descrição'))
        task = main.create_task(main.TaskInput(
            title='Criar backup', project_id=project['id'], status='doing', priority='high',
            assignee='Ana', due_date=date(2026, 10, 10), estimated_hours=3,
        ))
        main.create_entry(main.EntryInput(task_id=task['id'], hours=1.5, note='Primeira etapa'))
        item = main.create_checklist_item(task['id'], main.ChecklistInput(title='Revisar conteúdo'))
        main.update_checklist_item(item['id'], main.ChecklistUpdate(title=item['title'], is_done=True))
        main.start_timer(main.TimerInput(task_id=task['id']))
        backup = main.export_backup()

        main.update_profile(main.ProfileInput(display_name='Alterado'))
        main.update_settings(main.SettingsInput(board_name='Outro', theme='azul', appearance='light'))
        main.discard_timer(task['id'])

        restored = main.restore_backup(main.BackupPayload.model_validate(backup))

        self.assertEqual(restored, {'ok': True, 'projects': 1, 'tasks': 1, 'entries': 1, 'checklist_items': 1})
        self.assertEqual(main.get_profile(), {'display_name': 'Ana'})
        self.assertEqual(main.get_settings(), {'board_name': 'Equipe', 'theme': 'roxo', 'appearance': 'dark'})
        board = main.board()
        self.assertEqual(board['projects'][0]['name'], 'Aplicativo')
        self.assertEqual(board['tasks'][0]['title'], 'Criar backup')
        self.assertEqual(board['entries'][0]['note'], 'Primeira etapa')
        self.assertEqual(board['checklist_items'][0]['title'], 'Revisar conteúdo')
        self.assertTrue(board['checklist_items'][0]['is_done'])
        self.assertEqual(board['active_timers'][0]['task_id'], task['id'])

    def test_rejects_task_with_missing_project_without_replacing_data(self):
        existing = main.create_project(main.ProjectInput(name='Preservado'))
        backup = main.export_backup()
        backup['tasks'] = [{
            'id': 1, 'title': 'Órfã', 'project_id': 999, 'status': 'todo', 'priority': 'medium',
            'assignee': 'Ana', 'due_date': '', 'estimated_hours': 0,
        }]

        with self.assertRaises(HTTPException) as raised:
            main.restore_backup(main.BackupPayload.model_validate(backup))

        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(main.board()['projects'][0]['id'], existing['id'])


if __name__ == '__main__':
    unittest.main()
