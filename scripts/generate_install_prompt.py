"""
Генерирует файл INSTALL_PROMPT.md — инструкцию + готовый промт
для Claude Code, чтобы он сам выполнил установку.

Использование:
    python scripts/generate_install_prompt.py
    python scripts/generate_install_prompt.py --output INSTALL_PROMPT.md
"""

import argparse
from pathlib import Path


PROMPT = r"""Ты помогаешь пользователю установить «Tender AI Tools» — набор
инструментов для участия в госзакупках по 44-ФЗ.

Текущая папка должна быть корнем распакованного архива. В ней есть:
- `skills/` — 4 zip-файла со скиллами (загружаются в Cowork вручную)
- `mcp/` — Python-сервер MCP (server.py, zakupki_scraper.py, requirements.txt)
- `Установка Tender AI Tools.pptx` — полная презентация (для справки)

Сначала проверь, что эти папки и файлы на месте. Если нет — скажи об этом и
останови установку, попроси пользователя проверить, что архив распакован
правильно.

Дальше выполни шаги:

**Шаг 1. Проверить Python**

Проверь, что python и pip доступны (`python --version`, `pip --version`).
Если нет — попроси пользователя установить Python 3.10+ с сайта python.org
(обязательно с галочкой «Add Python to PATH») и запустить промт заново.

**Шаг 2. Установить зависимости MCP**

Установи зависимости MCP-сервера:
- `pip install -r mcp/requirements.txt`

Дополнительно установи библиотеку для генерации Word-файлов
(её использует скилл «zapros-razyasneniy»):
- `pip install python-docx`

**Шаг 3. Зарегистрировать MCP в Claude Code**

MCP-сервер скачивает документы закупок напрямую с сайта zakupki.gov.ru —
бесплатно, без API-ключей и регистраций.

Получи абсолютный путь к `mcp/server.py` (используй текущую рабочую папку).
Выполни команду:

```
claude mcp add --scope user zakupki-eis python <АБСОЛЮТНЫЙ_ПУТЬ>/mcp/server.py
```

Если команда `claude mcp add` недоступна — добавь сервер вручную в
конфиг-файл Claude Code. На Windows это обычно
`C:\Users\<имя>\.claude.json` (поле `mcpServers`). Покажи мне результат и
попроси перезапустить Claude Code.

**Шаг 4. Проверить, что MCP стартует**

Запусти `python mcp/server.py --help` (или просто `python mcp/server.py` на
1–2 секунды и останови) — убедись, что нет ошибок импорта. Если есть —
покажи мне текст ошибки и предложи решение.

**Шаг 5. Дать инструкцию по загрузке скиллов**

Я не могу загрузить скиллы в Cowork через тебя — это делается через веб-интерфейс.
Напиши мне понятный список:

> Открой Cowork (URL уточни у партнёра).
> Перейди в раздел Skills → Upload. Загрузи каждый из 4 zip-файлов из папки
> `skills/`:
> - verdikt-zakupki-vX.X.zip — отчёт «берёмся / не берёмся»
> - scan-zakupki-vX.X.zip — анализ ТЗ и смет
> - zhaloba-fas-vX.X.zip — жалобы в УФАС
> - zapros-razyasneniy-vX.X.zip — запрос разъяснений
> Убедись, что у каждого статус Active.

**Шаг 6. Финальное резюме**

Покажи короткое резюме:
- ✅ что готово
- ⏳ что осталось сделать вручную (загрузить скиллы в Cowork; перезапустить
  Claude Code, чтобы подцепился MCP)

Выполняй шаги по очереди, после каждого жди подтверждения от меня.
Работай на русском языке.
"""


TEMPLATE = """# Установка Tender AI Tools — через Claude Code

Если у тебя уже установлен **Claude Code** — установка займёт 5 минут.
Скопируй промт ниже и вставь в чат.

---

## Что нужно сделать

1. **Распакуй архив** в удобное место (рекомендуется `C:\\ClaudeCode\\tender-ai-tools\\`).
2. **Открой Claude Code** и переключись на распакованную папку:
   - В меню: **File → Open Folder** → выбери папку с распакованным архивом.
   - Либо в терминале: `cd C:\\ClaudeCode\\tender-ai-tools && claude`
3. **Скопируй промт ниже** (одной кнопкой — он внутри блока кода) и **вставь в чат**.

---

## Промт для копирования

````markdown
{prompt}
````

---

## Если Claude Code недоступен

Открой файл **«Установка Tender AI Tools.pptx»** — там пошаговая презентация
на 11 слайдов. Делай по ней вручную.

---

## Что должно получиться в итоге

- В Claude Code в новом чате доступен `@zakupki-eis` — можно скачивать
  документы закупок прямо из чата.
- В Cowork активны 4 скилла — анализ закупок, жалобы, запросы разъяснений.
- В любом чате можно прикрепить документ закупки и написать «оцени закупку» —
  получишь отчёт «берёмся / не берёмся».
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
