import asyncio
import unittest
from datetime import date
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine

from app import main


class LabelsTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False})
        self.engine_patch = patch.object(main, 'engine', self.engine)
        self.engine_patch.start()
        self.lifespan = main.lifespan(main.app)
        asyncio.run(self.lifespan.__aenter__())
        self.project = main.create_project(main.ProjectInput(name='Aplicativo'))

    def tearDown(self):
        asyncio.run(self.lifespan.__aexit__(None, None, None))
        self.engine_patch.stop()
        self.engine.dispose()

    def task_input(self, label_ids, status='todo'):
        return main.TaskInput(
            title='Preparar entrega', project_id=self.project['id'], status=status,
            priority='high', assignee='Ana', due_date=date(2026, 10, 1),
            recurrence='weekly', label_ids=label_ids,
        )

    def test_labels_can_be_created_assigned_and_updated(self):
        label = main.create_label(main.LabelInput(name='  Cliente  ', color='#AA5500'))
        task = main.create_task(self.task_input([label['id']]))

        board = main.board()
        self.assertEqual(board['labels'][0], {'id': label['id'], 'name': 'Cliente', 'color': '#aa5500'})
        self.assertEqual(board['tasks'][0]['label_ids'], [label['id']])

        updated = main.update_label(label['id'], main.LabelInput(name='Entrega', color='#123ABC'))
        self.assertEqual(updated['name'], 'Entrega')
        self.assertEqual(updated['color'], '#123abc')

    def test_recurring_occurrence_keeps_labels_and_deleting_label_removes_links(self):
        label = main.create_label(main.LabelInput(name='Rotina', color='#7399cd'))
        task = main.create_task(self.task_input([label['id']]))
        main.update_task(task['id'], self.task_input([label['id']], status='done'))
        self.assertEqual([row['label_ids'] for row in main.board()['tasks']], [[label['id']], [label['id']]])

        main.delete_label(label['id'])
        board = main.board()
        self.assertEqual(board['labels'], [])
        self.assertEqual([row['label_ids'] for row in board['tasks']], [[], []])

    def test_duplicate_name_and_unknown_label_are_rejected(self):
        label = main.create_label(main.LabelInput(name='Cliente', color='#7399cd'))
        with self.assertRaises(HTTPException) as duplicate:
            main.create_label(main.LabelInput(name='Cliente', color='#000000'))
        self.assertEqual(duplicate.exception.status_code, 409)
        with self.assertRaises(HTTPException) as missing:
            main.create_task(self.task_input([label['id'] + 999]))
        self.assertEqual(missing.exception.status_code, 422)


if __name__ == '__main__':
    unittest.main()
