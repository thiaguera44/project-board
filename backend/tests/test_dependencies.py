import asyncio
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine

from app import main


class DependenciesTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False})
        self.engine_patch = patch.object(main, 'engine', self.engine)
        self.engine_patch.start()
        self.lifespan = main.lifespan(main.app)
        asyncio.run(self.lifespan.__aenter__())
        project = main.create_project(main.ProjectInput(name='Projeto'))
        self.project_id = project['id']
        self.first = main.create_task(self.input('Preparar conteúdo'))
        self.second = main.create_task(self.input('Publicar', dependency_ids=[self.first['id']]))

    def tearDown(self):
        asyncio.run(self.lifespan.__aexit__(None, None, None))
        self.engine_patch.stop()
        self.engine.dispose()

    def input(self, title, status='todo', dependency_ids=None):
        return main.TaskInput(title=title, project_id=self.project_id, assignee='Ana', status=status, dependency_ids=dependency_ids or [])

    def test_dependency_is_returned_and_blocks_completion(self):
        task = next(row for row in main.board()['tasks'] if row['id'] == self.second['id'])
        self.assertEqual(task['dependency_ids'], [self.first['id']])
        with self.assertRaises(HTTPException) as blocked:
            main.update_task(self.second['id'], self.input('Publicar', status='done', dependency_ids=[self.first['id']]))
        self.assertEqual(blocked.exception.status_code, 409)

        main.update_task(self.first['id'], self.input('Preparar conteúdo', status='done'))
        completed = main.update_task(self.second['id'], self.input('Publicar', status='done', dependency_ids=[self.first['id']]))
        self.assertEqual(completed['status'], 'done')

    def test_circular_and_self_dependencies_are_rejected(self):
        with self.assertRaises(HTTPException) as cycle:
            main.update_task(self.first['id'], self.input('Preparar conteúdo', dependency_ids=[self.second['id']]))
        self.assertEqual(cycle.exception.status_code, 422)
        with self.assertRaises(HTTPException) as itself:
            main.update_task(self.first['id'], self.input('Preparar conteúdo', dependency_ids=[self.first['id']]))
        self.assertEqual(itself.exception.status_code, 422)

    def test_deleting_task_removes_dependency_links(self):
        main.delete_task(self.first['id'])
        task = next(row for row in main.board()['tasks'] if row['id'] == self.second['id'])
        self.assertEqual(task['dependency_ids'], [])


if __name__ == '__main__':
    unittest.main()
