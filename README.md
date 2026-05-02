# Tender AI Tools

AI-ассистент для участия в госзакупках по 44-ФЗ на монтаж слаботочных систем
(видеонаблюдение, СКУД, речевое оповещение, СКС).

## Состав

### Скиллы (Cowork)

| Скилл | Что делает | Версия |
|---|---|---|
| `verdikt-zakupki` | Отчёт «берёмся/не берёмся» по документации закупки | v1.0 |
| `scan-zakupki` | Детальный анализ ТЗ, смет, выявление расхождений | v0.3 |
| `zhaloba-fas` | Жалоба в УФАС: нарушения в документации, защита от РНП, сговор | v0.1 |
| `zapros-razyasneniy` | Запрос разъяснений + генерация Word-файла | v0.1.1 |

### MCP-сервер

`sabytrade-mcp` — скачивает документы закупок с ЕИС по реестровому номеру.
Репозиторий: **[github.com/murderfacc-oss/zakupki-eis](https://github.com/murderfacc-oss/zakupki-eis)**

## Установка

Полная инструкция: **[INSTALL.md](INSTALL.md)**

## Структура репозитория

```
project/
  skills/          ← исходники скиллов
    verdikt-zakupki/
    scan-zakupki/
    zhaloba-fas/
    zapros-razyasneniy/
  research/        ← практика УФАС, исследования
  observations.md  ← накопленные наблюдения по закупкам
scripts/
  pack_skills.py   ← упаковать скиллы в zip для Cowork
INSTALL.md
```
