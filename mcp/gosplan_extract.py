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


def _as_list(node):
    """attachment бывает объектом ИЛИ массивом — нормализуем к списку."""
    if node is None:
        return []
    return node if isinstance(node, list) else [node]


def _att(a: dict, group: str) -> dict:
    return {
        "url": a.get("url"),
        "file_name": a.get("fileName") or a.get("publishedContentId") or "file.bin",
        "content_id": a.get("publishedContentId"),
        "group": group,
    }


# Пути к закрывающим документам внутри элемента procedures[i].source.
# Установлены спайком 2026-05-18 (см. спек). Единственное место привязки.
_PROC_PATHS = [
    (("executions", "execution", "docAcceptance", "receiptDocuments", "attachment"), "receipt"),
    (("paymentDocuments", "attachment"), "payment"),
    (("examinationResultsDocuments", "attachment"), "examination"),
]


def iter_contract_attachments(contract_detail: dict, procedures: list):
    """Все вложения контракта: сам договор (docs[0].source.scanDocuments
    .CPEPAttachment[]) + закрывающие из массива procedures. Схема контрактов
    ОТЛИЧАЕТСЯ от закупок (не attachmentsInfo). Пустой procedures — валидно."""
    docs = contract_detail.get("docs") or []
    src = docs[0].get("source", {}) if docs else {}
    for a in _as_list((src.get("scanDocuments") or {}).get("CPEPAttachment")):
        if a.get("url"):
            yield _att(a, "contract")

    for proc in procedures or []:
        psrc = proc.get("source", {}) or {}
        for path, group in _PROC_PATHS:
            cur = psrc
            for k in path:
                cur = cur.get(k) if isinstance(cur, dict) else None
            for a in _as_list(cur):
                if isinstance(a, dict) and a.get("url"):
                    yield _att(a, group)
