import asyncio
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app import main


class DeletionFlowsTest(unittest.TestCase):
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

    def assert_http_error(self, status_code, action):
        with self.assertRaises(HTTPException) as raised:
            action()
        self.assertEqual(raised.exception.status_code, status_code)

    def create_project_and_task(self):
        project = main.create_project(main.ProjectInput(name='Projeto protegido'))
        task = main.create_task(main.TaskInput(
            title='Tarefa vinculada',
            project_id=project['id'],
            assignee='Pessoa',
        ))
        return project, task

    def test_project_with_tasks_is_protected_until_task_is_removed(self):
        project, task = self.create_project_and_task()

        self.assert_http_error(409, lambda: main.delete_project(project['id']))
        with Session(self.engine) as session:
            self.assertIsNotNone(session.get(main.Project, project['id']))
            self.assertIsNotNone(session.get(main.Task, task['id']))

        self.assertEqual(main.delete_task(task['id']), {'ok': True})
        self.assertEqual(main.delete_project(project['id']), {'ok': True})
        with Session(self.engine) as session:
            self.assertIsNone(session.get(main.Project, project['id']))
            self.assertIsNone(session.get(main.Task, task['id']))

    def test_task_with_active_timer_is_protected(self):
        _, task = self.create_project_and_task()
        main.start_timer(main.TimerInput(task_id=task['id']))

        self.assert_http_error(409, lambda: main.delete_task(task['id']))
        with Session(self.engine) as session:
            self.assertIsNotNone(session.get(main.Task, task['id']))
            self.assertIsNotNone(session.scalar(
                select(main.ActiveTimer).where(main.ActiveTimer.task_id == task['id'])
            ))

        main.discard_timer(task['id'])
        self.assertEqual(main.delete_task(task['id']), {'ok': True})

    def test_deleting_task_preserves_entries_and_history(self):
        project, task = self.create_project_and_task()
        main.create_entry(main.EntryInput(task_id=task['id'], hours=1.5, note='Trabalho feito'))
        with Session(self.engine) as session:
            session.add(main.History(
                task_title=task['title'],
                old_status='todo',
                new_status='doing',
                created_at=datetime.now(timezone.utc).isoformat(),
            ))
            session.commit()

        main.delete_task(task['id'])
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(main.Entry)), 1)
            self.assertEqual(session.scalar(select(func.count()).select_from(main.History)), 1)
            self.assertIsNone(session.get(main.Task, task['id']))

        self.assertEqual(main.delete_project(project['id']), {'ok': True})

    def test_missing_resources_return_not_found(self):
        self.assert_http_error(404, lambda: main.delete_project(999))
        self.assert_http_error(404, lambda: main.delete_task(999))
        self.assert_http_error(404, lambda: main.discard_timer(999))


if __name__ == '__main__':
    unittest.main()
