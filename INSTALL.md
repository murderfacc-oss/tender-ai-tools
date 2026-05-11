# Установка плагина Tender AI

Плагин ставится в Claude Desktop одним действием — через штатный интерфейс
загрузки плагинов. Два варианта на выбор.

---

## Способ 1. Upload plugin (один zip-файл)

Подходит если: получил файл `tender-ai-v0.5.2.zip` от меня в личке и хочешь поставить разово.

1. Открой **Claude Desktop**.
2. **Customize → Personal plugins → `+` → Create plugin → Upload plugin**.
3. Выбери файл `tender-ai-v0.5.2.zip`.
4. Перезапусти Claude Desktop.

Готово. Скиллы и MCP подцепятся автоматически.

---

## Способ 2. Add marketplace (через GitHub, с авто-обновлениями)

Подходит если: хочешь чтобы плагин обновлялся сам при выходе новой версии.

1. Открой **Claude Desktop**.
2. **Customize → Personal plugins → `+` → Create plugin → Add marketplace**.
3. Вставь URL:
   ```
   https://github.com/murderfacc-oss/tender-ai-tools
   ```
4. В появившемся списке плагинов нажми **Install** у `tender-ai`.
5. Перезапусти Claude Desktop.

Обновления потом: в том же меню найди маркетплейс → **Refresh** →
если есть новая версия, кнопка **Update**.

---

## Требования

- **Claude Desktop** (десктопное приложение, не путать с веб-версией claude.ai).
- **Python 3.10+** в системе — нужен для MCP-сервера `zakupki-eis`.
  Если нет: скачай с [python.org](https://python.org) с галочкой
  «Add Python to PATH».

При первом обращении к MCP (`@zakupki-eis` в чате) `launcher.py` сам
поставит нужные pip-пакеты — никаких ручных команд в терминале не нужно.

---

## Проверка после установки

В новом чате Claude Desktop:

1. **MCP подцеплен:** напиши `@zakupki-eis` — должно появиться 4 инструмента
   (`download_tender`, `download_contract`, `check_tender_updates`,
   `update_tender`).
2. **Скиллы работают:** напиши «прочитай закупку 0373200082122000012» —
   должен автоматически активироваться `scan-zakupki` и скачать
   документы через MCP.

---

## Что делать если не работает

| Симптом | Что проверить |
|---|---|
| `@zakupki-eis` не появляется | Перезапусти Claude Desktop полностью (не просто закрытие окна, а через трей) |
| MCP падает на старте | Открой консоль приложения — там будет ошибка от `launcher.py`. Чаще всего: нет Python в PATH |
| Скилл не активируется | Перезапуск приложения; убедись что плагин включён в **Personal plugins** |
| `pip install` падает на корпоративном прокси | В консоли увидишь это; задайте переменную `HTTPS_PROXY` или ставьте пакеты вручную: `pip install mcp requests beautifulsoup4 lxml` |

---

## Альтернатива для Claude Code (CLI)

Если используешь Claude Code в терминале, не Desktop:

```bash
/plugin marketplace add github:murderfacc-oss/tender-ai-tools
/plugin install tender-ai
```

Дальше всё то же самое — скиллы и MCP подцепятся, при первом обращении
MCP поставит зависимости.
