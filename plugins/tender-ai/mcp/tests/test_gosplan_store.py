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
