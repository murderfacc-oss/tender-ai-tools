# Перевод MCP zakupki-eis на ГосПлан API v2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Заменить скрап zakupki.gov.ru в MCP-сервере `zakupki-eis` на ГосПлан API v2, сохранив сигнатуры 4 инструментов и раскладку папок.

**Architecture:** Чистая реализация с нуля по `docs/superpowers/specs/2026-05-18-gosplan-api-migration-design.md`. 5 модулей в `mcp/` с одной ответственностью каждый: `gosplan_client.py` (HTTP), `doc_kind_map.py` (код→подпапка), `gosplan_extract.py` (JSON→вложения+сводка), `gosplan_store.py` (файлы/мета/diff), `server.py` (тонкий FastMCP-оркестратор). `zakupki_scraper.py` удаляется.

**Tech Stack:** Python 3.10+, `requests`, `mcp` (FastMCP), `pytest` (dev-only), ГосПлан API v2 (`https://v2.gosplan.info`).

---

## Справка по API (источник: spec + `_gosplan_spike.md`)

- База: `https://v2.gosplan.info`. Только HTTP GET. Заголовок `User-Agent` обязателен.
- До 2026-07-01 без ключа. Forward-compat: если задан env `GOSPLAN_API_KEY` — слать заголовком `X-API-Key` (предполагаемая схема, меняется одной константой когда ключи введут).
- `429` → пауза 60 сек, retry ≤3.
- `GET /fz{44|223}/purchases/{number}` — карточка закупки.
- `GET /fz{44|223}/contracts/{reg_num}` — карточка контракта.
- Вложения 44-ФЗ: `detail["docs"][0]["source"]["attachmentsInfo"]["attachmentInfo"]` — список `{publishedContentId, fileName, fileSize, docKindInfo:{code,name}, url}`. `url` качается без авторизации.
- Вложения 223-ФЗ: `detail["docs"][0]["source"]["attachments"]["document"]` — список `{guid, fileName, description, url}`.
- Коды подпапок: `POD→1_ТЗ`, `CP→2_Контракт`, `MRJ→3_НМЦК`, `CAR→5_Документация`, `AD→7_Прочее`. Незнакомые — эвристика по словам в `name`.

## File Structure

| Файл | Ответственность | Действие |
|---|---|---|
| `mcp/gosplan_client.py` | HTTP-клиент: `get_purchase`, `get_contract`, `download_file`, `GosplanError`/`GosplanNotFound` | Create |
| `mcp/doc_kind_map.py` | `folder_for(code, name) -> str` | Create |
| `mcp/gosplan_extract.py` | `iter_attachments`, `build_print_form_text` | Create |
| `mcp/gosplan_store.py` | `sanitize_filename`, мета I/O, `diff_meta` | Create |
| `mcp/server.py` | FastMCP, 4 инструмента | Rewrite |
| `mcp/zakupki_scraper.py` | — | Delete |
| `mcp/launcher.py` | REQUIRED без bs4/lxml | Modify |
| `mcp/requirements.txt` | без beautifulsoup4/lxml | Modify |
| `mcp/tests/` | юнит-тесты + фикстуры | Create |
| `scripts/build_plugin.py` | флаг `--test` (имя `tender-ai-test`) | Modify |
| `.gitignore` | игнор `tender-ai-test-v*.zip` | Modify |
| `.claude-plugin/plugin.json`, `marketplace.json` | версия 0.7.0 | Modify |
| `mcp/CLAUDE.md`, `PROJECT.md`, `project/CHANGELOG.md`, `TODO.md` | актуализация | Modify |

---

## Task 1: Проверочный спайк контрактов (ручной, сеть) — снять риск №1

Цель: до написания кода убедиться, что `/fz44/contracts/{reg_num}` отдаёт `attachmentsInfo` с реальными документами (КС-2/КС-3/приёмка). Это decision-gate из спека.

**Files:** Create: `mcp/tests/fixtures/.gitkeep`

- [ ] **Step 1: Снять живой ответ контракта**

Взять реальный реестровый номер прошлого контракта Артёма (из истории — `3366503536925000015`, Воронеж).

Run:
```bash
python -c "import requests,json,sys; r=requests.get('https://v2.gosplan.info/fz44/contracts/3366503536925000015', headers={'User-Agent':'tender-ai-tools/0.7'}, timeout=60); open('mcp/tests/fixtures/contract_44.json','w',encoding='utf-8').write(json.dumps(r.json(),ensure_ascii=False,indent=2)); print('HTTP', r.status_code)"
```
Expected: `HTTP 200` и создан файл `mcp/tests/fixtures/contract_44.json`.

- [ ] **Step 2: Проверить наличие вложений**

Run:
```bash
python -c "import json; d=json.load(open('mcp/tests/fixtures/contract_44.json',encoding='utf-8')); src=(d.get('docs') or [{}])[0].get('source',{}); ai=src.get('attachmentsInfo',{}).get('attachmentInfo',[]); print('attachments:', len(ai)); [print(' -', a.get('fileName'), a.get('docKindInfo',{}).get('code')) for a in ai[:10]]"
```
Expected: `attachments: N` где N≥1, в списке видны документы (договор/КС/приёмка).

- [ ] **Step 3: Decision gate**

- Если вложения есть → продолжаем план как есть.
- Если `attachments: 0` или иная структура → **ОСТАНОВИТЬСЯ**, сообщить пользователю фактическую структуру, вернуться к решению по `download_contract` (спек, секция «Риски» — вариант возврата к скрапу для контрактов). Не продолжать вслепую.

- [ ] **Step 4: Commit**

```bash
git add mcp/tests/fixtures/.gitkeep mcp/tests/fixtures/contract_44.json
git commit -m "test(mcp): зафиксирована фикстура контракта 44-ФЗ из ГосПлан API"
```

---

## Task 2: Дев-окружение и фикстуры закупок

**Files:**
- Create: `mcp/tests/__init__.py`, `mcp/tests/conftest.py`, `mcp/requirements-dev.txt`
- Create: `mcp/tests/fixtures/purchase_44.json`, `mcp/tests/fixtures/purchase_223.json`

- [ ] **Step 1: Поставить pytest**

Run:
```bash
python -m pip install pytest
```
Expected: `Successfully installed pytest-...`

- [ ] **Step 2: Создать dev-requirements**

`mcp/requirements-dev.txt`:
```
-r requirements.txt
pytest
```

- [ ] **Step 3: Снять фикстуры реальных закупок**

Run (номера — любые активные 44-ФЗ и 223-ФЗ на монтаж видеонаблюдения; если 223 недоступен — взять из `_gosplan_spike.md` пример `32615999002`):
```bash
python -c "import requests,json; h={'User-Agent':'tender-ai-tools/0.7'}; [open(f'mcp/tests/fixtures/purchase_{fz}.json','w',encoding='utf-8').write(json.dumps(requests.get(f'https://v2.gosplan.info/fz{fz}/purchases/{n}',headers=h,timeout=60).json(),ensure_ascii=False,indent=2)) for fz,n in [(44,'0373200082122000012'),(223,'32615999002')]]; print('ok')"
```
Expected: `ok`, созданы `purchase_44.json` и `purchase_223.json`.

- [ ] **Step 4: Создать пакет тестов**

`mcp/tests/__init__.py`: (пустой файл)

`mcp/tests/conftest.py`:
```python
import json
import sys
from pathlib import Path

import pytest

MCP_DIR = Path(__file__).resolve().parents[1]
if str(MCP_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_DIR))

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def purchase_44() -> dict:
    return _load("purchase_44.json")


@pytest.fixture
def purchase_223() -> dict:
    return _load("purchase_223.json")


@pytest.fixture
def contract_44() -> dict:
    return _load("contract_44.json")
```

- [ ] **Step 5: Проверить, что pytest видит пакет**

Run: `python -m pytest mcp/tests -q`
Expected: `no tests ran` (коллекция без ошибок импорта).

- [ ] **Step 6: Commit**

```bash
git add mcp/tests/__init__.py mcp/tests/conftest.py mcp/requirements-dev.txt mcp/tests/fixtures/purchase_44.json mcp/tests/fixtures/purchase_223.json
git commit -m "test(mcp): dev-окружение pytest + фикстуры закупок 44/223-ФЗ"
```

---

## Task 3: `doc_kind_map.py` — код документа → подпапка

**Files:**
- Create: `mcp/doc_kind_map.py`
- Test: `mcp/tests/test_doc_kind_map.py`

- [ ] **Step 1: Написать падающий тест**

`mcp/tests/test_doc_kind_map.py`:
```python
from doc_kind_map import folder_for


def test_known_codes():
    assert folder_for("POD", "Описание объекта закупки") == "1_ТЗ"
    assert folder_for("CP", "Проект контракта") == "2_Контракт"
    assert folder_for("MRJ", "Обоснование НМЦК") == "3_НМЦК"
    assert folder_for("CAR", "Требование к составу заявки") == "5_Документация"
    assert folder_for("AD", "Дополнительная информация") == "7_Прочее"


def test_heuristic_by_name_when_code_unknown():
    assert folder_for("ZZZ", "Локальный сметный расчёт") == "4_Смета"
    assert folder_for("", "Протокол подведения итогов") == "6_Протоколы"
    assert folder_for(None, "Проект контракта на монтаж") == "2_Контракт"


def test_fallback_to_misc():
    assert folder_for("UNKNOWN", "невнятное название") == "7_Прочее"
```

- [ ] **Step 2: Запустить — убедиться, что падает**

Run: `python -m pytest mcp/tests/test_doc_kind_map.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'doc_kind_map'`

- [ ] **Step 3: Реализовать модуль**

`mcp/doc_kind_map.py`:
```python
"""docKindInfo.code / name -> подпапка раскладки закупки.

Карта кодов выверена по _gosplan_spike.md (раздел 7). Для незнакомых
кодов — эвристика по ключевым словам в человекочитаемом name.
"""
from __future__ import annotations

_CODE_MAP = {
    "POD": "1_ТЗ",
    "CP": "2_Контракт",
    "MRJ": "3_НМЦК",
    "CAR": "5_Документация",
    "AD": "7_Прочее",
}

# (подпапка, кортеж ключевых слов в нижнем регистре) — порядок важен:
# более специфичные раньше общих.
_NAME_RULES = [
    ("4_Смета", ("смет", "лср", "локальный сметный")),
    ("6_Протоколы", ("протокол",)),
    ("3_НМЦК", ("нмцк", "обоснование начальной", "обоснование цены")),
    ("2_Контракт", ("контракт", "договор")),
    ("1_ТЗ", ("техническое задание", "описание объекта", "тз")),
    ("5_Документация", ("требование", "заявк", "документац")),
]

MISC = "7_Прочее"


def folder_for(code: str | None, name: str | None) -> str:
    if code and code in _CODE_MAP:
        return _CODE_MAP[code]
    low = (name or "").lower()
    for folder, keywords in _NAME_RULES:
        if any(kw in low for kw in keywords):
            return folder
    return MISC
```

- [ ] **Step 4: Запустить — убедиться, что проходит**

Run: `python -m pytest mcp/tests/test_doc_kind_map.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add mcp/doc_kind_map.py mcp/tests/test_doc_kind_map.py
git commit -m "feat(mcp): doc_kind_map — код документа ЕИС в подпапку"
```

---

## Task 4: `gosplan_extract.py` — вложения и текстовая сводка

**Files:**
- Create: `mcp/gosplan_extract.py`
- Test: `mcp/tests/test_gosplan_extract.py`

- [ ] **Step 1: Написать падающий тест**

`mcp/tests/test_gosplan_extract.py`:
```python
import pytest

from gosplan_extract import iter_attachments, build_print_form_text


def test_iter_attachments_44(purchase_44):
    atts = list(iter_attachments(purchase_44, fz=44))
    assert atts, "ожидаются вложения у фикстуры 44-ФЗ"
    a = atts[0]
    assert a["url"] and a["file_name"]
    assert "doc_code" in a and "doc_name" in a


def test_iter_attachments_223(purchase_223):
    atts = list(iter_attachments(purchase_223, fz=223))
    assert isinstance(atts, list)  # может быть пусто — это валидно


def test_iter_attachments_empty_is_not_error():
    empty = {"docs": [{"source": {}}]}
    assert list(iter_attachments(empty, fz=44)) == []


def test_iter_attachments_no_source_raises():
    with pytest.raises(KeyError):
        list(iter_attachments({"docs": []}, fz=44))


def test_build_print_form_text(purchase_44):
    text = build_print_form_text(purchase_44, fz=44)
    assert isinstance(text, str) and len(text) > 50
    assert "Закупка" in text or "Объект" in text
```

- [ ] **Step 2: Запустить — убедиться, что падает**

Run: `python -m pytest mcp/tests/test_gosplan_extract.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'gosplan_extract'`

- [ ] **Step 3: Реализовать модуль**

`mcp/gosplan_extract.py`:
```python
"""ГосПлан API v2: извлечение вложений и текстовой сводки из карточки.

ЕДИНСТВЕННОЕ место, где зашиты пути docs[].source.* — при дрейфе схемы
ГосПлан правим только этот модуль (см. spec, раздел «Риски»).
"""
from __future__ import annotations

from typing import Iterator


def _source(detail: dict) -> dict:
    """docs[0].source или KeyError, если структура не распознана."""
    docs = detail.get("docs")
    if not docs:
        raise KeyError("docs[0].source отсутствует — структура ответа не распознана")
    src = docs[0].get("source")
    if src is None:
        raise KeyError("docs[0].source отсутствует — структура ответа не распознана")
    return src


def iter_attachments(detail: dict, fz: int) -> Iterator[dict]:
    """Унифицированный список вложений: {url, file_name, file_size,
    doc_code, doc_name, content_id}. Пустой список — валидно (свежее
    извещение), не ошибка."""
    src = _source(detail)
    if fz == 223:
        docs = (src.get("attachments") or {}).get("document") or []
        for d in docs:
            url = d.get("url")
            if not url:
                continue
            yield {
                "url": url,
                "file_name": d.get("fileName") or d.get("guid") or "file.bin",
                "file_size": d.get("fileSize"),
                "doc_code": None,
                "doc_name": d.get("description") or "",
                "content_id": d.get("guid"),
            }
        return
    ai = (src.get("attachmentsInfo") or {}).get("attachmentInfo") or []
    for a in ai:
        url = a.get("url")
        if not url:
            continue
        dk = a.get("docKindInfo") or {}
        yield {
            "url": url,
            "file_name": a.get("fileName") or a.get("publishedContentId") or "file.bin",
            "file_size": a.get("fileSize"),
            "doc_code": dk.get("code"),
            "doc_name": dk.get("name") or "",
            "content_id": a.get("publishedContentId"),
        }


def _g(d: dict, *path):
    cur = d
    for k in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def build_print_form_text(detail: dict, fz: int) -> str:
    """Человекочитаемая сводка карточки — замена print_form.txt.
    Толерантна к отсутствующим узлам (берём что есть)."""
    src = _source(detail)
    lines: list[str] = []
    num = detail.get("purchase_number") or _g(src, "commonInfo", "purchaseNumber") or "?"
    lines.append(f"Закупка {num} (ФЗ-{fz})")

    obj = (
        _g(src, "commonInfo", "purchaseObjectInfo")
        or detail.get("object_info")
        or ""
    )
    if obj:
        lines.append(f"\nОбъект закупки:\n{obj}")

    ni = src.get("notificationInfo") or {}
    resp = _g(src, "purchaseResponsibleInfo", "responsibleOrgInfo") or {}
    if resp:
        lines.append(
            "\nЗаказчик: "
            + " | ".join(
                str(resp.get(k))
                for k in ("fullName", "inn", "kpp", "postAddress")
                if resp.get(k)
            )
        )

    proc = ni.get("procedureInfo") or {}
    if proc:
        lines.append("\nСроки (procedureInfo):")
        lines.append(_dump_kv(proc))

    cust_req = ni.get("customerRequirementsInfo")
    if cust_req:
        lines.append("\nТребования к участникам (customerRequirementsInfo):")
        lines.append(_dump_kv(cust_req))

    pref = ni.get("preferensesInfo")
    if pref:
        lines.append("\nПреференции / нацрежим (preferensesInfo):")
        lines.append(_dump_kv(pref))

    objects = (
        _g(ni, "purchaseObjectsInfo", "notDrugPurchaseObjectsInfo", "purchaseObject")
        or []
    )
    if objects:
        lines.append(f"\nПозиции ({len(objects)}):")
        for i, po in enumerate(objects, 1):
            name = po.get("name") or po.get("OKPDName") or "—"
            qty = po.get("quantity") or po.get("qty") or ""
            lines.append(f"  {i}. {name} {qty}".rstrip())

    return "\n".join(lines).strip() + "\n"


def _dump_kv(node, indent: int = 2) -> str:
    """Плоский дамп вложенного dict/list в читаемый текст (без JSON-скобок)."""
    out: list[str] = []
    pad = " " * indent

    def walk(n, depth):
        p = " " * (indent * depth)
        if isinstance(n, dict):
            for k, v in n.items():
                if isinstance(v, (dict, list)):
                    out.append(f"{p}{k}:")
                    walk(v, depth + 1)
                else:
                    out.append(f"{p}{k}: {v}")
        elif isinstance(n, list):
            for item in n:
                walk(item, depth)
        else:
            out.append(f"{p}{n}")

    walk(node, 1)
    return "\n".join(out) if out else pad + "—"
```

- [ ] **Step 4: Запустить — убедиться, что проходит**

Run: `python -m pytest mcp/tests/test_gosplan_extract.py -q`
Expected: PASS (5 passed). Если `test_iter_attachments_44` падает на пустых вложениях — фикстура `purchase_44.json` снята со свежей закупки без файлов; пересними Task 2 Step 3 с другим номером (закупка с опубликованными документами).

- [ ] **Step 5: Commit**

```bash
git add mcp/gosplan_extract.py mcp/tests/test_gosplan_extract.py
git commit -m "feat(mcp): gosplan_extract — вложения + текстовая сводка карточки"
```

---

## Task 5: `gosplan_client.py` — HTTP-клиент

**Files:**
- Create: `mcp/gosplan_client.py`
- Test: `mcp/tests/test_gosplan_client.py`

- [ ] **Step 1: Написать падающий тест (с моками, без сети)**

`mcp/tests/test_gosplan_client.py`:
```python
import pytest

import gosplan_client as gc


class FakeResp:
    def __init__(self, status, json_data=None, content=b""):
        self.status_code = status
        self._json = json_data
        self.content = content
        self.headers = {}

    def json(self):
        return self._json


def test_get_purchase_ok(monkeypatch):
    monkeypatch.setattr(gc.requests, "get",
                        lambda *a, **k: FakeResp(200, {"purchase_number": "X"}))
    assert gc.get_purchase(44, "X")["purchase_number"] == "X"


def test_get_purchase_404_raises_notfound(monkeypatch):
    monkeypatch.setattr(gc.requests, "get", lambda *a, **k: FakeResp(404))
    with pytest.raises(gc.GosplanNotFound):
        gc.get_purchase(44, "MISSING")


def test_429_retries_then_raises(monkeypatch):
    calls = {"n": 0}

    def fake_get(*a, **k):
        calls["n"] += 1
        return FakeResp(429)

    monkeypatch.setattr(gc.requests, "get", fake_get)
    monkeypatch.setattr(gc.time, "sleep", lambda s: None)
    with pytest.raises(gc.GosplanError):
        gc.get_purchase(44, "X")
    assert calls["n"] == gc.MAX_RETRIES + 1


def test_api_key_header(monkeypatch):
    seen = {}

    def fake_get(url, headers=None, timeout=None, stream=False):
        seen.update(headers or {})
        return FakeResp(200, {"ok": 1})

    monkeypatch.setenv("GOSPLAN_API_KEY", "secret123")
    monkeypatch.setattr(gc.requests, "get", fake_get)
    gc.get_purchase(44, "X")
    assert seen.get(gc.API_KEY_HEADER) == "secret123"
```

- [ ] **Step 2: Запустить — убедиться, что падает**

Run: `python -m pytest mcp/tests/test_gosplan_client.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'gosplan_client'`

- [ ] **Step 3: Реализовать модуль**

`mcp/gosplan_client.py`:
```python
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
```

- [ ] **Step 4: Запустить — убедиться, что проходит**

Run: `python -m pytest mcp/tests/test_gosplan_client.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add mcp/gosplan_client.py mcp/tests/test_gosplan_client.py
git commit -m "feat(mcp): gosplan_client — HTTP-клиент ГосПлан API v2"
```

---

## Task 6: `gosplan_store.py` — файлы, мета, diff

**Files:**
- Create: `mcp/gosplan_store.py`
- Test: `mcp/tests/test_gosplan_store.py`

- [ ] **Step 1: Написать падающий тест**

`mcp/tests/test_gosplan_store.py`:
```python
from pathlib import Path

from gosplan_store import sanitize_filename, save_meta, load_meta, diff_meta


def test_sanitize_filename():
    assert sanitize_filename('Проект: контракт?.docx') == "Проект_ контракт_.docx"
    long = "x" * 300 + ".pdf"
    out = sanitize_filename(long)
    assert len(out) <= 180 and out.endswith(".pdf")
    assert sanitize_filename("") == "unnamed"


def test_meta_roundtrip(tmp_path: Path):
    meta = {"fz": 44, "number": "N", "updated_at": "2026-05-18",
            "content_ids": ["a", "b"]}
    save_meta(tmp_path, meta)
    assert load_meta(tmp_path) == meta


def test_diff_meta_detects_new_and_removed():
    old = {"content_ids": ["a", "b"], "updated_at": "t1"}
    new_ids = ["b", "c"]
    d = diff_meta(old, new_ids, "t2")
    assert d["new"] == ["c"]
    assert d["removed"] == ["a"]
    assert d["changed"] is True


def test_diff_meta_no_change():
    old = {"content_ids": ["a"], "updated_at": "t1"}
    d = diff_meta(old, ["a"], "t1")
    assert d["changed"] is False
```

- [ ] **Step 2: Запустить — убедиться, что падает**

Run: `python -m pytest mcp/tests/test_gosplan_store.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'gosplan_store'`

- [ ] **Step 3: Реализовать модуль**

`mcp/gosplan_store.py`:
```python
"""Раскладка скачанных файлов, метаданные отслеживания, diff обновлений."""
from __future__ import annotations

import json
import re
from pathlib import Path

_BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_MAX = 180
META_NAME = ".tender_meta.json"


def sanitize_filename(name: str) -> str:
    name = _BAD.sub("_", name or "").strip().strip(".")
    if len(name) > _MAX:
        if "." in name[-12:]:
            stem, ext = name.rsplit(".", 1)
            name = stem[: _MAX - len(ext) - 1] + "." + ext
        else:
            name = name[:_MAX]
    return name or "unnamed"


def save_meta(folder: Path, meta: dict) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / META_NAME).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_meta(folder: Path) -> dict | None:
    p = Path(folder) / META_NAME
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def diff_meta(old: dict, new_content_ids: list[str], new_updated_at: str) -> dict:
    old_ids = set(old.get("content_ids") or [])
    new_ids = set(new_content_ids)
    new = sorted(new_ids - old_ids)
    removed = sorted(old_ids - new_ids)
    changed = bool(new or removed) or old.get("updated_at") != new_updated_at
    return {"new": new, "removed": removed, "changed": changed}
```

- [ ] **Step 4: Запустить — убедиться, что проходит**

Run: `python -m pytest mcp/tests/test_gosplan_store.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add mcp/gosplan_store.py mcp/tests/test_gosplan_store.py
git commit -m "feat(mcp): gosplan_store — раскладка файлов, мета, diff"
```

---

## Task 7: Переписать `server.py` — 4 инструмента на ГосПлан

**Files:**
- Modify (rewrite): `mcp/server.py`
- Test: `mcp/tests/test_server_orchestration.py`

- [ ] **Step 1: Написать падающий тест оркестрации (моки сети)**

`mcp/tests/test_server_orchestration.py`:
```python
from pathlib import Path

import server


def test_download_tender_writes_files_and_meta(tmp_path, purchase_44, monkeypatch):
    monkeypatch.setattr(server.client, "get_purchase",
                        lambda fz, n: purchase_44)
    saved = []
    monkeypatch.setattr(server.client, "download_file",
                        lambda url, dest: (saved.append(Path(dest)), 10)[1])
    out = server.download_tender("0373200082122000012", str(tmp_path))
    assert "Закупка" in out
    assert (tmp_path / ".tender_meta.json").is_file()
    assert (tmp_path / "print_form.txt").is_file()
    assert saved, "ожидались скачанные файлы"


def test_download_tender_404_message(tmp_path, monkeypatch):
    def boom(fz, n):
        raise server.client.GosplanNotFound("нет такой")
    monkeypatch.setattr(server.client, "get_purchase", boom)
    out = server.download_tender("BAD", str(tmp_path))
    assert "не найден" in out.lower()


def test_fz_autodetect_falls_back_to_223(tmp_path, purchase_223, monkeypatch):
    def gp(fz, n):
        if fz == 44:
            raise server.client.GosplanNotFound("нет в 44")
        return purchase_223
    monkeypatch.setattr(server.client, "get_purchase", gp)
    monkeypatch.setattr(server.client, "download_file", lambda url, dest: 1)
    out = server.download_tender("32615999002", str(tmp_path))
    assert "ФЗ-223" in out or "223" in out
```

- [ ] **Step 2: Запустить — убедиться, что падает**

Run: `python -m pytest mcp/tests/test_server_orchestration.py -q`
Expected: FAIL (старый `server.py` импортирует `zakupki_scraper`, нет нужных функций)

- [ ] **Step 3: Переписать server.py**

`mcp/server.py` (полная замена содержимого):
```python
"""MCP-сервер «Закупки ЕИС» — данные через ГосПлан API v2.

Источник: docs/superpowers/specs/2026-05-18-gosplan-api-migration-design.md
Инструменты (сигнатуры не менялись со времён скрап-версии):
  download_tender, download_contract, check_tender_updates, update_tender
"""
import sys
from pathlib import Path

_here = str(Path(__file__).resolve().parent)
if _here not in sys.path:
    sys.path.insert(0, _here)

from mcp.server.fastmcp import FastMCP

import gosplan_client as client
import gosplan_extract as extract
import gosplan_store as store
from doc_kind_map import folder_for

mcp = FastMCP("Закупки ЕИС")

_FZ_ORDER = (44, 223)


def _fetch_purchase(number: str):
    """Пробуем 44-ФЗ, затем 223-ФЗ. Возвращает (fz, detail)."""
    last = None
    for fz in _FZ_ORDER:
        try:
            return fz, client.get_purchase(fz, number)
        except client.GosplanNotFound as e:
            last = e
    raise last


def _fetch_contract(reg_num: str):
    last = None
    for fz in _FZ_ORDER:
        try:
            return fz, client.get_contract(fz, reg_num)
        except client.GosplanNotFound as e:
            last = e
    raise last


def _download_attachments(detail, fz, base: Path, subfolder_fn) -> tuple[list, list]:
    ok, errors = [], []
    for att in extract.iter_attachments(detail, fz):
        sub = subfolder_fn(att)
        fn = store.sanitize_filename(att["file_name"])
        dest = base / sub / fn
        try:
            size = client.download_file(att["url"], dest)
            ok.append({"file": f"{sub}/{fn}", "size": size,
                       "content_id": att["content_id"]})
        except client.GosplanError as e:
            errors.append({"name": fn, "error": str(e)})
    return ok, errors


@mcp.tool()
def download_tender(reg_number: str, folder: str) -> str:
    """Скачать документы извещения закупки через ГосПлан API v2.

    Качает только документы ИЗВЕЩЕНИЯ. Для документов подписанного
    контракта (КС-2/КС-3/приёмка) используй download_contract.

    Параметры:
    - reg_number: номер закупки (44-ФЗ или 223-ФЗ — определяется автоматически)
    - folder: папка назначения (создаётся при необходимости)
    """
    base = Path(folder).resolve()
    base.mkdir(parents=True, exist_ok=True)
    try:
        fz, detail = _fetch_purchase(reg_number)
    except client.GosplanError as e:
        return f"Ошибка: {e}"

    (base / "gosplan_meta.json").write_text(
        __import__("json").dumps(detail, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    try:
        ok, errors = _download_attachments(
            detail, fz, base,
            lambda a: folder_for(a["doc_code"], a["doc_name"]),
        )
    except KeyError as e:
        return (f"Закупка найдена, но структура ответа API не распознана "
                f"({e}). Сырой ответ сохранён в gosplan_meta.json — можно "
                f"разобрать вручную.")

    try:
        pf = extract.build_print_form_text(detail, fz)
        (base / "print_form.txt").write_text(pf, encoding="utf-8")
    except KeyError:
        pf = None

    content_ids = [a["content_id"] for a in ok if a["content_id"]]
    store.save_meta(base, {
        "fz": fz, "number": reg_number,
        "updated_at": detail.get("updated_at") or detail.get("doc_updated_at"),
        "content_ids": content_ids,
    })

    lines = [f"Закупка {reg_number} (ФЗ-{fz}) — скачано в {base}",
             f"Файлов: {len(ok)}"]
    for a in ok:
        lines.append(f"  • {a['file']} ({a['size'] // 1024} КБ)")
    if not ok:
        (base / "_no_attachments.txt").write_text(
            "Извещение есть в ГосПлан, но файлы ещё не опубликованы в ЕИС. "
            "Повторите позже.\n", encoding="utf-8")
        lines.append("  (вложений нет — извещение свежее, повторите позже)")
    if errors:
        lines.append(f"Не скачано: {len(errors)}")
        for e in errors:
            lines.append(f"  ! {e['name']}: {e['error']}")
    if pf:
        lines.append("Сводка: print_form.txt")
    lines.append("Контракт подписан? → download_contract(<рег. № контракта>)")
    return "\n".join(lines)


@mcp.tool()
def download_contract(contract_reestr_number: str, folder: str) -> str:
    """Скачать документы подписанного контракта в подпапку Контракт/.

    Параметры:
    - contract_reestr_number: реестровый номер КОНТРАКТА (не извещения)
    - folder: папка закупки (подпапка Контракт/ создаётся автоматически)
    """
    base = Path(folder).resolve()
    sub = base / "Контракт"
    sub.mkdir(parents=True, exist_ok=True)
    try:
        fz, detail = _fetch_contract(contract_reestr_number)
    except client.GosplanError as e:
        return f"Ошибка: {e}"

    (sub / ".contract_meta.json").write_text(
        __import__("json").dumps(detail, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    try:
        atts = list(extract.iter_attachments(detail, fz))
    except KeyError as e:
        return (f"Контракт найден, но вложения в ответе API отсутствуют "
                f"({e}). Сырой ответ в Контракт/.contract_meta.json — "
                f"проверь структуру, возможно нужен возврат к скрапу для "
                f"контрактов (см. спек, раздел «Риски»).")
    if not atts:
        return ("Контракт найден, но вложений в ответе API нет. Сырой "
                "ответ в Контракт/.contract_meta.json.")

    ok, errors = [], []
    for a in atts:
        fn = store.sanitize_filename(a["file_name"])
        try:
            size = client.download_file(a["url"], sub / fn)
            ok.append((fn, size))
        except client.GosplanError as e:
            errors.append((fn, str(e)))

    lines = [f"Контракт {contract_reestr_number} (ФЗ-{fz}) — {len(ok)} файл(ов) → {sub}"]
    for fn, size in ok:
        lines.append(f"  • {fn} ({size // 1024} КБ)")
    for fn, err in errors:
        lines.append(f"  ! {fn}: {err}")
    return "\n".join(lines)


@mcp.tool()
def check_tender_updates(folder: str) -> str:
    """Проверить, обновились ли документы закупки (без скачивания)."""
    base = Path(folder).resolve()
    meta = store.load_meta(base)
    if not meta:
        return f"Ошибка: нет {store.META_NAME} в {base} — сначала download_tender"
    try:
        detail = client.get_purchase(meta["fz"], meta["number"])
    except client.GosplanError as e:
        return f"Ошибка: {e}"
    try:
        ids = [a["content_id"] for a in extract.iter_attachments(detail, meta["fz"])
               if a["content_id"]]
    except KeyError as e:
        return f"Ошибка: структура ответа не распознана ({e})"
    upd = detail.get("updated_at") or detail.get("doc_updated_at")
    d = store.diff_meta(meta, ids, upd)
    if not d["changed"]:
        return f"Закупка {meta['number']}: без изменений."
    lines = [f"Закупка {meta['number']}: ЕСТЬ ИЗМЕНЕНИЯ"]
    if d["new"]:
        lines.append(f"Новых документов: {len(d['new'])}")
    if d["removed"]:
        lines.append(f"Убрано с сайта: {len(d['removed'])}")
    lines.append(f"Для загрузки: update_tender('{folder}')")
    return "\n".join(lines)


@mcp.tool()
def update_tender(folder: str) -> str:
    """Скачать обновлённые документы и записать _changes.md."""
    base = Path(folder).resolve()
    meta = store.load_meta(base)
    if not meta:
        return f"Ошибка: нет {store.META_NAME} в {base} — сначала download_tender"
    try:
        fz, detail = meta["fz"], client.get_purchase(meta["fz"], meta["number"])
    except client.GosplanError as e:
        return f"Ошибка: {e}"
    try:
        ok, errors = _download_attachments(
            detail, fz, base,
            lambda a: folder_for(a["doc_code"], a["doc_name"]),
        )
    except KeyError as e:
        return f"Ошибка: структура ответа не распознана ({e})"
    ids = [a["content_id"] for a in ok if a["content_id"]]
    upd = detail.get("updated_at") or detail.get("doc_updated_at")
    d = store.diff_meta(meta, ids, upd)
    store.save_meta(base, {**meta, "updated_at": upd, "content_ids": ids})
    (base / "_changes.md").write_text(
        f"# Изменения {meta['number']}\n\n"
        f"Новые: {d['new']}\nУбраны: {d['removed']}\n",
        encoding="utf-8",
    )
    return (f"Закупка {meta['number']} обновлена. Новых: {len(d['new'])}, "
            f"убрано: {len(d['removed'])}. Лог: _changes.md")


if __name__ == "__main__":
    mcp.run(transport="stdio")
```

- [ ] **Step 4: Запустить весь набор тестов**

Run: `python -m pytest mcp/tests -q`
Expected: PASS (все тесты Task 3–7)

- [ ] **Step 5: Commit**

```bash
git add mcp/server.py mcp/tests/test_server_orchestration.py
git commit -m "feat(mcp): server.py на ГосПлан API v2 (4 инструмента, fz-автоопределение)"
```

---

## Task 8: Удалить скрап, почистить зависимости

**Files:**
- Delete: `mcp/zakupki_scraper.py`
- Modify: `mcp/launcher.py:24-29`, `mcp/requirements.txt`

- [ ] **Step 1: Удалить скрапер**

Run: `git rm mcp/zakupki_scraper.py`
Expected: `rm 'mcp/zakupki_scraper.py'`

- [ ] **Step 2: Почистить launcher REQUIRED**

В `mcp/launcher.py` заменить блок:
```python
REQUIRED = [
    ("mcp",          "mcp"),
    ("requests",     "requests"),
    ("bs4",          "beautifulsoup4"),
    ("lxml",         "lxml"),
]
```
на:
```python
REQUIRED = [
    ("mcp",      "mcp"),
    ("requests", "requests"),
]
```

- [ ] **Step 3: Почистить requirements.txt**

`mcp/requirements.txt` (полная замена):
```
mcp
requests
```

- [ ] **Step 4: Проверить, что сервер импортируется без bs4/lxml**

Run: `python -c "import sys; sys.path.insert(0,'mcp'); import server; print('import OK')"`
Expected: `import OK`

- [ ] **Step 5: Прогнать все тесты**

Run: `python -m pytest mcp/tests -q`
Expected: PASS (без изменений в количестве)

- [ ] **Step 6: Commit**

```bash
git add mcp/launcher.py mcp/requirements.txt
git commit -m "chore(mcp): удалён скрапер, убраны beautifulsoup4/lxml"
```

---

## Task 9: Тестовая сборка плагина `tender-ai-test`

Цель: пользователь ставит тестовую сборку рядом с рабочим плагином, не ломая его. Два плагина с одинаковым `name` конфликтуют → флаг `--test` собирает zip с именем `tender-ai-test`.

**Files:**
- Modify: `scripts/build_plugin.py`
- Modify: `.gitignore`
- Test: `scripts/test_build_plugin.py`

- [ ] **Step 1: Написать падающий тест**

`scripts/test_build_plugin.py`:
```python
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_test_build_renames_plugin(tmp_path):
    out = tmp_path / "t.zip"
    subprocess.check_call([sys.executable, "scripts/build_plugin.py",
                           "--test", "-o", str(out)], cwd=ROOT)
    with zipfile.ZipFile(out) as zf:
        pj = json.loads(zf.read(".claude-plugin/plugin.json"))
    assert pj["name"] == "tender-ai-test"
```

- [ ] **Step 2: Запустить — убедиться, что падает**

Run: `python -m pytest scripts/test_build_plugin.py -q`
Expected: FAIL — `build_plugin.py: error: unrecognized arguments: --test`

- [ ] **Step 3: Добавить флаг `--test` в build_plugin.py**

В `scripts/build_plugin.py`, в `main()`, после строки с `--output`:
```python
    parser.add_argument("--test", action="store_true",
                        help="тестовая сборка: name=tender-ai-test (ставится "
                             "рядом с рабочим плагином, не конфликтует)")
    args = parser.parse_args()

    version = _read_version()
    if args.test:
        output = args.output or (ROOT / f"tender-ai-test-v{version}.zip")
    else:
        output = args.output or (ROOT / f"tender-ai-v{version}.zip")
```
И заменить запись `plugin.json`/`marketplace.json` в цикле на патч имени при `--test`. После `with zipfile.ZipFile(...)` строку записи `INCLUDE_FILES` заменить на:
```python
        for rel in INCLUDE_FILES:
            src = ROOT / rel
            if not src.is_file():
                print(f"  ! пропущен (нет файла): {rel}")
                continue
            if args.test and rel == ".claude-plugin/plugin.json":
                data = json.loads(src.read_text(encoding="utf-8"))
                data["name"] = "tender-ai-test"
                data["description"] = "[ТЕСТ] " + data.get("description", "")
                zf.writestr(rel, json.dumps(data, ensure_ascii=False, indent=2))
                added += 1
            elif args.test and rel == ".claude-plugin/marketplace.json":
                data = json.loads(src.read_text(encoding="utf-8"))
                for p in data.get("plugins", []):
                    p["name"] = "tender-ai-test"
                zf.writestr(rel, json.dumps(data, ensure_ascii=False, indent=2))
                added += 1
            else:
                zf.write(src, rel)
                added += 1
```

- [ ] **Step 4: Запустить — убедиться, что проходит**

Run: `python -m pytest scripts/test_build_plugin.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: Игнор тестового zip**

В `.gitignore` после строки `tender-ai-v*.zip` добавить:
```
tender-ai-test-v*.zip
```

- [ ] **Step 6: Проверить обычную сборку не сломана**

Run: `python scripts/build_plugin.py -o /tmp/regular.zip && python -c "import json,zipfile; print(json.loads(zipfile.ZipFile('/tmp/regular.zip').read('.claude-plugin/plugin.json'))['name'])"`
Expected: `tender-ai` (обычная сборка не переименована)

- [ ] **Step 7: Commit**

```bash
git add scripts/build_plugin.py scripts/test_build_plugin.py .gitignore
git commit -m "feat(build): флаг --test — сборка tender-ai-test рядом с рабочим"
```

---

## Task 10: Версия и документация

**Files:**
- Modify: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`
- Modify: `mcp/CLAUDE.md`, `project/PROJECT.md`, `project/CHANGELOG.md`, `TODO.md`

- [ ] **Step 1: Bump версии 0.6.0 → 0.7.0**

В `.claude-plugin/plugin.json`: `"version": "0.6.0"` → `"version": "0.7.0"`.
В `.claude-plugin/marketplace.json`: оба `"version": "0.6.0"` → `"version": "0.7.0"`.

- [ ] **Step 2: Обновить mcp/CLAUDE.md**

В `mcp/CLAUDE.md` заменить описание стека и источника: убрать `beautifulsoup4`/`lxml`/«прямой скрап», написать что источник данных — ГосПлан API v2 (`https://v2.gosplan.info`), скрап удалён, см. спек `docs/superpowers/specs/2026-05-18-gosplan-api-migration-design.md`. Обновить таблицу инструментов: `download_tender` качает только извещение; контракт — через `download_contract`.

- [ ] **Step 3: Обновить проектные доки**

`project/CHANGELOG.md` — добавить секцию `## 2026-05-18` запись: «MCP zakupki-eis переведён со скрапа zakupki.gov.ru на ГосПлан API v2 (v0.7.0). Скрапер удалён, зависимости bs4/lxml убраны. download_tender теперь качает только извещение, контракт — отдельной командой».
`project/PROJECT.md` — в разделе про MCP отметить смену источника на ГосПлан API v2.
`TODO.md` — в «Открытые задачи» добавить пункт: «после боевой обкатки v0.7.0 — решить, нужен ли поиск закупок через ГосПлан API как новый MCP-инструмент».

- [ ] **Step 4: Финальный прогон тестов + сборки**

Run: `python -m pytest mcp/tests scripts/test_build_plugin.py -q && python scripts/build_plugin.py --test -o /tmp/test-build.zip`
Expected: все тесты PASS; собран `/tmp/test-build.zip`.

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json mcp/CLAUDE.md project/PROJECT.md project/CHANGELOG.md TODO.md
git commit -m "docs: ГосПлан API v2 миграция — версия 0.7.0, актуализация доков"
```

---

## Task 11: Боевая проверка (ручная, сеть) перед PR

**Files:** нет (ручная проверка)

- [ ] **Step 1: Прогнать download_tender на реальной закупке**

Run:
```bash
python -c "import sys; sys.path.insert(0,'mcp'); import server; print(server.download_tender('0373200082122000012','/tmp/tt'))"
```
Expected: сводка со списком файлов; `/tmp/tt/print_form.txt` и `/tmp/tt/.tender_meta.json` существуют, файлы разложены по подпапкам.

- [ ] **Step 2: Прогнать download_contract на реальном контракте**

Run:
```bash
python -c "import sys; sys.path.insert(0,'mcp'); import server; print(server.download_contract('3366503536925000015','/tmp/tt'))"
```
Expected: файлы контракта в `/tmp/tt/Контракт/` (подтверждает гипотезу Task 1).

- [ ] **Step 3: Прогнать check/update**

Run:
```bash
python -c "import sys; sys.path.insert(0,'mcp'); import server; print(server.check_tender_updates('/tmp/tt'))"
```
Expected: «без изменений» (только что скачали).

- [ ] **Step 4: Решение о готовности**

Если все 3 шага прошли — план выполнен, можно открывать PR. Если `download_contract` не отдал файлы — зафиксировать факт, не мержить, эскалировать пользователю (риск №1 материализовался).

---

## Self-Review

**1. Покрытие спека:**
- Удаление скрапа → Task 8 ✓
- 5 модулей с одной ответственностью → Tasks 3–7 ✓
- Сигнатуры 4 инструментов не меняются → Task 7 (download_tender/download_contract/check_tender_updates/update_tender) ✓
- fz-автоопределение (44→223) → Task 7 `_fetch_purchase`/`_fetch_contract` ✓
- print_form.txt из JSON → Task 4 `build_print_form_text`, Task 7 запись ✓
- .tender_meta.json + diff → Task 6, Task 7 ✓
- Ошибки 404/429/таймаут/пустые/битый JSON → Task 5 (`GosplanNotFound`, retry), Task 7 (KeyError-ветки, `_no_attachments.txt`) ✓
- GOSPLAN_API_KEY forward-compat → Task 5 `_headers`/`API_KEY_HEADER` ✓
- Риск контрактов снят первым шагом → Task 1 decision-gate ✓
- Тесты на фикстурах → Tasks 2–7 ✓
- launcher/requirements чистка → Task 8 ✓
- build --test (tender-ai-test) → Task 9 ✓
- Версия 0.7.0 + доки → Task 10 ✓
- Вне scope (поиск, миграция папок) — не включено, отмечено в TODO ✓

**2. Плейсхолдеры:** код приведён полностью в каждом шаге; «<рег. № контракта>» в docstring инструмента — рантайм-значение для пользователя, не пробел плана. Замечаний нет.

**3. Согласованность типов:** `iter_attachments(detail, fz)` отдаёт `{url, file_name, file_size, doc_code, doc_name, content_id}` — те же ключи используются в `server._download_attachments`, `download_contract`, `check/update`. `folder_for(code, name)` — сигнатура едина в Task 3 и вызовах Task 7. `GosplanNotFound`/`GosplanError` определены в Task 5, используются в Task 7. `save_meta/load_meta/diff_meta/META_NAME` — Task 6 ↔ Task 7. `client.get_purchase/get_contract/download_file` — Task 5 ↔ Task 7. Расхождений нет.
