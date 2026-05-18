"""MCP-сервер «Закупки ЕИС» — данные через ГосПлан API v2.

Источник: docs/superpowers/specs/2026-05-18-gosplan-api-migration-design.md
Инструменты (сигнатуры не менялись со времён скрап-версии):
  download_tender, download_contract, check_tender_updates, update_tender
"""
import json
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
        json.dumps(detail, ensure_ascii=False, indent=2),
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

    # procedures: 404 = нет этапов исполнения, не ошибка (вернёт []).
    # fz уже определён в _fetch_contract — не дёргаем чужой ФЗ зря.
    try:
        procedures = client.get_contract_procedures(fz, contract_reestr_number)
    except client.GosplanError:
        procedures = []

    (sub / ".contract_meta.json").write_text(
        json.dumps({"contract": detail, "procedures": procedures},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    atts = list(extract.iter_contract_attachments(detail, procedures))
    if not atts:
        return ("Контракт найден, но вложений в ответе API нет. Сырой "
                "ответ в Контракт/.contract_meta.json.")

    ok, errors = [], []
    for a in atts:
        fn = store.sanitize_filename(a["file_name"])
        try:
            size = client.download_file(a["url"], sub / fn)
            ok.append((fn, size, a["group"]))
        except client.GosplanError as e:
            errors.append((fn, str(e)))

    has_closing = any(g != "contract" for _, _, g in ok)
    lines = [f"Контракт {contract_reestr_number} (ФЗ-{fz}) — {len(ok)} файл(ов) → {sub}"]
    for fn, size, g in ok:
        lines.append(f"  • [{g}] {fn} ({size // 1024} КБ)")
    for fn, err in errors:
        lines.append(f"  ! {fn}: {err}")
    if not has_closing:
        lines.append("ℹ Закрывающих документов (КС-2/КС-3/приёмка) в API "
                      "пока нет — контракт ещё в исполнении или акты не "
                      "опубликованы.")
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
