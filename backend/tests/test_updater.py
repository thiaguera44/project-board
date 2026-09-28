import json
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import updater


class FakeResponse:
    def __init__(self, content): self.content, self.offset = content, 0
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self, size=-1):
        if size < 0: result, self.offset = self.content[self.offset:], len(self.content)
        else: result, self.offset = self.content[self.offset:self.offset+size], self.offset+size
        return result


class UpdaterTest(unittest.TestCase):
    def test_release_comparison_and_asset_selection(self):
        info = updater.release_info({'tag_name':'v1.2.0','html_url':'https://github.com/thiaguera44/project-board/releases/tag/v1.2.0','body':'Novidades','assets':[{'name':'ProjectBoard.exe','browser_download_url':'https://github.com/thiaguera44/project-board/releases/download/v1.2.0/ProjectBoard.exe','digest':'sha256:abc'}]}, '1.1.0')
        self.assertTrue(info['available'])
        self.assertTrue(info['download_ready'])
        self.assertEqual(info['latest_version'], '1.2.0')
        self.assertFalse(updater.release_info({'tag_name':'v1.1.0','assets':[]}, '1.1.0')['available'])

    def test_download_requires_github_executable_and_checks_digest(self):
        content = b'MZ' + b'x' * 2048
        import hashlib
        target = Path(__file__).with_name('.update-test.exe')
        try:
            with patch.object(updater, 'urlopen', return_value=FakeResponse(content)):
                updater.download_executable('https://github.com/thiaguera44/project-board/releases/download/v2/ProjectBoard.exe', target, 'sha256:'+hashlib.sha256(content).hexdigest())
            self.assertEqual(target.read_bytes(), content)
            with self.assertRaises(ValueError): updater.download_executable('https://example.com/file.exe', target)
        finally:
            target.unlink(missing_ok=True)
            target.with_suffix('.download').unlink(missing_ok=True)

    def test_invalid_versions_are_rejected(self):
        with self.assertRaises(ValueError): updater.version_tuple('latest')


if __name__ == '__main__': unittest.main()
