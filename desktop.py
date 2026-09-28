"""Launch Project Board as a local Windows desktop application."""

import os
import base64
import json
from datetime import date
from html import escape
from pathlib import Path
import subprocess
import sys
from threading import Event, Thread
import time
from urllib.request import urlopen

import uvicorn
import webview
from updater import APP_VERSION, check_latest_release, download_executable, version_tuple


def show_windows_notification(title: str, message: str) -> bool:
    xml = (f'<toast><visual><binding template="ToastGeneric"><text>Project Board · {escape(title)}</text>'
           f'<text>{escape(message)}</text></binding></visual></toast>')
    xml_base64 = base64.b64encode(xml.encode('utf-8')).decode('ascii')
    script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null
$content = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{xml_base64}'))
$document = [Windows.Data.Xml.Dom.XmlDocument]::new()
$document.LoadXml($content)
$toast = [Windows.UI.Notifications.ToastNotification]::new($document)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Microsoft.WindowsPowerShell').Show($toast)
"""
    encoded = base64.b64encode(script.encode('utf-16-le')).decode('ascii')
    try:
        completed = subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
            capture_output=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), timeout=10,
        )
        return completed.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def notification_worker(base_url: str, data_dir: Path, stop: Event) -> None:
    from app.notifications import mark_notified, notification_events

    state_path = data_dir / 'notification_state.json'
    try:
        state = json.loads(state_path.read_text(encoding='utf-8')) if state_path.is_file() else {}
    except (OSError, ValueError, TypeError):
        state = {}
    while not stop.is_set():
        try:
            with urlopen(f'{base_url}/api/settings', timeout=5) as response:
                settings = json.load(response)
            with urlopen(f'{base_url}/api/board', timeout=5) as response:
                board = json.load(response)
            events, state = notification_events(board, state, date.today())
            if settings.get('notifications_enabled', True):
                for event in events:
                    if show_windows_notification(event['title'], event['message']):
                        mark_notified(state, event['key'])
            state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        except (OSError, ValueError, TypeError):
            pass
        stop.wait(60)


class DesktopApi:
    def __init__(self, base_url: str, data_dir: Path | None = None) -> None:
        self.base_url = base_url
        self.attachments_dir = (data_dir or Path.cwd()) / 'attachments'
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

    def check_update(self) -> dict:
        try:
            return {'status': 'ok', **check_latest_release(APP_VERSION)}
        except Exception:
            return {'status': 'error', 'current_version': APP_VERSION, 'message': 'Não foi possível consultar novas versões agora.'}

    def install_update(self, asset_url: str, version: str, digest: str = '') -> dict:
        if not getattr(sys, 'frozen', False):
            return {'status': 'error', 'message': 'A instalação automática está disponível no executável publicado.'}
        version_tuple(version)
        updates_dir = self.attachments_dir.parent / 'updates'
        downloaded = download_executable(asset_url, updates_dir / f'ProjectBoard-{version}.exe', digest)
        current = Path(sys.executable).resolve()
        script = f"""
$processId = {os.getpid()}
$source = '{str(downloaded).replace("'", "''")}'
$target = '{str(current).replace("'", "''")}'
Wait-Process -Id $processId -ErrorAction SilentlyContinue
$backup = $target + '.anterior'
Remove-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue
Move-Item -LiteralPath $target -Destination $backup -Force
Move-Item -LiteralPath $source -Destination $target -Force
Start-Process -FilePath $target
"""
        encoded = base64.b64encode(script.encode('utf-16-le')).decode('ascii')
        subprocess.Popen(['powershell.exe', '-NoProfile', '-NonInteractive', '-WindowStyle', 'Hidden', '-EncodedCommand', encoded], creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        def close_after_response():
            time.sleep(1)
            if webview.windows:
                webview.windows[0].destroy()
        Thread(target=close_after_response, daemon=True).start()
        return {'status': 'installing'}

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

    def save_pdf(self, filename: str, content: str) -> bool:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        safe_name = ''.join(character for character in filename if character not in '<>:"/\\|?*').strip() or 'relatorio.pdf'
        if not safe_name.lower().endswith('.pdf'):
            safe_name += '.pdf'
        selected = webview.windows[0].create_file_dialog(webview.FileDialog.SAVE, save_filename=safe_name, file_types=('Arquivo PDF (*.pdf)',))
        if not selected:
            return False
        data = json.loads(content)
        styles = getSampleStyleSheet()
        document = SimpleDocTemplate(str(selected[0]), pagesize=landscape(A4), rightMargin=14*mm, leftMargin=14*mm, topMargin=12*mm, bottomMargin=12*mm)
        story = [Paragraph(escape(str(data.get('title', 'Relatório'))), styles['Title']), Paragraph(f"Gerado em {escape(str(data.get('generated_at', '')))}", styles['Normal']), Spacer(1, 4*mm)]
        filters = data.get('filters', {})
        story.extend([Paragraph(f"<b>Período:</b> {escape(str(filters.get('period', '')))} &nbsp;&nbsp; <b>Projeto:</b> {escape(str(filters.get('project', '')))}", styles['Normal']), Spacer(1, 5*mm)])

        def add_table(title, headers, rows, widths=None):
            story.extend([Paragraph(escape(title), styles['Heading2']), Spacer(1, 1.5*mm)])
            if not rows:
                story.extend([Paragraph('Nenhum registro encontrado.', styles['Normal']), Spacer(1, 4*mm)])
                return
            values = [[Paragraph(f'<b>{escape(str(cell))}</b>', styles['BodyText']) for cell in headers]]
            values += [[Paragraph(escape(str(cell)), styles['BodyText']) for cell in row] for row in rows]
            table = Table(values, colWidths=widths, repeatRows=1, hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#6f4d42')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),.35,colors.HexColor('#d7dfe4')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f6f7f8')])]))
            story.extend([table, Spacer(1, 5*mm)])

        add_table('Resumo', ['Indicador', 'Valor'], data.get('summary', []), [75*mm, 45*mm])
        add_table('Estimado x realizado', ['Tarefa', 'Projeto', 'Estimado', 'Realizado', 'Diferença'], data.get('comparisons', []), [70*mm, 55*mm, 30*mm, 30*mm, 30*mm])
        add_table('Tarefas atrasadas', ['Tarefa', 'Projeto', 'Prazo', 'Dias'], data.get('overdue', []), [85*mm, 65*mm, 35*mm, 25*mm])
        add_table('Produtividade diária', ['Data', 'Tempo realizado'], data.get('productivity', []), [60*mm, 60*mm])
        add_table('Lançamentos de horas', ['Data', 'Projeto', 'Tarefa', 'Observação', 'Horas'], data.get('entries', []), [28*mm, 45*mm, 55*mm, 75*mm, 25*mm])
        document.build(story)
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
        if path.stat().st_size > 200 * 1024 * 1024:
            raise ValueError('O arquivo de backup ultrapassa o limite de 200 MB.')
        return path.read_text(encoding='utf-8-sig')

    def open_attachment(self, stored_name: str) -> bool:
        if stored_name != Path(stored_name).name:
            return False
        path = self.attachments_dir / stored_name
        if not path.is_file():
            return False
        os.startfile(path)
        return True


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
    notification_stop = Event()
    notification_thread = Thread(target=notification_worker, args=(base_url, data_dir, notification_stop), daemon=True)
    notification_thread.start()
    try:
        webview.create_window('Project Board', f'{base_url}/', width=1280, height=800, min_size=(900, 600), js_api=DesktopApi(base_url, data_dir))
        webview.start()
    finally:
        notification_stop.set()
        notification_thread.join(timeout=2)
        server.should_exit = True
        thread.join(timeout=5)


if __name__ == '__main__':
    main()
