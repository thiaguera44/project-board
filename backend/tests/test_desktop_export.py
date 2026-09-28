import unittest
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import desktop


class FakeWindow:
    def __init__(self, path):
        self.path = path
        self.arguments = None

    def create_file_dialog(self, *args, **kwargs):
        self.arguments = (args, kwargs)
        return [str(self.path)]


class DesktopExportTest(unittest.TestCase):
    def test_pdf_report_is_created(self):
        target = Path(__file__).with_name('.report-test.pdf')
        try:
            window = FakeWindow(target)
            content = json.dumps({'title': 'Relatório de teste', 'generated_at': '28/09/2026', 'filters': {'period': 'Setembro', 'project': 'Todos'}, 'summary': [['Realizado', '2h']], 'comparisons': [['Tarefa', 'Projeto', '1h', '2h', '+1h']], 'overdue': [], 'productivity': [['20/09/2026', '2h']], 'entries': []})
            with patch.object(desktop.webview, 'windows', [window]):
                self.assertTrue(desktop.DesktopApi('http://localhost').save_pdf('relatório?.pdf', content))
            self.assertTrue(target.read_bytes().startswith(b'%PDF'))
            self.assertGreater(target.stat().st_size, 1000)
            self.assertEqual(window.arguments[1]['save_filename'], 'relatório.pdf')
        finally:
            target.unlink(missing_ok=True)

    def test_csv_is_saved_with_excel_compatible_encoding(self):
        target = Path(__file__).with_name('.export-test.csv')
        try:
            window = FakeWindow(target)
            with patch.object(desktop.webview, 'windows', [window]):
                saved = desktop.DesktopApi('http://localhost').save_csv(
                    'relatório?.csv',
                    '"Data";"Observação"\r\n"24/09/2026";"Revisão"',
                )

            self.assertTrue(saved)
            self.assertTrue(target.read_bytes().startswith(b'\xef\xbb\xbf'))
            self.assertIn('Revisão', target.read_text(encoding='utf-8-sig'))
            self.assertEqual(window.arguments[1]['save_filename'], 'relatório.csv')
        finally:
            target.unlink(missing_ok=True)

    def test_backup_is_saved_and_loaded_as_utf8_json(self):
        target = Path(__file__).with_name('.backup-test.json')
        try:
            window = FakeWindow(target)
            api = desktop.DesktopApi('http://localhost')
            with patch.object(desktop.webview, 'windows', [window]):
                self.assertTrue(api.save_backup('cópia?.json', '{"nome":"Revisão"}'))
                self.assertEqual(api.load_backup(), '{"nome":"Revisão"}')

            self.assertEqual(window.arguments[0][0], desktop.webview.FileDialog.OPEN)
            self.assertEqual(target.read_text(encoding='utf-8'), '{"nome":"Revisão"}')
        finally:
            target.unlink(missing_ok=True)


if __name__ == '__main__':
    unittest.main()
