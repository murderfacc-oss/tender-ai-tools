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


def _diagnostic_banner() -> None:
    """Одна строка в stderr при старте — попадает в логи Claude Desktop.

    Если MCP «не цепляется», именно отсутствие этой строки в логах
    показывает, что launcher.py вообще не запустился (типично для
    Windows: command "python" указывает на Microsoft Store stub либо
    Python вообще не в PATH). На macOS — что нужен "python3".
    """
    exe = sys.executable or "?"
    is_store_stub = (
        sys.platform == "win32"
        and "WindowsApps" in exe
        and "python" in exe.lower()
    )
    marker = " [Microsoft Store stub — поставь Python с python.org]" if is_store_stub else ""
    print(
        f"[zakupki-eis launcher] python={exe} platform={sys.platform}{marker}",
        file=sys.stderr,
        flush=True,
    )
    if is_store_stub:
        # Stub завершится сам, лучше упасть с понятной ошибкой раньше.
        print(
            "[zakupki-eis launcher] python из WindowsApps — это заглушка, "
            "которая ничего не запускает. Установи Python 3.10+ с python.org "
            "(галочка «Add Python to PATH») и переустанови плагин.",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(2)


def main() -> None:
    _force_utf8_streams()
    _diagnostic_banner()

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

    # Запускаем server.py отдельным процессом, а не через exec() в текущем.
    # Это полностью изолирует sys.path / globals / state launcher'а от
    # сервера. stdin/stdout/stderr наследуются от нас — MCP-протокол
    # (JSON-RPC по stdio) идёт напрямую между Claude и server.py без
    # промежуточных буферов.
    #
    # Embedded Python: чистый sys.path в новом процессе тоже не содержит
    # script-dir, но server.py сам добавляет свою директорию в sys.path
    # в первых строках — он самодостаточен.
    try:
        proc = subprocess.run([sys.executable, str(server)])
    except FileNotFoundError as e:
        print(f"[launcher] Не смог запустить {sys.executable}: {e}",
              file=sys.stderr, flush=True)
        sys.exit(127)
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
