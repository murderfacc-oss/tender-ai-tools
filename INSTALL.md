# Инструкция по установке

Настройка займёт ~15 минут. После неё у тебя будет:
- 4 скилла в Cowork (анализ закупок, жалобы, запросы разъяснений)
- MCP-сервер, скачивающий документы с ЕИС прямо в чат

---

## Требования

- **Python 3.10+** — скачать с python.org (отметить «Add to PATH» при установке)
- **Claude Code** — десктоп-приложение Anthropic, скачать с claude.ai/download
- **Аккаунт Cowork** — попросить у меня ссылку приглашения

> MCP-сервер скачивает документы напрямую с zakupki.gov.ru — бесплатно,
> без API-ключей и регистраций.

---

## Шаг 1. Клонировать репозитории

Открыть **Terminal** (или Git Bash на Windows) и выполнить:

```bash
# Создать рабочую папку
mkdir C:\ClaudeCode
cd C:\ClaudeCode

# Клонировать скиллы и документы
git clone https://github.com/murderfacc-oss/tender-ai-tools.git Analiz-tender

# Клонировать MCP-сервер
git clone https://github.com/murderfacc-oss/zakupki-eis.git sabytrade-mcp
```

---

## Шаг 2. Установить зависимости Python

```bash
# Зависимости MCP-сервера
cd C:\ClaudeCode\sabytrade-mcp
pip install -r requirements.txt

# Зависимость для генерации Word-файлов (скилл zapros-razyasneniy)
pip install python-docx
```

---

## Шаг 3. Подключить MCP к Claude Code

Открыть Claude Code → иконка настроек (⚙) → **MCP Servers** → **Add server** → заполнить:

| Поле | Значение |
|---|---|
| Name | `zakupki-eis` |
| Type | `stdio` |
| Command | `python` |
| Args | `C:\ClaudeCode\sabytrade-mcp\server.py` |

Сохранить. Перезапустить Claude Code.

**Проверка:** в новом чате написать `@zakupki-eis` — должны появиться инструменты `download_tender`, `check_tender_updates` и др.

---

## Шаг 4. Залить скиллы в Cowork

Каждый скилл упаковывается в zip и загружается через интерфейс Cowork.

**4.1.** Собрать zip-архивы скиллов:

```bash
cd C:\ClaudeCode\Analiz-tender
python scripts/pack_skills.py
```

Скрипт создаст файлы в `project/skills/`:
- `verdikt-zakupki-vX.X.zip`
- `scan-zakupki-vX.X.zip`
- `zhaloba-fas-vX.X.zip`
- `zapros-razyasneniy-vX.X.zip`

**4.2.** Для каждого zip:

1. Открыть Cowork → **Skills** → **Upload**
2. Выбрать zip-файл
3. Убедиться, что скилл появился в списке и статус **Active**

---

## Шаг 5. Проверить работу

Открыть Claude Code, создать новый чат, приложить любой Word/PDF из закупки и написать:

```
оцени закупку
```

Должен сработать скилл `verdikt-zakupki` и вернуть отчёт «берёмся/не берёмся».

---

## Обновление (когда я выпускаю новую версию)

```bash
# Получить изменения
cd C:\ClaudeCode\Analiz-tender
git pull

cd C:\ClaudeCode\sabytrade-mcp
git pull
pip install -r requirements.txt   # на случай новых зависимостей

# Пересобрать и переустановить нужные скиллы
cd C:\ClaudeCode\Analiz-tender
python scripts/pack_skills.py

# Затем в Cowork: удалить старую версию скилла, загрузить новый zip
```

> CHANGELOG каждого скилла лежит в `project/skills/<имя>/CHANGELOG.md` — смотреть там что изменилось.

---

## Структура папок после установки

```
C:\ClaudeCode\
  Analiz-tender\           ← репозиторий со скиллами
    project\
      skills\              ← исходники скиллов
      research\            ← практика УФАС
    scripts\
      pack_skills.py
    INSTALL.md
    README.md
  sabytrade-mcp\           ← MCP-сервер
    server.py
    requirements.txt
```

---

## Частые проблемы

**`python` не найден в PATH**
→ Переустановить Python с галочкой «Add Python to PATH».
→ Или использовать `py` вместо `python`.

**MCP не появляется в Claude Code**
→ Убедиться, что путь в Args указан без ошибок. Открыть Терминал и запустить `python C:\ClaudeCode\sabytrade-mcp\server.py` — если упадёт с ошибкой, будет видно что не так.

**`ModuleNotFoundError: No module named 'mcp'`**
→ Снова выполнить `pip install -r requirements.txt` из папки sabytrade-mcp.

**Скилл не срабатывает в Cowork**
→ Проверить, что zip содержит файл `SKILL.md` в корне архива (не в подпапке).
→ Убедиться, что скилл в статусе **Active**.
