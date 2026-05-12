# Установка плагина Tender AI

Плагин ставится в Claude Desktop одним действием — через штатный интерфейс
загрузки плагинов. Два варианта на выбор.

---

## Способ 1. Upload plugin (один zip-файл)

Подходит если: хочешь поставить разово, без авто-обновлений.

1. Скачай свежий `tender-ai-v<версия>.zip` со страницы
   [Releases](https://github.com/murderfacc-oss/tender-ai-tools/releases).
2. Открой **Claude Desktop**.
3. **Customize → Personal plugins → `+` → Create plugin → Upload plugin**.
4. Выбери скачанный zip.
5. Перезапусти Claude Desktop.

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
| `@zakupki-eis` не появляется | 1) Перезапусти Claude Desktop полностью (через трей, не крестиком). 2) Проверь что в `cmd` команда `python --version` печатает 3.10+ — если нет, поставь с python.org с галочкой «Add Python to PATH». 3) В Personal plugins нажми **Disable → Enable** у `tender-ai`, чтобы Claude перезагрузил `.mcp.json`. |
| `python` открывает Microsoft Store | Это заглушка Windows. Поставь настоящий Python с [python.org](https://python.org) (с галочкой «Add Python to PATH») и перезапусти Claude. В логах launcher напишет об этом явно. |
| MCP падает на старте | Открой консоль приложения — там будет строка `[zakupki-eis launcher] python=...` от `launcher.py`. Если её **нет совсем** — Claude вообще не нашёл Python (ставь с python.org). Если есть, но дальше ошибка — `pip` не смог поставить зависимости. |
| Скилл не активируется | Перезапуск приложения; убедись что плагин включён в **Personal plugins** |
| `pip install` падает на корпоративном прокси | В консоли увидишь это; задайте переменную `HTTPS_PROXY` или ставьте пакеты вручную: `pip install mcp requests beautifulsoup4 lxml` |
| MCP «работает у разработчика, у меня нет» | На машине разработчика MCP мог быть прописан **отдельно** через `claude mcp add` или руками в `claude_desktop_config.json` — это не часть плагина. Проверь, что у тебя плагин действительно стоит свежей версии (см. в Personal plugins) и что ты дёрнул **Disable → Enable** после обновления. |

---

## Альтернатива для Claude Code (CLI)

Если используешь Claude Code в терминале, не Desktop:

```bash
/plugin marketplace add github:murderfacc-oss/tender-ai-tools
/plugin install tender-ai
```

Дальше всё то же самое — скиллы и MCP подцепятся, при первом обращении
MCP поставит зависимости.
