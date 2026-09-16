"""Launch Project Board as a local Windows desktop application."""

import os
from pathlib import Path
import sys
from threading import Thread
import time

import uvicorn
import webview


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
    try:
        webview.create_window('Project Board', f'http://127.0.0.1:{port}/', width=1280, height=800, min_size=(900, 600))
        webview.start()
    finally:
        server.should_exit = True
        thread.join(timeout=5)


if __name__ == '__main__':
    main()
