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
