"""Launch Project Board as a local Windows desktop application."""

import os
from pathlib import Path
import sys
from threading import Thread
import time

import uvicorn
import webview


class DesktopApi:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.timer_window = None

    def show_timer(self) -> bool:
        if self.timer_window is not None:
            self.timer_window.restore()
            return True
        window = webview.create_window(
            'Cronômetros · Project Board', f'{self.base_url}/timer',
            width=390, height=340, min_size=(320, 180), on_top=True,
        )
        self.timer_window = window
        window.events.closed += lambda *args: setattr(self, 'timer_window', None)
        return True

    def save_csv(self, filename: str, content: str) -> bool:
        safe_name = ''.join(character for character in filename if character not in '<>:"/\\|?*').strip() or 'relatorio.csv'
        if not safe_name.lower().endswith('.csv'):
            safe_name += '.csv'
        selected = webview.windows[0].create_file_dialog(
            webview.FileDialog.SAVE,
            save_filename=safe_name,
            file_types=('Arquivo CSV (*.csv)',),
        )
        if not selected:
            return False
        Path(selected[0]).write_text(content, encoding='utf-8-sig')
        return True

    def save_backup(self, filename: str, content: str) -> bool:
        safe_name = ''.join(character for character in filename if character not in '<>:"/\\|?*').strip() or 'project-board-backup.json'
        if not safe_name.lower().endswith('.json'):
            safe_name += '.json'
        selected = webview.windows[0].create_file_dialog(
            webview.FileDialog.SAVE,
            save_filename=safe_name,
            file_types=('Backup do Project Board (*.json)',),
        )
        if not selected:
            return False
        Path(selected[0]).write_text(content, encoding='utf-8')
        return True

    def load_backup(self) -> str | None:
        selected = webview.windows[0].create_file_dialog(
            webview.FileDialog.OPEN,
            allow_multiple=False,
            file_types=('Backup do Project Board (*.json)',),
        )
        if not selected:
            return None
        path = Path(selected[0])
        if path.stat().st_size > 20 * 1024 * 1024:
            raise ValueError('O arquivo de backup ultrapassa o limite de 20 MB.')
        return path.read_text(encoding='utf-8-sig')


def main() -> None:
    app_data = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    data_dir = app_data / 'Project Board'
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ['PROJECT_BOARD_DATA_DIR'] = str(data_dir)
    os.environ['PROJECT_BOARD_DESKTOP'] = '1'

    # Keep the backend importable both from the repository and a PyInstaller bundle.
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    sys.path.insert(0, str(root / 'backend'))
    from app.main import app

    config = uvicorn.Config(app, host='127.0.0.1', port=0, log_level='warning', access_log=False)
    server = uvicorn.Server(config)
    thread = Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started and server.servers:
            break
        if not thread.is_alive():
            raise RuntimeError('Não foi possível iniciar a API local.')
        time.sleep(0.1)
    else:
        raise RuntimeError('A API local demorou demais para iniciar.')

    port = server.servers[0].sockets[0].getsockname()[1]
    base_url = f'http://127.0.0.1:{port}'
    try:
        webview.create_window('Project Board', f'{base_url}/', width=1280, height=800, min_size=(900, 600), js_api=DesktopApi(base_url))
        webview.start()
    finally:
        server.should_exit = True
        thread.join(timeout=5)


if __name__ == '__main__':
    main()
