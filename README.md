# Tender AI Tools

AI-плагин для Claude Code: участие в госзакупках по 44-ФЗ на монтаж
слаботочных систем (видеонаблюдение, СКУД, речевое оповещение, СКС).

## Что входит

| Скилл | Триггер | Что делает |
|---|---|---|
| `scan-zakupki` | «прочитай закупку», «разбери» | Сопровождение закупки от подачи до закрытия |
| `zhaloba-fas` | «составь жалобу», «защита от РНП» | Жалобы в УФАС и антимонопольные заявления |
| `zapros-razyasneniy` | «запрос разъяснений» | Запрос разъяснений + Word-файл |

Плюс MCP-сервер `zakupki-eis` — скачивает документы закупок напрямую с
zakupki.gov.ru, без API-ключей.

## Дистрибуция

Всё упаковывается в один `.plugin` файл, который партнёр устанавливает
в Claude Code одной кнопкой.

```bash
python scripts/build_plugin.py
# → tender-ai.plugin (готов к отправке партнёру)
```

Партнёр:
1. Получает `tender-ai.plugin`
2. Перетаскивает в Claude Code → нажимает **Install**
3. Один раз в терминале: `pip install -r <папка_плагина>/mcp/requirements.txt`
4. Перезапускает Claude Code

После — все скиллы и MCP доступны.

## Структура репозитория

```
project/
  skills/          ← исходники скиллов
    scan-zakupki/
    zhaloba-fas/
    zapros-razyasneniy/
    verdikt-zakupki/   ← в плагин не входит, оставлен для истории
  research/        ← практика УФАС, исследования
  observations.md  ← наблюдения по закупкам
scripts/
  build_plugin.py  ← собирает .plugin файл
  pack_skills.py   ← упаковать отдельные скиллы (legacy, для Cowork)
plugin-build/
  tender-ai/       ← рабочая папка для сборки плагина
```

MCP-сервер живёт в отдельном репозитории
[zakupki-eis](https://github.com/murderfacc-oss/zakupki-eis) — скрипт сборки
автоматически копирует его в плагин.

## Версионирование

Версии скиллов — в их `CHANGELOG.md`. Версия плагина — в
`scripts/build_plugin.py` (поле `version` в `PLUGIN_JSON`).
