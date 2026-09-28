import asyncio
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine

from app import main


class CommentsTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False})
        self.engine_patch = patch.object(main, 'engine', self.engine)
        self.engine_patch.start()
        self.lifespan = main.lifespan(main.app)
        asyncio.run(self.lifespan.__aenter__())
        project = main.create_project(main.ProjectInput(name='Projeto'))
        self.task = main.create_task(main.TaskInput(title='Tarefa', project_id=project['id'], assignee='Ana'))

    def tearDown(self):
        asyncio.run(self.lifespan.__aexit__(None, None, None))
        self.engine_patch.stop()
        self.engine.dispose()

    def test_comment_is_trimmed_and_preserved_when_task_is_archived(self):
        comment = main.create_comment(self.task['id'], main.CommentInput(author=' Ana ', content='  Decisão registrada.  '))
        self.assertEqual(comment['author'], 'Ana')
        self.assertEqual(comment['content'], 'Decisão registrada.')
        main.archive_task(self.task['id'])
        self.assertEqual(main.board()['comments'][0]['task_id'], self.task['id'])

    def test_comment_can_be_deleted_and_is_removed_with_task(self):
        comment = main.create_comment(self.task['id'], main.CommentInput(author='Ana', content='Atualização'))
        self.assertEqual(main.delete_comment(comment['id']), {'ok': True})
        self.assertEqual(main.board()['comments'], [])
        main.create_comment(self.task['id'], main.CommentInput(author='Ana', content='Outra'))
        main.delete_task(self.task['id'])
        self.assertEqual(main.board()['comments'], [])

    def test_missing_task_and_comment_return_not_found(self):
        with self.assertRaises(HTTPException) as task_error:
            main.create_comment(999, main.CommentInput(author='Ana', content='Texto'))
        self.assertEqual(task_error.exception.status_code, 404)
        with self.assertRaises(HTTPException) as comment_error:
            main.delete_comment(999)
        self.assertEqual(comment_error.exception.status_code, 404)


if __name__ == '__main__':
    unittest.main()
