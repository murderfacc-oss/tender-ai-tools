"""
Собирает плагин tender-ai.plugin для Claude Code.

Структура плагина:
  .claude-plugin/plugin.json   — манифест
  .mcp.json                    — конфиг MCP-сервера
  README.md                    — описание плагина
  skills/<имя>/                — 4 скилла
  mcp/server.py + ...          — MCP-сервер

Использование:
    python scripts/build_plugin.py
    python scripts/build_plugin.py --output tender-ai.plugin
"""

import argparse
import shutil
import zipfile
from pathlib import Path

ROOT       = Path(__file__).parent.parent
SKILLS_DIR = ROOT / "project" / "skills"
MCP_DIR    = ROOT.parent / "sabytrade-mcp"
BUILD_DIR  = ROOT / "plugin-build" / "tender-ai"

SKILLS = ["scan-zakupki", "zhaloba-fas", "zapros-razyasneniy"]
MCP_FILES = ["launcher.py", "server.py", "zakupki_scraper.py"]


PLUGIN_JSON = """\
{
  "name": "tender-ai",
  "version": "0.4.0",
  "description": "Инструменты для участия в госзакупках по 44-ФЗ на монтаж слаботочки. Сопровождение закупки от подачи до закрытия, жалобы в УФАС, запросы разъяснений + MCP-сервер для скачивания документов с ЕИС.",
  "author": {
    "name": "Artem",
    "email": "murderfacc@gmail.com"
  },
  "homepage": "https://github.com/murderfacc-oss/tender-ai-tools",
  "keywords": ["44-fz", "zakupki", "tender", "fas", "eis", "russia"]
}
"""

MCP_JSON = """\
{
  "mcpServers": {
    "zakupki-eis": {
      "command": "python",
      "args": ["${CLAUDE_PLUGIN_ROOT}/mcp/launcher.py"]
    }
  }
}
"""

README = """\
# Tender AI

Плагин для участия в госзакупках по 44-ФЗ на монтаж слаботочных систем
(видеонаблюдение, СКУД, речевое оповещение, СКС).

## Что внутри

### Скиллы (3 шт.)

| Скилл | Триггер | Что делает |
|---|---|---|
| **scan-zakupki** | «прочитай закупку», «разбери» | Анализ закупки от подачи до закрытия: контакты, ОКПД, эквивалент, СРО/опыт; подбор оборудования; ответы стройконтролю |
| **zhaloba-fas** | «составь жалобу», «жалоба в УФАС», «защита от РНП» | Жалобы в УФАС, защита от РНП, антимонопольные заявления |
| **zapros-razyasneniy** | «запрос разъяснений», «снять коллизию» | Запрос разъяснений + Word-файл для УКЭП |

### MCP-сервер

`zakupki-eis` — скачивает документы закупок напрямую с zakupki.gov.ru.
Бесплатно, без API-ключей. Доступен через `@zakupki-eis` в чате.

## Установка

1. Перетащи `tender-ai.plugin` в Claude Code → нажми **Install**.
2. Перезапусти Claude Code.

При первом запуске MCP-сервер сам поставит свои Python-зависимости через
pip — никаких ручных команд в терминале не требуется.

**Требуется только Python 3.10+ в системе.** Если его нет — поставь с
python.org с галочкой «Add Python to PATH».

## Проверка

1. В новом чате `@zakupki-eis` — должны появиться инструменты.
2. Прикрепи документ закупки и напиши «прочитай закупку».

## Источник данных

zakupki.gov.ru — открытые страницы, без API-ключей.
"""


def build():
    # очищаем build-папку
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True)
    (BUILD_DIR / ".claude-plugin").mkdir()
    (BUILD_DIR / "skills").mkdir()
    (BUILD_DIR / "mcp").mkdir()

    # манифест
    (BUILD_DIR / ".claude-plugin" / "plugin.json").write_text(
        PLUGIN_JSON, encoding="utf-8")
    (BUILD_DIR / ".mcp.json").write_text(MCP_JSON, encoding="utf-8")
    (BUILD_DIR / "README.md").write_text(README, encoding="utf-8")

    # копируем скиллы
    for name in SKILLS:
        src = SKILLS_DIR / name
        if not src.exists():
            print(f"WARN: скилл не найден — {src}")
            continue
        shutil.copytree(src, BUILD_DIR / "skills" / name,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        print(f"  + skills/{name}/")

    # копируем MCP
    for fname in MCP_FILES:
        src = MCP_DIR / fname
        if not src.exists():
            print(f"WARN: файл MCP не найден — {src}")
            continue
        shutil.copy(src, BUILD_DIR / "mcp" / fname)
        print(f"  + mcp/{fname}")


def package(output: Path):
    n = 0
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(BUILD_DIR.rglob("*")):
            if f.is_file() and "__pycache__" not in str(f):
                zf.write(f, f.relative_to(BUILD_DIR))
                n += 1
    size_kb = output.stat().st_size // 1024
    print(f"\nГотово: {output}  ({size_kb} KB, {n} файлов)")


def validate():
    """Проверка структуры плагина."""
    errors = []
    if not (BUILD_DIR / ".claude-plugin" / "plugin.json").exists():
        errors.append("нет .claude-plugin/plugin.json")
    if not (BUILD_DIR / ".mcp.json").exists():
        errors.append("нет .mcp.json")
    skills = list((BUILD_DIR / "skills").iterdir()) if (BUILD_DIR / "skills").exists() else []
    for s in skills:
        if not (s / "SKILL.md").exists():
            errors.append(f"в skills/{s.name}/ нет SKILL.md")
    if not (BUILD_DIR / "mcp" / "server.py").exists():
        errors.append("нет mcp/server.py")
    if not (BUILD_DIR / "mcp" / "launcher.py").exists():
        errors.append("нет mcp/launcher.py")
    if errors:
        print("\nОШИБКИ ВАЛИДАЦИИ:")
        for e in errors:
            print(f"  ! {e}")
        return False
    print(f"  OK валидация: {len(skills)} скиллов, MCP, манифест")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", "-o", type=Path,
                        default=ROOT / "tender-ai.plugin")
    args = parser.parse_args()

    print("Собираю плагин tender-ai...")
    build()
    if not validate():
        return 1
    package(args.output)
    print(f"\nОтправляй партнёру: {args.output.name}")
    print("Партнёр перетаскивает .plugin в Claude Code и нажимает Install.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
