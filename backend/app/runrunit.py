"""Small Runrun.it API client and local protected credential storage."""
from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class RunrunError(Exception):
    pass


class _Blob(ctypes.Structure):
    _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_char))]


def _blob(data: bytes):
    buffer = ctypes.create_string_buffer(data)
    return _Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))), buffer


def _protect(data: bytes) -> bytes:
    if not hasattr(ctypes, 'windll'):
        return data
    source, keepalive = _blob(data)
    target = _Blob()
    if not ctypes.windll.crypt32.CryptProtectData(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(target)):
        raise OSError('Não foi possível proteger as credenciais.')
    try:
        return ctypes.string_at(target.pbData, target.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(target.pbData)


def _unprotect(data: bytes) -> bytes:
    if not hasattr(ctypes, 'windll'):
        return data
    source, keepalive = _blob(data)
    target = _Blob()
    if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(target)):
        raise OSError('Não foi possível abrir as credenciais salvas.')
    try:
        return ctypes.string_at(target.pbData, target.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(target.pbData)


class CredentialStore:
    def __init__(self, path: Path): self.path = path
    def save(self, app_key: str, user_token: str):
        raw = json.dumps({'app_key': app_key.strip(), 'user_token': user_token.strip()}).encode()
        self.path.write_bytes(base64.b64encode(_protect(raw)))
    def load(self) -> dict[str, str] | None:
        if not self.path.is_file(): return None
        try: return json.loads(_unprotect(base64.b64decode(self.path.read_bytes())).decode())
        except Exception as exc: raise RunrunError('As credenciais salvas não puderam ser lidas.') from exc


class RunrunClient:
    def __init__(self, app_key: str, user_token: str, opener=urlopen, base_url='https://runrun.it/api/v1.0'):
        self.base_url, self.opener = base_url.rstrip('/'), opener
        self.headers = {'App-Key': app_key, 'User-Token': user_token, 'Content-Type': 'application/json', 'Accept': 'application/json'}
    def _request(self, path: str, method='GET', body=None, query=None):
        url = self.base_url + path + (('?' + urlencode(query)) if query else '')
        request = Request(url, data=json.dumps(body).encode() if body is not None else None, headers=self.headers, method=method)
        try:
            with self.opener(request, timeout=30) as response:
                payload = response.read()
                return json.loads(payload.decode()) if payload else {}
        except HTTPError as exc:
            messages = {401:'Credenciais recusadas pelo Runrun.it.',403:'Seu usuário não tem permissão para esta ação.',404:'Recurso não encontrado no Runrun.it.',429:'O limite de consultas do Runrun.it foi atingido. Tente novamente em alguns minutos.'}
            raise RunrunError(messages.get(exc.code, f'O Runrun.it retornou um erro ({exc.code}).')) from exc
        except (URLError, TimeoutError) as exc:
            raise RunrunError('Não foi possível conectar ao Runrun.it.') from exc
    def test(self): return self._request('/projects', query={'limit':1})
    def boards(self):
        boards = {}
        for row in self._task_pages({}):
            board_id = row.get('board_id')
            if board_id:
                boards[board_id] = {'id': board_id, 'name': row.get('board_name') or f'Quadro {board_id}'}
        return list(boards.values())
    def projects(self): return self._request('/projects')
    def users(self): return self._request('/users')
    def stages(self, board_id: int): return self._request(f'/boards/{board_id}/stages')
    def _task_pages(self, filters):
        output=[]
        for page in range(1, 101):
            batch=self._request('/tasks', query={**filters,'page':page,'limit':100})
            rows=batch.get('tasks', batch) if isinstance(batch, dict) else batch
            output.extend(rows)
            if len(rows)<100: break
        return output
    def tasks(self, board_id: int): return self._task_pages({'board_id':board_id})
    def add_manual_work(self, task_id: int, seconds: int, date_to_apply: str):
        return self._request('/manual_work_periods','POST',{'manual_work_period':{'task_id':task_id,'seconds':seconds,'date_to_apply':date_to_apply}})
    def move_task(self, task_id: int, board_stage_id: int):
        return self._request(f'/tasks/{task_id}/move','POST',{'board_stage_id':board_stage_id})
