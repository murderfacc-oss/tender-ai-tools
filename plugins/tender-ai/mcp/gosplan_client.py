"""ГосПлан API v2 — HTTP-клиент. Только GET. Без сторонних зависимостей
кроме requests."""
from __future__ import annotations

import os
import time
from pathlib import Path

import requests

BASE_URL = "https://v2.gosplan.info"
USER_AGENT = "tender-ai-tools/0.7 (+https://github.com/murderfacc-oss/tender-ai-tools)"
# Предполагаемая схема передачи ключа (ключи обязательны с 2026-07-01).
# Когда ГосПлан опубликует точный механизм — поменять только эту константу.
API_KEY_HEADER = "X-API-Key"
TIMEOUT = 60
MAX_RETRIES = 3
RETRY_WAIT = 60  # сек, по spike: 429 → пауза 60с


class GosplanError(RuntimeError):
    pass


class GosplanNotFound(GosplanError):
    pass


def _headers() -> dict:
    h = {"User-Agent": USER_AGENT}
    key = os.environ.get("GOSPLAN_API_KEY")
    if key:
        h[API_KEY_HEADER] = key
    return h


def _get_json(path: str) -> dict:
    url = f"{BASE_URL}{path}"
    attempt = 0
    while True:
        resp = requests.get(url, headers=_headers(), timeout=TIMEOUT)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 404:
            raise GosplanNotFound(
                f"не найдено в ГосПлан API: {path}. Для 223-ФЗ возможно вне "
                f"покрытия API — проверьте номер или скачайте вручную с "
                f"zakupki.gov.ru"
            )
        if resp.status_code == 429 and attempt < MAX_RETRIES:
            attempt += 1
            time.sleep(RETRY_WAIT)
            continue
        if resp.status_code == 429:
            raise GosplanError("лимит запросов ГосПлан (429), повторите позже")
        raise GosplanError(f"ГосПлан API вернул HTTP {resp.status_code} на {path}")


def get_purchase(fz: int, number: str) -> dict:
    return _get_json(f"/fz{fz}/purchases/{number}")


def get_contract(fz: int, reg_num: str) -> dict:
    return _get_json(f"/fz{fz}/contracts/{reg_num}")


def get_contract_procedures(fz: int, reg_num: str) -> list:
    """Этапы исполнения контракта (КС-2/КС-3/приёмка/платёжки/экспертиза).
    Возвращает список. 404 = у контракта нет этапов исполнения — это
    валидно (контракт ещё не исполнялся), отдаём []."""
    try:
        data = _get_json(f"/fz{fz}/contracts/{reg_num}/procedures")
    except GosplanNotFound:
        return []
    return data if isinstance(data, list) else []


def download_file(url: str, dest: Path) -> int:
    """Качает файл во временный .part рядом, переименовывает при успехе.
    Возвращает размер в байтах. Битых частичных файлов не оставляет."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        resp = requests.get(url, headers=_headers(), timeout=TIMEOUT, stream=True)
        if resp.status_code != 200:
            raise GosplanError(f"скачивание {url}: HTTP {resp.status_code}")
        size = 0
        with open(tmp, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    fh.write(chunk)
                    size += len(chunk)
        tmp.replace(dest)
        return size
    except requests.RequestException as e:
        raise GosplanError(f"сеть при скачивании {url}: {e}") from e
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
