"""
Собирает zip-плагин tender-ai для распространения.

Получившийся файл `tender-ai-v<версия>.zip` партнёр устанавливает через
Claude Desktop: **Customize → Personal plugins → + → Create plugin →
Upload plugin** и выбирает этот zip. Альтернатива — добавить маркетплейс
по GitHub-URL (см. `.claude-plugin/marketplace.json`).

Структура zip совпадает со структурой репо — один источник правды,
никакого «build directory» с переименованиями.

Использование:
    python scripts/build_plugin.py
    python scripts/build_plugin.py --output tender-ai-v0.5.0.zip
"""

import argparse
import fnmatch
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent.parent

# Что попадает в плагин
INCLUDE_FILES = [
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    ".mcp.json",
    "README.md",
]
INCLUDE_DIRS = [
    "skills",
    "mcp",
]

# Что выкидываем из директорий
EXCLUDE = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".DS_Store",
    "Thumbs.db",
]


def _excluded(rel: Path) -> bool:
    for part in rel.parts:
        for pattern in EXCLUDE:
            if fnmatch.fnmatch(part, pattern):
                return True
    return False


def _read_version() -> str:
    manifest = ROOT / ".claude-plugin" / "plugin.json"
    return json.loads(manifest.read_text(encoding="utf-8"))["version"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", "-o", type=Path, default=None,
                        help="имя выходного zip (по умолчанию tender-ai-v<версия>.zip)")
    args = parser.parse_args()

    version = _read_version()
    output = args.output or (ROOT / f"tender-ai-v{version}.zip")

    added = 0
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in INCLUDE_FILES:
            src = ROOT / rel
            if src.is_file():
                zf.write(src, rel)
                added += 1
            else:
                print(f"  ! пропущен (нет файла): {rel}")

        for d in INCLUDE_DIRS:
            base = ROOT / d
            if not base.is_dir():
                print(f"  ! пропущена (нет директории): {d}")
                continue
            for f in sorted(base.rglob("*")):
                if not f.is_file():
                    continue
                rel = f.relative_to(ROOT)
                if _excluded(rel):
                    continue
                zf.write(f, str(rel))
                added += 1

    size_kb = output.stat().st_size // 1024
    print(f"\nГотово: {output.name}  ({size_kb} KB, {added} файлов)")
    print(f"Партнёр: Customize → Personal plugins → + → Create plugin → Upload plugin → {output.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
