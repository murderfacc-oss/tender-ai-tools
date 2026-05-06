"""
Wrapper для MCP-сервера: при первом запуске проверяет зависимости и при
необходимости ставит их через pip. Затем запускает server.py.

Этот файл указан в .mcp.json плагина — Claude Code запускает его, а он уже
сам разбирается с окружением. Партнёру не нужно ничего делать в терминале.

Особенности:
- stdout/stderr принудительно в UTF-8 — важно для путей с кириллицей и
  служебных сообщений на русском (Windows по умолчанию cp1251).
- Все пути нормализуются и резолвятся до абсолютных через Path.resolve() —
  устойчиво к запуску из любой рабочей директории, включая пути с
  пробелами и не-ASCII символами (кириллица, диакритика).
- subprocess запускается с явным encoding='utf-8' — pip может писать
  не-ASCII в вывод и без encoding падает на Windows.
"""

import io
import os
import subprocess
import sys
from pathlib import Path

REQUIRED = [
    ("mcp",          "mcp"),
    ("requests",     "requests"),
    ("bs4",          "beautifulsoup4"),
    ("lxml",         "lxml"),
]


def _force_utf8_streams() -> None:
    """Перевести stdout/stderr в UTF-8 до первого print().

    На Windows консоль по умолчанию cp1251 — любая кириллица в служебных
    сообщениях (или в путях, которые pip печатает) валит print с
    UnicodeEncodeError. Делаем это в самом начале main().
    """
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        enc = (getattr(stream, "encoding", "") or "").lower().replace("-", "")
        if enc == "utf8":
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # py3.7+
        except (AttributeError, ValueError):
            buf = getattr(stream, "buffer", None)
            if buf is not None:
                setattr(
                    sys, stream_name,
                    io.TextIOWrapper(buf, encoding="utf-8",
                                     errors="replace", line_buffering=True),
                )


def ensure_dependencies() -> None:
    """Проверить, что все нужные пакеты импортируются. Если нет — поставить."""
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
        flush=True,
    )

    base_cmd = [
        sys.executable, "-m", "pip", "install",
        "--quiet", "--disable-pip-version-check",
    ]

    def _run(cmd: list) -> int:
        # encoding='utf-8' обязателен — без него pip падает на Windows,
        # если в его выводе встречается не-ASCII (имена путей и т.п.).
        return subprocess.call(
            cmd,
            stdout=sys.stderr,         # MCP читает наш stdout — не засоряем
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
        )

    rc = _run(base_cmd + missing)
    if rc != 0:
        # Возможно нет прав на system-wide install — пробуем --user.
        print("[launcher] pip упал, пробую --user", file=sys.stderr, flush=True)
        rc = _run(base_cmd + ["--user"] + missing)
        if rc != 0:
            print(
                f"[launcher] pip install завершился с ошибкой ({rc}). "
                "Проверь интернет/прокси и права на запись в site-packages.",
                file=sys.stderr,
                flush=True,
            )
            sys.exit(rc)

    print("[launcher] Зависимости установлены.", file=sys.stderr, flush=True)


def main() -> None:
    _force_utf8_streams()

    # На Windows: чтобы дочерние процессы (pip и его подпроцессы)
    # тоже работали в UTF-8 при чтении/печати путей.
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")

    ensure_dependencies()

    # Path(__file__).resolve() — устойчиво к относительным путям,
    # симлинкам, запуску из любой рабочей директории, путям с пробелами
    # и кириллицей.
    here = Path(__file__).resolve().parent
    server = here / "server.py"

    if not server.is_file():
        print(f"[launcher] Не нашёл server.py рядом: {server}",
              file=sys.stderr, flush=True)
        sys.exit(1)

    source = server.read_text(encoding="utf-8")
    code = compile(source, str(server), "exec")
    globs = {"__name__": "__main__", "__file__": str(server)}
    exec(code, globs)


if __name__ == "__main__":
    main()
