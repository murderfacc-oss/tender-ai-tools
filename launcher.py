"""
Wrapper для MCP-сервера: при первом запуске проверяет зависимости и при
необходимости ставит их через pip. Затем запускает server.py.

Этот файл указан в .mcp.json плагина — Claude Code запускает его, а он уже
сам разбирается с окружением. Партнёру не нужно ничего делать в терминале.
"""

import subprocess
import sys
from pathlib import Path

REQUIRED = [
    ("mcp",          "mcp"),
    ("requests",     "requests"),
    ("bs4",          "beautifulsoup4"),
    ("lxml",         "lxml"),
    ("docx",         "python-docx"),
]


def ensure_dependencies():
    """Проверяет, что все нужные пакеты импортируются. Если нет — ставит."""
    missing = []
    for module, package in REQUIRED:
        try:
            __import__(module)
        except ImportError:
            missing.append(package)

    if not missing:
        return

    # пишем в stderr — stdout зарезервирован под MCP-протокол
    print(
        f"[launcher] Устанавливаю недостающие пакеты: {', '.join(missing)}",
        file=sys.stderr,
    )
    cmd = [sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check", *missing]
    try:
        subprocess.check_call(cmd, stdout=sys.stderr)
    except subprocess.CalledProcessError as exc:
        # Если упало (например, нет прав) — пробуем с --user
        print("[launcher] pip упал, пробую --user", file=sys.stderr)
        cmd_user = cmd[:4] + ["--user"] + cmd[4:]
        subprocess.check_call(cmd_user, stdout=sys.stderr)

    print("[launcher] Зависимости установлены.", file=sys.stderr)


def main():
    ensure_dependencies()

    # запускаем настоящий сервер в этом же процессе
    here = Path(__file__).parent
    server = here / "server.py"

    # exec'аем код server.py в том же интерпретаторе
    code = compile(server.read_text(encoding="utf-8"), str(server), "exec")
    globs = {"__name__": "__main__", "__file__": str(server)}
    exec(code, globs)


if __name__ == "__main__":
    main()
