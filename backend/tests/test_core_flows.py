import asyncio
import unittest
from datetime import date
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine

from app import main


class CoreFlowsTest(unittest.TestCase):
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

    def test_complete_project_task_hours_and_history_flow(self):
        project = main.create_project(main.ProjectInput(name='Projeto', description='Descrição'))
        task = main.create_task(main.TaskInput(
            title='Planejar entrega',
            project_id=project['id'],
            assignee='Pessoa',
            due_date=date(2026, 10, 1),
            estimated_hours=2.5,
        ))
        updated = main.update_task(task['id'], main.TaskInput(
            title='Planejar entrega final',
            project_id=project['id'],
            status='doing',
            priority='high',
            assignee='Pessoa',
            due_date=date(2026, 10, 2),
            estimated_hours=3,
        ))
        entry = main.create_entry(main.EntryInput(task_id=task['id'], hours=1.25, note='Planejamento'))
        original_created_at = entry['created_at']
        entry = main.update_entry(entry['id'], main.EntryInput(task_id=task['id'], hours=2, note='Revisado'))
        board = main.board()

        self.assertEqual(updated['status'], 'doing')
        self.assertEqual(entry['task_title'], 'Planejar entrega final')
        self.assertEqual(board['projects'][0]['name'], 'Projeto')
        self.assertEqual(board['tasks'][0]['due_date'], '2026-10-02')
        self.assertEqual(board['entries'][0]['hours'], 2)
        self.assertEqual(board['entries'][0]['note'], 'Revisado')
        self.assertEqual(board['entries'][0]['created_at'], original_created_at)
        self.assertEqual(board['history'][0]['old_status'], 'todo')
        self.assertEqual(board['history'][0]['new_status'], 'doing')
        self.assertEqual(main.delete_entry(entry['id']), {'ok': True})
        self.assertEqual(main.board()['entries'], [])

    def test_profile_and_settings_are_trimmed_and_persisted(self):
        self.assertEqual(main.update_profile(main.ProfileInput(display_name='  Ana Silva  ')), {'display_name': 'Ana Silva'})
        self.assertEqual(main.get_profile(), {'display_name': 'Ana Silva'})

        saved = main.update_settings(main.SettingsInput(board_name='  Quadro pessoal  ', theme='verde', appearance='dark'))
        self.assertEqual(saved['board_name'], 'Quadro pessoal')
        self.assertEqual(main.get_settings(), {'board_name': 'Quadro pessoal', 'theme': 'verde', 'appearance': 'dark'})

    def test_invalid_inputs_and_missing_relationships_are_rejected(self):
        with self.assertRaises(ValidationError):
            main.EntryInput(task_id=1, hours=0)
        with self.assertRaises(ValidationError):
            main.SettingsInput(board_name='Quadro', theme='laranja')
        with self.assertRaises(ValidationError):
            main.SettingsInput(board_name='Quadro', appearance='automatico')
        with self.assertRaises(HTTPException) as raised:
            main.create_task(main.TaskInput(title='Órfã', project_id=999, assignee='Pessoa'))
        self.assertEqual(raised.exception.status_code, 404)
        with self.assertRaises(HTTPException) as raised:
            main.update_entry(999, main.EntryInput(task_id=999, hours=1))
        self.assertEqual(raised.exception.status_code, 404)


if __name__ == '__main__':
    unittest.main()
