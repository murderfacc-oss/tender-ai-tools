# Tender AI Tools — описание проекта

## Что это

Плагин для Claude Code: инструменты для участия в госзакупках по **44-ФЗ** на монтаж слаботочных систем (видеонаблюдение, СКУД, речевое оповещение, СКС).

Владелец: Артём (murderfacc@gmail.com)  
Дата начала: 2025  
Статус: production, скиллы активно используются

---

## Структура репозитория

```
project/
  skills/                   ← исходники скиллов (в плагин идут 3 из 4)
    scan-zakupki/           ← анализ закупки от подачи до закрытия
    zhaloba-fas/            ← жалобы в УФАС, защита от РНП
    zapros-razyasneniy/     ← запрос разъяснений + Word-файл
    verdikt-zakupki/        ← [не в плагине] остался для истории
  research/                 ← практика УФАС, исследования
  observations.md           ← наблюдения по закупкам
  PROJECT.md                ← цели и контекст проекта
  tenders/                  ← реальные документы закупок [в .gitignore]

mcp/                        ← MCP-сервер zakupki-eis (раньше отдельный репо)
  launcher.py               ← обёртка: при первом запуске ставит pip
  server.py                 ← FastMCP, 4 инструмента
  zakupki_scraper.py        ← парсер zakupki.gov.ru
  requirements.txt
  CLAUDE.md                 ← локальное описание MCP

scripts/
  build_plugin.py           ← собирает tender-ai.plugin (ZIP)
  pack_skills.py            ← упаковать отдельные скиллы (для Cowork, legacy)

plugin-build/               ← рабочая папка сборки [в .gitignore]
tender-ai.plugin            ← готовый плагин для отправки партнёру [в .gitignore]
Для партнёра/               ← готовая папка для отправки [в .gitignore]
INSTALL.md                  ← инструкция для партнёра
```

---

## MCP-сервер zakupki-eis

Живёт в этом же репо, в папке `mcp/`. Раньше был отдельным репозиторием
`github.com/murderfacc-oss/zakupki-eis` — слит сюда через `git subtree`,
история сохранена. Старый репо архивирован.

Скачивает документы закупок напрямую с **zakupki.gov.ru** — без API-ключей, без регистрации.

**Файлы (в `mcp/`):**
- `server.py` — MCP-сервер (4 инструмента)
- `launcher.py` — обёртка: при первом запуске ставит pip-зависимости автоматически
- `zakupki_scraper.py` — парсер ЕИС

**Инструменты MCP:**
| Инструмент | Что делает |
|---|---|
| `download_tender` | Скачивает документы закупки по номеру или URL |
| `download_contract` | Скачивает документы контракта |
| `check_tender_updates` | Проверяет, появились ли новые события по закупке |
| `update_tender` | Обновляет локальный снимок закупки |

---

## Плагин tender-ai.plugin

Собирается командой:
```bash
python scripts/build_plugin.py
```

Что входит в плагин:
- 3 скилла: `scan-zakupki`, `zhaloba-fas`, `zapros-razyasneniy`
- MCP-сервер: `launcher.py`, `server.py`, `zakupki_scraper.py`
- Манифест `.claude-plugin/plugin.json`
- `.mcp.json` с конфигом MCP

Партнёр устанавливает: перетаскивает `.plugin` в Claude Code → Install → перезапуск.  
Python-зависимости MCP ставятся автоматически при первом использовании.

---

## Ключевые решения

| Решение | Обоснование |
|---|---|
| Плагин как единый `.plugin` файл | Партнёр устанавливает одной кнопкой, без терминала |
| `launcher.py` вместо прямого запуска `server.py` | Автоустановка pip-зависимостей при первом старте |
| Скрапинг zakupki.gov.ru | Никаких API-ключей, данные открыты |
| verdikt-zakupki не в плагине | Не используется в текущем процессе работы |
| `${CLAUDE_PLUGIN_ROOT}` в `.mcp.json` | Портабельный путь, работает у любого пользователя |

---

## Конфиг claude_desktop_config.json

Расположен: `C:\Users\user\AppData\Roaming\Claude\claude_desktop_config.json`

Сейчас зарегистрированы два MCP-сервера:
- `zakupki-eis` — запускает MCP напрямую из `sabytrade-mcp/server.py`
- `analiz-tender-fs` — filesystem-сервер для доступа к файлам проекта из чата

---

## Связанные репозитории

| Репо | Статус |
|---|---|
| `murderfacc-oss/tender-ai-tools` | **Активный** — единое место: скиллы, MCP, скрипты, документация |
| `murderfacc-oss/zakupki-eis` | Архивирован — содержимое перенесено в `mcp/` основного репо |
