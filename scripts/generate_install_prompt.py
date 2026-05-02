"""
Генерирует файл INSTALL_PROMPT.md — короткая инструкция + готовый
промт для Claude Code, который сам устанавливает ВСЁ окружение.

Использование:
    python scripts/generate_install_prompt.py
    python scripts/generate_install_prompt.py --output INSTALL_PROMPT.md
"""

import argparse
from pathlib import Path


PROMPT = r"""Установи мне «Tender AI Tools» — набор инструментов для участия
в госзакупках по 44-ФЗ.

Текущая рабочая папка должна быть корнем распакованного архива.
В ней должны быть:
- `skills/` — 4 zip-файла со скиллами
- `mcp/` — Python-сервер MCP (server.py, zakupki_scraper.py, requirements.txt)

Если этих папок нет — останови установку и попроси меня проверить, что
архив распакован правильно и что ты открыт именно в папке архива.

Дальше выполни шаги по очереди. После каждого шага кратко отчитывайся
что сделал, и переходи к следующему. Работай на русском.

**Шаг 1. Проверить и при необходимости установить Python**

Запусти `python --version`. Если выводит версию ≥ 3.10 — переходи к шагу 2.

Если Python не установлен или версия старая:
- На Windows используй winget: `winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements`
- На macOS: `brew install python@3.12`
- На Linux: подскажи команду под дистрибутив.

После установки попроси меня закрыть и открыть терминал заново (чтобы
обновился PATH), затем продолжи.

**Шаг 2. Установить Python-зависимости**

В корне архива выполни:
```
pip install -r mcp/requirements.txt
pip install python-docx
```

Если pip не находится — попробуй `python -m pip install ...`. Если ошибка
«access denied» — добавь флаг `--user`.

**Шаг 3. Зарегистрировать MCP-сервер в Claude Code**

MCP скачивает документы напрямую с zakupki.gov.ru, никаких ключей и
регистраций не нужно.

Получи абсолютный путь к `mcp/server.py` (используй текущую папку).
Выполни:
```
claude mcp add --scope user zakupki-eis python <АБСОЛЮТНЫЙ_ПУТЬ_К>/mcp/server.py
```

Если команда `claude mcp add` недоступна — добавь сервер вручную, отредактировав
файл `~/.claude.json` (на Windows: `C:\Users\<имя>\.claude.json`):
в секцию `mcpServers` добавь:
```
"zakupki-eis": {
  "command": "python",
  "args": ["<АБСОЛЮТНЫЙ_ПУТЬ>/mcp/server.py"]
}
```

**Шаг 4. Проверить что MCP-сервер запускается**

Запусти `python mcp/server.py` в фоне на 1–2 секунды и останови. Если
есть ошибки импорта — покажи их и предложи решение (обычно недостающий
пакет, который надо доустановить через pip).

**Шаг 5. Дать инструкцию по загрузке скиллов в Cowork**

Я не могу через тебя загрузить скиллы в Cowork — это веб-интерфейс.
Напиши мне понятный список:

> Открой Cowork в браузере (URL уточни у партнёра).
> Перейди в раздел **Skills** → нажми **Upload**.
> Загрузи каждый из 4 zip-файлов из папки `skills/`:
> - `verdikt-zakupki-vX.X.zip` — отчёт «берёмся / не берёмся»
> - `scan-zakupki-vX.X.zip` — анализ ТЗ и смет
> - `zhaloba-fas-vX.X.zip` — жалобы в УФАС
> - `zapros-razyasneniy-vX.X.zip` — запрос разъяснений
>
> Убедись, что у каждого скилла статус **Active**.

**Шаг 6. Финальное резюме**

Покажи короткое резюме:
- ✅ что готово автоматически
- ⏳ что осталось вручную (загрузить скиллы в Cowork; перезапустить
  Claude Code, чтобы подцепился MCP)

После перезапуска я смогу написать `@zakupki-eis` в новом чате и получить
доступ к инструментам скачивания закупок с ЕИС.

Действуй пошагово. Если на каком-то шаге нужна моя команда (закрыть/
открыть терминал, перезапустить Claude Code, подтвердить установку) —
останавливайся и проси.
"""


TEMPLATE = """# Установка Tender AI Tools

## Три простых действия

1. **Распакуй** этот архив в папку (рекомендуется `C:\\ClaudeCode\\tender-ai-tools\\`)
2. **Открой** Claude Code и переключись на распакованную папку
   (меню **File → Open Folder**)
3. **Скопируй промт ниже** и **вставь в чат** Claude Code

Всё остальное — установку Python, библиотек и MCP-сервера — Claude Code
сделает сам. От тебя нужно только подтверждать его действия.

---

## Промт для копирования

````markdown
{prompt}
````

---

## После установки — одно ручное действие

Загрузи 4 zip-файла из папки `skills/` в Cowork (через **Skills → Upload**).
Claude Code напомнит об этом в конце.

---

## Если что-то пошло не так

Открой файл **«Установка Tender AI Tools.pptx»** — там визуальная инструкция
со скриншотами. Делай по ней вручную.
"""


def generate(output_path: Path):
    content = TEMPLATE.format(prompt=PROMPT.strip())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    size = output_path.stat().st_size
    print(f"OK: {output_path}  ({size} байт)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", "-o", type=Path,
                        default=Path("INSTALL_PROMPT.md"))
    args = parser.parse_args()
    generate(args.output)


if __name__ == "__main__":
    main()
