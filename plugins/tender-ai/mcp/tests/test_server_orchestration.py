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
        raise server.client.GosplanNotFound(
            "не найдено в ГосПлан API: /fz44/purchases/BAD")
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


def test_download_contract_pulls_doc_and_closing(
    tmp_path, contract_44, contract_44_procedures, monkeypatch
):
    monkeypatch.setattr(server.client, "get_contract",
                        lambda fz, n: contract_44)
    monkeypatch.setattr(server.client, "get_contract_procedures",
                        lambda fz, n: contract_44_procedures)
    pulled = []
    monkeypatch.setattr(server.client, "download_file",
                        lambda url, dest: (pulled.append(url), 5)[1])
    out = server.download_contract("3366503536925000015", str(tmp_path))
    assert (tmp_path / "Контракт" / ".contract_meta.json").is_file()
    assert pulled, "ожидались скачанные файлы контракта"
    assert "Контракт" in out


def test_download_contract_no_procedures_marks_missing(tmp_path, monkeypatch):
    detail = {"docs": [{"source": {"scanDocuments": {"CPEPAttachment": [
        {"fileName": "Контракт.doc", "url": "http://x/1", "publishedContentId": "c1"}
    ]}}}]}
    monkeypatch.setattr(server.client, "get_contract", lambda fz, n: detail)
    monkeypatch.setattr(server.client, "get_contract_procedures",
                        lambda fz, n: [])
    monkeypatch.setattr(server.client, "download_file", lambda url, dest: 3)
    out = server.download_contract("REG", str(tmp_path))
    assert "Закрывающих документов" in out
