"""GitHub release checks and safe executable downloads for Project Board."""

import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

APP_VERSION = '1.1.0'
REPOSITORY = 'thiaguera44/project-board'
LATEST_RELEASE_URL = f'https://api.github.com/repos/{REPOSITORY}/releases/latest'


def version_tuple(value: str) -> tuple[int, ...]:
    clean = value.strip().lower().removeprefix('v').split('-', 1)[0]
    parts = clean.split('.')
    if not parts or any(not part.isdigit() for part in parts):
        raise ValueError('Versão inválida recebida do GitHub.')
    return tuple(int(part) for part in parts)


def release_info(payload: dict, current_version: str = APP_VERSION) -> dict:
    tag = str(payload.get('tag_name', ''))
    latest = tag.removeprefix('v')
    assets = payload.get('assets') if isinstance(payload.get('assets'), list) else []
    asset = next((item for item in assets if str(item.get('name', '')).lower() == 'projectboard.exe'), None)
    available = version_tuple(latest) > version_tuple(current_version)
    return {
        'current_version': current_version,
        'latest_version': latest,
        'available': available,
        'download_ready': bool(asset),
        'asset_url': asset.get('browser_download_url', '') if asset else '',
        'asset_digest': asset.get('digest', '') if asset else '',
        'release_url': str(payload.get('html_url', '')),
        'notes': str(payload.get('body', ''))[:2000],
    }


def check_latest_release(current_version: str = APP_VERSION) -> dict:
    request = Request(LATEST_RELEASE_URL, headers={'Accept': 'application/vnd.github+json', 'User-Agent': f'ProjectBoard/{current_version}', 'X-GitHub-Api-Version': '2022-11-28'})
    with urlopen(request, timeout=12) as response:
        return release_info(json.load(response), current_version)


def download_executable(url: str, target: Path, digest: str = '') -> Path:
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in {'github.com', 'objects.githubusercontent.com'}:
        raise ValueError('Endereço de atualização não reconhecido.')
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix('.download')
    request = Request(url, headers={'User-Agent': f'ProjectBoard/{APP_VERSION}'})
    hasher = hashlib.sha256()
    try:
        with urlopen(request, timeout=60) as response, partial.open('wb') as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
                hasher.update(chunk)
        if partial.stat().st_size < 1024 or partial.read_bytes()[:2] != b'MZ':
            raise ValueError('O arquivo baixado não é um executável válido.')
        if digest.startswith('sha256:') and hasher.hexdigest().lower() != digest[7:].lower():
            raise ValueError('A verificação de integridade da atualização falhou.')
        partial.replace(target)
        return target
    except Exception:
        partial.unlink(missing_ok=True)
        raise
