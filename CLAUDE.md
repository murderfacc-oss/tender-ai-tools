# Tender AI Tools — описание проекта

## Что это

Плагин Claude (Desktop и Code) для участия в госзакупках по **44-ФЗ** на монтаж слаботочных систем (видеонаблюдение, СКУД, речевое оповещение, СКС).

В одном плагине: 3 скилла (`scan-zakupki`, `zhaloba-fas`, `zapros-razyasneniy`) + MCP-сервер `zakupki-eis` для скачивания документов с ЕИС. Распространяется как один файл `tender-ai-v<версия>.zip` (через **Upload plugin** в Claude Desktop) или через GitHub-marketplace (через **Add marketplace**).

Владелец: Артём (murderfacc@gmail.com)  
Дата начала: 2025  
Статус: production, скиллы активно используются

---

## Структура репозитория

```
.claude-plugin/             ← метаданные плагина (видит Claude при установке)
  plugin.json               ← манифест: name, version, author
  marketplace.json          ← каталог для Add marketplace по GitHub-URL
.mcp.json                   ← конфиг MCP-серверов плагина (использует ${CLAUDE_PLUGIN_ROOT})

skills/                     ← скиллы (видны Claude как часть плагина)
  scan-zakupki/             ← анализ закупки от подачи до закрытия
  zhaloba-fas/              ← жалобы в УФАС, защита от РНП
  zapros-razyasneniy/       ← запрос разъяснений + Word-файл

mcp/                        ← MCP-сервер zakupki-eis
  launcher.py               ← обёртка: при первом запуске ставит pip
  server.py                 ← FastMCP, 4 инструмента
  zakupki_scraper.py        ← парсер zakupki.gov.ru
  requirements.txt
  CLAUDE.md                 ← локальное описание MCP

project/                    ← заметки проекта (НЕ часть плагина)
  research/                 ← практика УФАС, исследования
  observations.md           ← наблюдения по закупкам
  PROJECT.md                ← цели и контекст проекта
  CHANGELOG.md              ← журнал проектных решений
  tenders/                  ← реальные документы закупок [в .gitignore]

scripts/
  build_plugin.py           ← основной: собирает tender-ai-v<версия>.zip для Upload plugin
  pack_skills.py            ← вспомогательный: упаковка отдельных скиллов (для Cowork)

INSTALL.md                  ← инструкция для партнёра (установка плагина)
README.md                   ← публичное описание
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

## Дистрибуция

**Один плагин, два способа установки** — выбирает пользователь.

### Способ 1. Upload plugin (zip-файл)

Собираем плагин:
```bash
python scripts/build_plugin.py
# → tender-ai-v0.5.0.zip
```

Партнёр:
1. Открывает Claude Desktop.
2. **Customize → Personal plugins → `+` → Create plugin → Upload plugin**.
3. Выбирает полученный zip.
4. Перезапуск Claude → плагин активен.

### Способ 2. Add marketplace (GitHub)

В корне репо лежит `.claude-plugin/marketplace.json` — каталог из одного плагина.
Партнёр:
1. **Customize → Personal plugins → `+` → Create plugin → Add marketplace**.
2. Вводит URL: `https://github.com/murderfacc-oss/tender-ai-tools`.
3. Находит в списке плагин `tender-ai` → Install.

**Обновления** при способе 2 — автоматически: `git push` на main → пользователь делает Refresh marketplace и получает свежую версию.

### Что про MCP

MCP-сервер `zakupki-eis` подцепляется автоматически — он описан в `.mcp.json` плагина. `launcher.py` при первом запуске сам ставит pip-зависимости. Никаких `claude mcp add` руками.

### Прошлое решение про «отказ от плагина» было ошибочным

В мае 2026 в репо было записано «отказались от плагинного пути в пользу раздельной установки». Причина была — Python-зависимости и сложность установки. **На практике Claude Desktop с весны 2026 поддерживает плагины через UI** (`Customize → Personal plugins → Upload plugin / Add marketplace`), и `launcher.py` снимает проблему с pip. Плагин снова сделан основным способом дистрибуции.

`scripts/pack_skills.py` оставлен как вспомогательный — для случаев, когда нужно загрузить один скилл отдельно (в Cowork, для тестов).

---

## Ключевые решения

| Решение | Обоснование |
|---|---|
| Плагин как основной способ дистрибуции | Claude Desktop UI принимает плагины через Upload plugin / Add marketplace одним действием |
| Структура репо = структура плагина (skills/, mcp/, .mcp.json в корне) | Один источник правды; zip — это просто архив нужных папок репо |
| `${CLAUDE_PLUGIN_ROOT}` в `.mcp.json` | Портабельный путь — работает у любого пользователя без правок |
| `launcher.py` вместо прямого запуска `server.py` | Автоустановка pip-зависимостей при первом старте, нужен только Python 3.10+ в системе |
| Скрапинг zakupki.gov.ru | Никаких API-ключей, данные открыты |
| verdikt-zakupki удалён из репо | Не используется в текущем процессе работы; история — в git |

---

## Конфиг claude_desktop_config.json

При установке плагина MCP-серверы регистрируются автоматически через `.mcp.json` плагина — руками править `claude_desktop_config.json` не нужно. Файл нужен только для отдельных не-плагинных MCP-серверов (например, `analiz-tender-fs` — filesystem-сервер для доступа к файлам из чата).

Расположение на Windows: `C:\Users\<имя>\AppData\Roaming\Claude\claude_desktop_config.json`.

---

## Связанные репозитории

| Репо | Статус |
|---|---|
| `murderfacc-oss/tender-ai-tools` | **Активный** — единое место: скиллы, MCP, скрипты, документация |
| `murderfacc-oss/zakupki-eis` | Архивирован — содержимое перенесено в `mcp/` основного репо |
