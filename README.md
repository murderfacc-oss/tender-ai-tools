# Tender AI Tools

AI-плагин для Claude Code: участие в госзакупках по 44-ФЗ на монтаж
слаботочных систем (видеонаблюдение, СКУД, речевое оповещение, СКС).

## Что входит

### Скиллы

| Скилл | Триггер | Что делает |
|---|---|---|
| `scan-zakupki` | «прочитай закупку», «разбери» | Сопровождение закупки от подачи до закрытия |
| `zhaloba-fas` | «составь жалобу», «защита от РНП» | Жалобы в УФАС и антимонопольные заявления |
| `zapros-razyasneniy` | «запрос разъяснений» | Запрос разъяснений + Word-файл |

### MCP-сервер `zakupki-eis`

Скачивает документы закупок напрямую с zakupki.gov.ru без API-ключей.

| Инструмент | Что делает |
|---|---|
| `download_tender` | Документы извещения + печатная форма ЕИС + (если есть) контракт |
| `download_contract` | Документы из реестра контрактов |
| `check_tender_updates` | Проверка изменений на сайте |
| `update_tender` | Скачать обновления и показать что изменилось |

## Дистрибуция

Всё упаковывается в один `.plugin` файл, который партнёр устанавливает
в Claude Code одной кнопкой:

```bash
python scripts/build_plugin.py
# → tender-ai.plugin (готов к отправке партнёру)
```

Партнёр:
1. Получает `tender-ai.plugin`.
2. Перетаскивает в Claude Code → нажимает **Install**.
3. Перезапускает Claude Code.

При первом обращении к MCP `launcher.py` сам поставит pip-зависимости —
терминал не нужен. Требование: Python 3.10+ в системе.

## Структура репозитория

```
.
├── README.md, CLAUDE.md, TODO.md, INSTALL.md
├── project/
│   ├── skills/                    ← исходники скиллов
│   │   ├── scan-zakupki/
│   │   ├── zhaloba-fas/
│   │   ├── zapros-razyasneniy/
│   │   └── verdikt-zakupki/       ← не в плагине, для истории
│   ├── research/                  ← практика УФАС
│   ├── observations.md            ← наблюдения по закупкам
│   └── PROJECT.md                 ← цели и контекст
├── mcp/                           ← MCP-сервер (был отдельным репо zakupki-eis)
│   ├── launcher.py                  обёртка с auto-pip + UTF-8
│   ├── server.py                    FastMCP, 4 инструмента
│   ├── zakupki_scraper.py           парсер zakupki.gov.ru
│   └── requirements.txt
├── scripts/
│   ├── build_plugin.py            ← собирает .plugin файл
│   └── pack_skills.py             ← упаковка скиллов отдельно (Cowork legacy)
└── plugin-build/                  ← рабочая папка сборки (gitignore)
```

## История репозиториев

Раньше MCP-сервер жил в отдельном репозитории
[`zakupki-eis`](https://github.com/murderfacc-oss/zakupki-eis). С версии
0.5 он влит в этот репо как папка `mcp/` через `git subtree` — история
сохранена. Старый репо архивирован, ссылки на него остаются рабочими
для read-only.

## Версионирование

- **Скиллы** — версии в их `CHANGELOG.md`.
- **MCP** — версии в коммитах (CHANGELOG отсутствует, ведётся в основной TODO.md).
- **Плагин** — версия в `scripts/build_plugin.py`, поле `version` в `PLUGIN_JSON`.

Текущая версия плагина: **0.4.0**.
