import asyncio
import unittest
from datetime import date
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine

from app import main


class RecurringTasksTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False})
        self.engine_patch = patch.object(main, 'engine', self.engine)
        self.engine_patch.start()
        self.lifespan = main.lifespan(main.app)
        asyncio.run(self.lifespan.__aenter__())
        self.project = main.create_project(main.ProjectInput(name='Rotinas'))

    def tearDown(self):
        asyncio.run(self.lifespan.__aexit__(None, None, None))
        self.engine_patch.stop()
        self.engine.dispose()

    def task_input(self, **changes):
        values = {
            'title': 'Revisão semanal', 'project_id': self.project['id'], 'status': 'todo',
            'priority': 'medium', 'assignee': 'Ana', 'due_date': date(2026, 9, 25),
            'estimated_hours': 1, 'recurrence': 'weekly', 'recurrence_end': None,
        }
        values.update(changes)
        return main.TaskInput(**values)

    def test_completing_recurring_task_creates_next_occurrence_and_checklist(self):
        task = main.create_task(self.task_input())
        main.create_checklist_item(task['id'], main.ChecklistInput(title='Conferir dados'))

        main.update_task(task['id'], self.task_input(status='done'))
        board = main.board()

        self.assertEqual(len(board['tasks']), 2)
        current, next_task = board['tasks']
        self.assertEqual(current['status'], 'done')
        self.assertEqual(next_task['status'], 'todo')
        self.assertEqual(next_task['due_date'], '2026-10-02')
        self.assertEqual(next_task['recurrence'], 'weekly')
        copied = [item for item in board['checklist_items'] if item['task_id'] == next_task['id']]
        self.assertEqual([(item['title'], item['is_done']) for item in copied], [('Conferir dados', False)])

    def test_repeated_save_of_completed_task_does_not_duplicate_next_occurrence(self):
        task = main.create_task(self.task_input())
        completed = self.task_input(status='done')
        main.update_task(task['id'], completed)
        main.update_task(task['id'], completed)
        self.assertEqual(len(main.board()['tasks']), 2)

    def test_end_date_prevents_occurrence_after_limit(self):
        task = main.create_task(self.task_input(recurrence_end=date(2026, 9, 30)))
        main.update_task(task['id'], self.task_input(status='done', recurrence_end=date(2026, 9, 30)))
        self.assertEqual(len(main.board()['tasks']), 1)

    def test_recurrence_requires_due_date_and_monthly_handles_month_end(self):
        with self.assertRaises(HTTPException) as raised:
            main.create_task(self.task_input(due_date=None))
        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(main.next_recurrence_date(date(2026, 1, 31), 'monthly'), date(2026, 2, 28))


class RecurrenceMigrationTest(unittest.TestCase):
    def test_existing_tasks_receive_recurrence_columns(self):
        engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False})
        with engine.begin() as connection:
            connection.exec_driver_sql('CREATE TABLE tasks (id INTEGER PRIMARY KEY, title VARCHAR NOT NULL, project_id INTEGER NOT NULL, status VARCHAR NOT NULL, priority VARCHAR NOT NULL, assignee VARCHAR NOT NULL, due_date VARCHAR NOT NULL, estimated_hours FLOAT NOT NULL, is_archived BOOLEAN NOT NULL DEFAULT 0)')
            connection.exec_driver_sql("INSERT INTO tasks (id,title,project_id,status,priority,assignee,due_date,estimated_hours,is_archived) VALUES (1,'Existente',1,'todo','medium','Ana','',0,0)")
        with patch.object(main, 'engine', engine):
            lifespan = main.lifespan(main.app)
            asyncio.run(lifespan.__aenter__())
            try:
                with engine.connect() as connection:
                    columns = {row[1] for row in connection.exec_driver_sql('PRAGMA table_info(tasks)')}
                    task = connection.exec_driver_sql('SELECT title, recurrence, recurrence_end FROM tasks WHERE id=1').one()
                self.assertTrue({'recurrence', 'recurrence_end'} <= columns)
                self.assertEqual(tuple(task), ('Existente', 'none', ''))
            finally:
                asyncio.run(lifespan.__aexit__(None, None, None))
                engine.dispose()


if __name__ == '__main__':
    unittest.main()
