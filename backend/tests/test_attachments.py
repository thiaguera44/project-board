import asyncio
import base64
from pathlib import Path
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine

from app import main


class AttachmentsTest(unittest.TestCase):
    def setUp(self):
        self.temp_path = Path(__file__).parent / '.attachment-test-data'
        self.temp_path.mkdir(exist_ok=True)
        for path in self.temp_path.iterdir(): path.unlink()
        self.engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False})
        self.engine_patch = patch.object(main, 'engine', self.engine); self.engine_patch.start()
        self.dir_patch = patch.object(main, 'attachments_dir', self.temp_path); self.dir_patch.start()
        self.lifespan = main.lifespan(main.app); asyncio.run(self.lifespan.__aenter__())
        project = main.create_project(main.ProjectInput(name='Projeto'))
        self.task = main.create_task(main.TaskInput(title='Tarefa', project_id=project['id'], assignee='Ana'))

    def tearDown(self):
        asyncio.run(self.lifespan.__aexit__(None, None, None)); self.dir_patch.stop(); self.engine_patch.stop(); self.engine.dispose()
        for path in self.temp_path.iterdir(): path.unlink()

    def test_attachment_can_be_created_opened_archived_and_removed(self):
        content = b'conteudo do documento'
        attachment = main.create_attachment(self.task['id'], main.AttachmentInput(original_name='../relatorio.txt', content_base64=base64.b64encode(content).decode()))
        self.assertEqual(attachment['original_name'], 'relatorio.txt')
        self.assertEqual((self.temp_path / attachment['stored_name']).read_bytes(), content)
        self.assertEqual(main.download_attachment(attachment['id']).filename, 'relatorio.txt')
        main.archive_task(self.task['id'])
        self.assertEqual(main.board()['attachments'][0]['id'], attachment['id'])
        main.delete_attachment(attachment['id'])
        self.assertFalse((self.temp_path / attachment['stored_name']).exists())

    def test_limits_and_task_deletion_remove_file(self):
        with self.assertRaises(HTTPException):
            main.create_attachment(999, main.AttachmentInput(original_name='x.txt', content_base64='eA=='))
        attachment = main.create_attachment(self.task['id'], main.AttachmentInput(original_name='x.txt', content_base64='eA=='))
        main.delete_task(self.task['id'])
        self.assertEqual(main.board()['attachments'], [])
        self.assertFalse((self.temp_path / attachment['stored_name']).exists())

    def test_attachment_is_preserved_by_backup(self):
        attachment = main.create_attachment(self.task['id'], main.AttachmentInput(original_name='imagem.png', content_base64=base64.b64encode(b'png-data').decode()))
        backup = main.export_backup()
        main.delete_attachment(attachment['id'])
        main.restore_backup(main.BackupPayload.model_validate(backup))
        restored = main.board()['attachments'][0]
        self.assertEqual(restored['original_name'], 'imagem.png')
        self.assertEqual((self.temp_path / restored['stored_name']).read_bytes(), b'png-data')
