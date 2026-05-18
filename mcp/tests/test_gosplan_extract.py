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


def test_iter_contract_attachments(contract_44, contract_44_procedures):
    from gosplan_extract import iter_contract_attachments

    atts = list(iter_contract_attachments(contract_44, contract_44_procedures))
    assert atts, "ожидаются вложения контракта (договор + закрывающие)"
    groups = {a["group"] for a in atts}
    # сам договор всегда есть; закрывающие — на тестовом контракте есть
    assert "contract" in groups
    a = atts[0]
    assert a["url"] and a["file_name"]


def test_iter_contract_attachments_normalizes_single_obj():
    from gosplan_extract import iter_contract_attachments

    detail = {"docs": [{"source": {"scanDocuments": {"CPEPAttachment": [
        {"fileName": "Контракт.doc", "url": "http://x/1", "publishedContentId": "c1"}
    ]}}}]}
    procedures = [{"source": {"paymentDocuments": {"attachment": {
        "fileName": "Платёжка.pdf", "url": "http://x/2", "publishedContentId": "p1"}}}}]
    atts = list(iter_contract_attachments(detail, procedures))
    names = {a["file_name"] for a in atts}
    assert names == {"Контракт.doc", "Платёжка.pdf"}


def test_iter_contract_attachments_empty_procedures_ok():
    from gosplan_extract import iter_contract_attachments

    detail = {"docs": [{"source": {"scanDocuments": {"CPEPAttachment": [
        {"fileName": "Контракт.doc", "url": "http://x/1", "publishedContentId": "c1"}
    ]}}}]}
    atts = list(iter_contract_attachments(detail, []))
    assert [a["file_name"] for a in atts] == ["Контракт.doc"]


# --- Регрессия: EIS схлопывает одноэлементные массивы в одиночный объект ---

def test_build_print_form_text_single_position_real(purchase_44_single):
    """Реальная закупка с 1 позицией: purchaseObject — dict, не список.
    Раньше падало 'str' object has no attribute 'get' (gosplan_extract:117)."""
    text = build_print_form_text(purchase_44_single, fz=44)
    assert isinstance(text, str) and len(text) > 50
    assert "Позиции (1)" in text


def test_iter_attachments_single_attachment_collapse():
    """Одно вложение → attachmentInfo приходит dict, не списком."""
    detail = {"docs": [{"source": {"attachmentsInfo": {"attachmentInfo": {
        "publishedContentId": "P1", "fileName": "ТЗ.docx",
        "url": "http://x/1", "docKindInfo": {"code": "POD", "name": "ТЗ"},
    }}}}]}
    atts = list(iter_attachments(detail, fz=44))
    assert len(atts) == 1
    assert atts[0]["file_name"] == "ТЗ.docx" and atts[0]["url"] == "http://x/1"


def test_iter_attachments_223_single_document_collapse():
    detail = {"docs": [{"source": {"attachments": {"document": {
        "guid": "G1", "fileName": "Извещение.pdf", "url": "http://x/2",
    }}}}]}
    atts = list(iter_attachments(detail, fz=223))
    assert [a["file_name"] for a in atts] == ["Извещение.pdf"]


def test_build_print_form_text_single_position_synthetic():
    detail = {"docs": [{"source": {"notificationInfo": {
        "purchaseObjectsInfo": {"notDrugPurchaseObjectsInfo": {
            "purchaseObject": {"name": "Камера", "quantity": "5"}}}}}}]}
    text = build_print_form_text(detail, fz=44)
    assert "Позиции (1)" in text and "Камера" in text
