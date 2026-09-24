import unittest
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


if __name__ == '__main__':
    unittest.main()
