# Tender AI Tools

Плагин Claude (Desktop и Code) для участия в госзакупках по 44-ФЗ на монтаж
слаботочных систем (видеонаблюдение, СКУД, речевое оповещение, СКС).

В одном плагине:
- **3 скилла** — `scan-zakupki`, `zhaloba-fas`, `zapros-razyasneniy`;
- **MCP-сервер `zakupki-eis`** — скачивает документы закупок напрямую с
  `zakupki.gov.ru` без API-ключей и регистрации.

## Что входит

### Скиллы

| Скилл | Триггер | Что делает |
|---|---|---|
| `scan-zakupki` | «прочитай закупку», «разбери» | Сопровождение закупки от подачи до закрытия |
| `zhaloba-fas` | «составь жалобу», «защита от РНП» | Жалобы в УФАС и антимонопольные заявления |
| `zapros-razyasneniy` | «запрос разъяснений» | Запрос разъяснений + Word-файл |

Скиллы активируются **автоматически** по описанию (`description` во frontmatter
`SKILL.md`) — ничего вручную выбирать не надо.

### MCP-сервер `zakupki-eis`

| Инструмент | Что делает |
|---|---|
| `download_tender` | Документы извещения + печатная форма ЕИС + (если есть) контракт |
| `download_contract` | Документы из реестра контрактов |
| `check_tender_updates` | Проверка изменений на сайте |
| `update_tender` | Скачать обновления и показать что изменилось |

## Установка

**Способ 1 — Upload plugin** (zip-файл):
1. Скачиваешь `tender-ai-v0.5.0.zip` (выпуски — в Releases репо).
2. Claude Desktop → **Customize → Personal plugins → `+` → Create plugin → Upload plugin** → выбираешь zip.
3. Перезапуск приложения.

**Способ 2 — Add marketplace** (через GitHub, с авто-обновлениями):
1. Claude Desktop → **Customize → Personal plugins → `+` → Create plugin → Add marketplace**.
2. Вводишь URL: `https://github.com/murderfacc-oss/tender-ai-tools`.
3. В списке плагинов нажимаешь **Install** у `tender-ai`.

Подробная инструкция — в [INSTALL.md](INSTALL.md).

**Требование:** Python 3.10+ в системе (для MCP-сервера). При первом
обращении к MCP `launcher.py` сам поставит pip-зависимости.

## Сборка плагина (для разработчика)

```bash
python scripts/build_plugin.py
# → tender-ai-v0.5.0.zip в корне репо
```

Версия читается из `.claude-plugin/plugin.json`. Зипуется структура репо:
`.claude-plugin/`, `.mcp.json`, `skills/`, `mcp/`, `README.md`.

Дополнительный скрипт `scripts/pack_skills.py` — упаковывает отдельные
скиллы (если нужно загрузить один скилл в Cowork без всего плагина).

## Структура репозитория

```
.
├── .claude-plugin/                ← метаданные плагина
│   ├── plugin.json                  манифест: name, version, author
│   └── marketplace.json             каталог для Add marketplace
├── .mcp.json                      ← конфиг MCP-сервера плагина
├── skills/                        ← скиллы
│   ├── scan-zakupki/
│   ├── zhaloba-fas/
│   └── zapros-razyasneniy/
├── mcp/                           ← MCP-сервер zakupki-eis
│   ├── launcher.py                  обёртка с auto-pip + UTF-8
│   ├── server.py                    FastMCP, 4 инструмента
│   ├── zakupki_scraper.py           парсер zakupki.gov.ru
│   └── requirements.txt
├── project/                       ← заметки проекта (НЕ часть плагина)
│   ├── research/                    практика УФАС
│   ├── observations.md              наблюдения по закупкам
│   ├── PROJECT.md                   цели и контекст
│   └── CHANGELOG.md                 журнал решений
├── scripts/
│   ├── build_plugin.py            ← собирает tender-ai-v*.zip
│   └── pack_skills.py             ← упаковка отдельных скиллов (вспомогательно)
├── README.md, CLAUDE.md, TODO.md, INSTALL.md
```

## История репозиториев

Раньше MCP-сервер жил в отдельном репозитории
[`zakupki-eis`](https://github.com/murderfacc-oss/zakupki-eis). С версии
0.5 он влит в этот репо как папка `mcp/` через `git subtree` — история
сохранена. Старый репо архивирован.

## Версионирование

- **Плагин** — версия в `.claude-plugin/plugin.json` (читает `build_plugin.py`).
- **Скиллы** — версии в их `CHANGELOG.md`.
- **MCP** — версии в коммитах, ведётся в основной `TODO.md`.

Текущая версия плагина: **0.5.0**.
