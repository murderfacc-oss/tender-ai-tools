# -*- coding: utf-8 -*-
"""
Модуль для скачивания документов закупок с zakupki.gov.ru.
Без API-ключей, без регистрации — работает через открытые страницы ЕИС.

Основные функции:
- download_tender(reg_number, folder)  — скачать все документы закупки
- check_updates(folder)               — проверить есть ли новые/изменённые файлы
- update_tender(folder)               — скачать обновления и показать что изменилось
"""

import os
import re
import json
import hashlib
import urllib.parse
from pathlib import Path
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# ───────────────────────────── Константы ──────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Типы закупок для перебора при поиске страницы документов
NOTICE_TYPES = [
    "ea44", "ok44", "zk44",        # 44-ФЗ: аукцион, конкурс, закрытая
    "ea20", "ok20", "zk20",        # 44-ФЗ: новые форматы
    "ea223", "ok223", "pp223",     # 223-ФЗ
    "ea615", "ok615",              # 615-ПП (капремонт)
]

META_FILENAME = ".tender_meta.json"
CONTRACT_META_FILENAME = ".contract_meta.json"
CONTRACT_FOLDER_NAME = "Контракт"

# ─────────────────── Классификация документов по папкам ───────────────────
#
# Каждая категория: (номер_папки, имя_папки, [ключевые слова])
# Ключевые слова проверяются в имени документа (link text с сайта).
# Порядок важен — первое совпадение выигрывает.

CATEGORIES = [
    ("1_ТЗ", [
        "техническое задание", "техзадание", " тз ", "тз.", "тз_",
        "задание на", "описание объекта", "требования к",
    ]),
    ("2_Контракт", [
        "проект контракта", "проект договора", "контракт", "договор",
        "форма контракта", "форма договора",
    ]),
    ("3_НМЦК", [
        "нмцк", "расчет нм", "расчёт нм", "обоснование нм",
        "обоснование цены", "протокол цк", "протокол ценовых",
        "ценовой запрос", "коммерческое предложение",
    ]),
    ("4_Смета", [
        "смета", "ведомость объёмов", "ведомость объемов",
        "лср", "локальная смета", "сводная смета", "бор",
    ]),
    ("5_Документация", [
        "документация", "аукционная", "конкурсная",
        "извещение", "electronic", "auction",
        "electronicauction", "описание закупки",
    ]),
    ("6_Протоколы", [
        "протокол", "итог", "результат", "рассмотрение заявок",
        "итоговый", "вскрытие",
    ]),
    # 7_Прочее — для всего что не попало выше
]

DEFAULT_CATEGORY = "7_Прочее"


def _classify_doc(name: str) -> str:
    """
    Определяет папку для документа по его названию.
    name — текст ссылки со страницы закупки (читаемое описание).
    """
    low = name.lower()
    for folder, keywords in CATEGORIES:
        for kw in keywords:
            if kw in low:
                return folder
    return DEFAULT_CATEGORY


# ─────────────────────────── Вспомогательные ──────────────────────────────

def _sanitize_filename(name: str) -> str:
    """Убирает из имени файла запрещённые символы Windows/Linux"""
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    name = name.strip(". ")
    return name[:100]  # Ограничиваем длину


def _sha256(filepath: str) -> str:
    """Считаем SHA-256 хеш файла для отслеживания изменений"""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _load_meta(folder: str) -> dict:
    """Загружаем .tender_meta.json из папки закупки"""
    meta_path = os.path.join(folder, META_FILENAME)
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_meta(folder: str, meta: dict):
    """Сохраняем .tender_meta.json"""
    meta_path = os.path.join(folder, META_FILENAME)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


# ──────────────────────── Получение списка документов ─────────────────────

def _get_docs_page(reg_number: str):
    """
    Находит страницу документов закупки.
    Перебирает типы закупок (ea44, ok44 и т.д.) пока не найдёт рабочую.

    Возвращает: (html_text, final_url, notice_type) или (None, None, None)
    """
    session = requests.Session()
    for notice_type in NOTICE_TYPES:
        url = (
            f"https://zakupki.gov.ru/epz/order/notice/{notice_type}"
            f"/view/documents.html?regNumber={reg_number}"
        )
        try:
            r = session.get(url, headers=HEADERS, timeout=25, allow_redirects=True)
            if r.status_code != 200:
                continue
            # Страница не найдена если в URL нет номера закупки
            if reg_number not in r.url and "documents.html" not in r.url:
                continue
            # Признак реальной страницы закупки — наличие ссылок на документы
            if "filestore" in r.text or "downloadDocument" in r.text:
                return r.text, r.url, notice_type
        except requests.RequestException:
            continue
    return None, None, None


def _extract_docs(html: str) -> list:
    """
    Вытаскивает список документов из HTML страницы.
    Возвращает список словарей: [{uid, name, url}, ...]
    """
    soup = BeautifulSoup(html, "html.parser")
    docs = []
    seen_uids = set()

    # Основной формат 44-ФЗ: /44fz/filestore/public/1.0/download/...?uid=XXXX
    for a in soup.select("a[href*='filestore'][href*='download']"):
        href = a.get("href", "")
        # Вытаскиваем uid из URL
        parsed = urllib.parse.urlparse(href)
        params = urllib.parse.parse_qs(parsed.query)
        uid = params.get("uid", [None])[0]

        if not uid or uid in seen_uids:
            continue
        seen_uids.add(uid)

        name = a.text.strip() or f"document_{uid[:8]}"
        # Убеждаемся что URL абсолютный
        if href.startswith("/"):
            href = "https://zakupki.gov.ru" + href

        docs.append({"uid": uid, "name": name, "url": href})

    # Запасной вариант: старый формат downloadDocument?id=XXX
    for a in soup.select("a[href*='downloadDocument']"):
        href = a.get("href", "")
        parsed = urllib.parse.urlparse(href)
        params = urllib.parse.parse_qs(parsed.query)
        doc_id = params.get("id", [None])[0]

        if not doc_id or doc_id in seen_uids:
            continue
        seen_uids.add(doc_id)

        name = a.text.strip() or f"document_{doc_id}"
        if href.startswith("/"):
            href = "https://zakupki.gov.ru" + href

        docs.append({"uid": doc_id, "name": name, "url": href})

    return docs


# ─────────────────────────── Скачивание файла ─────────────────────────────

def _download_file(url: str, folder: str, suggested_name: str) -> dict:
    """
    Скачивает один файл в папку folder.
    Имя берём из Content-Disposition заголовка, или из suggested_name.

    Возвращает: {filename, size_bytes, sha256} или {error: ...}
    """
    try:
        r = requests.get(url, headers=HEADERS, timeout=60, stream=True)
        r.raise_for_status()

        # Имя файла из заголовка
        filename = None
        cd = r.headers.get("Content-Disposition", "")
        if cd:
            # Пробуем UTF-8 вариант: filename*=UTF-8''name.pdf
            match = re.search(r"filename\*=UTF-8''(.+)", cd, re.IGNORECASE)
            if match:
                filename = urllib.parse.unquote(match.group(1))
            else:
                # Обычный вариант: filename="name.pdf"
                match = re.search(r'filename=["\']?([^"\';\n]+)', cd, re.IGNORECASE)
                if match:
                    filename = match.group(1).strip('"\'')
                    # requests читает HTTP-заголовки как latin-1, но zakupki.gov.ru
                    # шлёт имена файлов в UTF-8. Восстанавливаем оригинальные байты
                    # через latin-1, затем декодируем как UTF-8:
                    try:
                        filename = filename.encode('latin-1').decode('utf-8')
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        try:
                            # Запасной вариант: старые сайты могут использовать CP1251
                            filename = filename.encode('latin-1').decode('cp1251')
                        except (UnicodeDecodeError, UnicodeEncodeError):
                            pass  # Оставляем как есть

        # Если из заголовка не вышло — используем suggested_name
        if not filename:
            # Добавляем расширение из Content-Type
            ct = r.headers.get("Content-Type", "")
            ext_map = {
                "pdf": ".pdf", "msword": ".doc",
                "vnd.openxmlformats-officedocument.wordprocessingml": ".docx",
                "vnd.ms-excel": ".xls",
                "vnd.openxmlformats-officedocument.spreadsheetml": ".xlsx",
                "zip": ".zip", "xml": ".xml", "jpeg": ".jpg", "png": ".png",
            }
            ext = ".bin"
            for key, val in ext_map.items():
                if key in ct:
                    ext = val
                    break
            filename = _sanitize_filename(suggested_name) + ext

        filename = _sanitize_filename(filename)
        filepath = os.path.join(folder, filename)

        # Если файл с таким именем уже есть — добавляем суффикс
        if os.path.exists(filepath):
            base, ext = os.path.splitext(filename)
            i = 1
            while os.path.exists(filepath):
                filepath = os.path.join(folder, f"{base}_{i}{ext}")
                i += 1
            filename = os.path.basename(filepath)

        # Сохраняем файл
        size = 0
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
                size += len(chunk)

        sha = _sha256(filepath)
        return {"filename": filename, "size_bytes": size, "sha256": sha}

    except Exception as e:
        return {"error": str(e)}


# ───────────── Реестр контрактов: поиск и скачивание документов ───────────

def _find_contract_by_notice(notice_reg_number: str, notice_type_hint: str = None) -> str | None:
    """
    Находит реестровый номер контракта по номеру извещения.
    Идёт на страницу supplier-results.html извещения и ищет ссылку на карточку
    контракта вида /epz/contract/contractCard/...?reestrNumber=NNN

    Параметры:
        notice_reg_number  : номер извещения (закупки)
        notice_type_hint   : тип извещения (ea44, ok44, ...) если уже известен

    Возвращает: реестровый номер контракта (строка) или None если контракт не найден
                или конкурс ещё не завершён.
    """
    session = requests.Session()
    types_to_try = [notice_type_hint] if notice_type_hint else NOTICE_TYPES
    types_to_try = [t for t in types_to_try if t]  # убираем None

    for notice_type in types_to_try:
        url = (
            f"https://zakupki.gov.ru/epz/order/notice/{notice_type}"
            f"/view/supplier-results.html?regNumber={notice_reg_number}"
        )
        try:
            r = session.get(url, headers=HEADERS, timeout=25, allow_redirects=True)
            if r.status_code != 200:
                continue
            # Ищем ссылку на карточку контракта в реестре
            # Формат: /epz/contract/contractCard/common-info.html?reestrNumber=NNNN
            match = re.search(
                r'/epz/contract/contractCard/[^"\']*reestrNumber=(\d+)',
                r.text
            )
            if match:
                return match.group(1)
        except requests.RequestException:
            continue

    return None


def _get_contract_docs_page(contract_reestr_number: str):
    """
    Получает страницу документов контракта из реестра контрактов.
    URL: /epz/contract/contractCard/document-info.html?reestrNumber=NNN

    Возвращает: (html_text, final_url) или (None, None)
    """
    url = (
        f"https://zakupki.gov.ru/epz/contract/contractCard/document-info.html"
        f"?reestrNumber={contract_reestr_number}"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=25, allow_redirects=True)
        if r.status_code != 200:
            return None, None
        # Признак реальной страницы — наличие ссылок на файлы
        if "filestore" not in r.text and "downloadDocument" not in r.text:
            return None, None
        return r.text, r.url
    except requests.RequestException:
        return None, None


def download_contract(contract_reestr_number: str, folder: str) -> dict:
    """
    Скачивает все документы подписанного контракта из реестра контрактов
    в подпапку "Контракт/" внутри указанной папки закупки.

    На странице контракта обычно есть несколько групп документов:
      - Информация о контракте (подписанный контракт, печатная форма, электронный)
      - Исполнение контракта — Этап 1, Этап 2, ... (КС-2, КС-3, документы о приёмке,
        платёжные поручения, акты экспертизы)

    Все файлы складываются плоско в подпапку "Контракт/" (без подразделения по этапам).
    Метаданные сохраняются в .contract_meta.json в самой папке "Контракт/".

    Параметры:
        contract_reestr_number : реестровый номер контракта (например 3366503536925000015)
        folder                 : путь к папке закупки (туда уже могут быть скачаны
                                 документы извещения через download_tender).
                                 Подпапка "Контракт/" будет создана внутри.

    Возвращает: словарь с результатами {ok, downloaded, errors, files, folder}
    """
    os.makedirs(folder, exist_ok=True)
    contract_folder = os.path.join(folder, CONTRACT_FOLDER_NAME)
    os.makedirs(contract_folder, exist_ok=True)

    # Получаем страницу с документами контракта
    html, page_url = _get_contract_docs_page(contract_reestr_number)
    if not html:
        return {
            "ok": False,
            "error": (
                f"Страница документов контракта {contract_reestr_number} не найдена "
                f"в реестре контрактов на zakupki.gov.ru"
            ),
        }

    # Извлекаем список документов (тот же парсер что для извещения — формат ссылок похожий)
    docs = _extract_docs(html)
    if not docs:
        return {
            "ok": False,
            "error": "Документы на странице контракта не обнаружены",
        }

    # Скачиваем каждый файл — все плоско в Контракт/
    downloaded = []
    errors = []
    for doc in docs:
        result = _download_file(doc["url"], contract_folder, doc["name"])
        if "error" in result:
            errors.append({"name": doc["name"], "error": result["error"]})
        else:
            downloaded.append({
                "uid": doc["uid"],
                "name": doc["name"],
                "filename": result["filename"],
                "size_bytes": result["size_bytes"],
                "sha256": result["sha256"],
                "url": doc["url"],
                "downloaded_at": _now_iso(),
            })

    # Сохраняем метаданные контракта (отдельный файл в подпапке Контракт/)
    contract_meta = {
        "contract_reestr_number": contract_reestr_number,
        "docs_url": page_url,
        "downloaded_at": _now_iso(),
        "last_checked": _now_iso(),
        "files": downloaded,
    }
    contract_meta_path = os.path.join(contract_folder, CONTRACT_META_FILENAME)
    with open(contract_meta_path, "w", encoding="utf-8") as f:
        json.dump(contract_meta, f, ensure_ascii=False, indent=2)

    # Также добавляем ссылку на контракт в основной .tender_meta.json
    # (если он есть в родительской папке) — для отслеживания связи
    parent_meta = _load_meta(folder)
    if parent_meta:
        parent_meta["contract_reestr_number"] = contract_reestr_number
        parent_meta["contract_downloaded_at"] = _now_iso()
        _save_meta(folder, parent_meta)

    return {
        "ok": True,
        "downloaded": len(downloaded),
        "errors": len(errors),
        "files": downloaded,
        "error_list": errors,
        "folder": contract_folder,
        "contract_reestr_number": contract_reestr_number,
    }


# ═══════════════════════════ ОСНОВНЫЕ ФУНКЦИИ ══════════════════════════════

def download_tender(reg_number: str, folder: str) -> dict:
    """
    Скачивает все документы закупки в папку.

    Параметры:
        reg_number : номер извещения (например 0373200082122000012)
        folder     : путь к папке (будет создана если не существует)

    Возвращает словарь с результатами: {ok, files, errors, meta_path}
    """
    os.makedirs(folder, exist_ok=True)

    # Ищем страницу документов
    html, page_url, notice_type = _get_docs_page(reg_number)
    if not html:
        return {"ok": False, "error": f"Страница закупки {reg_number} не найдена на zakupki.gov.ru"}

    # Определяем ФЗ из URL
    fz = "223" if "223" in page_url else "44"

    # Извлекаем список документов
    docs = _extract_docs(html)
    if not docs:
        return {"ok": False, "error": "Документы на странице закупки не обнаружены"}

    # Скачиваем каждый файл — раскладываем по подпапкам
    downloaded = []
    errors = []
    for doc in docs:
        # Определяем подпапку по названию документа
        category = _classify_doc(doc["name"])
        dest_folder = os.path.join(folder, category)
        os.makedirs(dest_folder, exist_ok=True)

        result = _download_file(doc["url"], dest_folder, doc["name"])
        if "error" in result:
            errors.append({"name": doc["name"], "error": result["error"]})
        else:
            downloaded.append({
                "uid": doc["uid"],
                "name": doc["name"],
                "category": category,
                "filename": result["filename"],
                "size_bytes": result["size_bytes"],
                "sha256": result["sha256"],
                "url": doc["url"],
                "downloaded_at": _now_iso(),
            })

    # Сохраняем метаданные (включая notice_type для последующего поиска контракта)
    meta = {
        "reg_number": reg_number,
        "fz": fz,
        "notice_type": notice_type,
        "docs_url": page_url,
        "downloaded_at": _now_iso(),
        "last_checked": _now_iso(),
        "files": downloaded,
    }
    _save_meta(folder, meta)

    # Дополнительно — пытаемся найти подписанный контракт в реестре контрактов
    # Если контракт уже заключён, сразу скачиваем его документы в подпапку Контракт/
    contract_result = None
    contract_reestr = _find_contract_by_notice(reg_number, notice_type)
    if contract_reestr:
        contract_result = download_contract(contract_reestr, folder)

    return {
        "ok": True,
        "downloaded": len(downloaded),
        "errors": len(errors),
        "files": downloaded,
        "error_list": errors,
        "folder": folder,
        "contract": contract_result,  # None если контракт ещё не подписан
    }


def check_updates(folder: str) -> dict:
    """
    Проверяет есть ли изменения на сайте по сравнению с локальной копией.
    Файлы НЕ скачиваются — только проверка.

    Возвращает: {new: [...], removed: [...], unchanged: [...], reg_number, checked_at}
    """
    meta = _load_meta(folder)
    if not meta:
        return {"ok": False, "error": f"Папка {folder} не содержит .tender_meta.json. Сначала выполните download_tender."}

    reg_number = meta["reg_number"]

    # Получаем актуальный список документов с сайта
    html, page_url, _ = _get_docs_page(reg_number)
    if not html:
        return {"ok": False, "error": f"Не удалось подключиться к zakupki.gov.ru для закупки {reg_number}"}

    current_docs = _extract_docs(html)
    current_uids = {d["uid"]: d for d in current_docs}
    local_uids = {f["uid"]: f for f in meta.get("files", [])}

    new_docs = [d for uid, d in current_uids.items() if uid not in local_uids]
    removed_docs = [f for uid, f in local_uids.items() if uid not in current_uids]
    unchanged = [f for uid, f in local_uids.items() if uid in current_uids]

    # Обновляем время последней проверки
    meta["last_checked"] = _now_iso()
    _save_meta(folder, meta)

    return {
        "ok": True,
        "reg_number": reg_number,
        "checked_at": _now_iso(),
        "has_updates": len(new_docs) > 0 or len(removed_docs) > 0,
        "new": new_docs,
        "removed": removed_docs,
        "unchanged_count": len(unchanged),
        "page_url": page_url,
    }


def update_tender(folder: str) -> dict:
    """
    Скачивает новые документы и создаёт лог изменений _changes.md.

    Возвращает: {downloaded: [...], removed: [...], changes_file}
    """
    # Сначала проверяем что изменилось
    check = check_updates(folder)
    if not check.get("ok"):
        return check

    if not check["has_updates"]:
        return {
            "ok": True,
            "message": "Документы актуальны. Новых изменений нет.",
            "reg_number": check["reg_number"],
        }

    meta = _load_meta(folder)
    new_downloaded = []
    errors = []

    # Скачиваем новые файлы — в правильные подпапки
    for doc in check["new"]:
        category = _classify_doc(doc["name"])
        dest_folder = os.path.join(folder, category)
        os.makedirs(dest_folder, exist_ok=True)

        result = _download_file(doc["url"], dest_folder, doc["name"])
        if "error" in result:
            errors.append({"name": doc["name"], "error": result["error"]})
        else:
            entry = {
                "uid": doc["uid"],
                "name": doc["name"],
                "category": category,
                "filename": result["filename"],
                "size_bytes": result["size_bytes"],
                "sha256": result["sha256"],
                "url": doc["url"],
                "downloaded_at": _now_iso(),
            }
            meta["files"].append(entry)
            new_downloaded.append(entry)

    # Помечаем удалённые (не удаляем физически — оставляем пользователю)
    removed_names = [f["filename"] for f in check["removed"]]

    # Обновляем метаданные
    meta["last_checked"] = _now_iso()
    _save_meta(folder, meta)

    # Создаём лог изменений
    changes_file = os.path.join(folder, "_changes.md")
    with open(changes_file, "w", encoding="utf-8") as f:
        f.write(f"# Изменения закупки {check['reg_number']}\n")
        f.write(f"Проверено: {check['checked_at']}\n\n")
        if new_downloaded:
            f.write("## Новые / обновлённые документы\n")
            for d in new_downloaded:
                size_kb = d["size_bytes"] // 1024
                f.write(f"- **{d['filename']}** ({size_kb} КБ) — {d['name']}\n")
        if removed_names:
            f.write("\n## Документы убраны с сайта\n")
            for name in removed_names:
                f.write(f"- ~~{name}~~\n")
        if errors:
            f.write("\n## Ошибки при скачивании\n")
            for e in errors:
                f.write(f"- {e['name']}: {e['error']}\n")

    return {
        "ok": True,
        "reg_number": check["reg_number"],
        "new_downloaded": len(new_downloaded),
        "removed_on_site": len(removed_names),
        "errors": len(errors),
        "files": new_downloaded,
        "changes_file": changes_file,
    }
