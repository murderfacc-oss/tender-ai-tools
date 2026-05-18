# Дизайн: перевод MCP `zakupki-eis` со скрапа на ГосПлан API v2

_Дата: 2026-05-18 • Статус: спецификация, ожидает реализации_

## Проблема и цель

Сейчас загрузка документов закупок в `tender-ai-tools` реализована MCP-сервером
`zakupki-eis` через **скрап zakupki.gov.ru** (`mcp/zakupki_scraper.py`, 802
строки: HTML-парсинг BeautifulSoup/lxml). Скрап хрупкий (ломается при смене
вёрстки сайта), медленный и не даёт структурных данных.

Цель: заменить скрап на **ГосПлан API v2** — задокументированный JSON-API
поверх ЕИС. Источник истины по API — `_gosplan_spike.md` из проекта
«Zakupki 3.0» (`E:\ClaudeCode\Zakupki 3.0\memory\_gosplan_spike.md`) и
официальная OpenAPI-спека `https://swagger.gosplan.info/{fz44,fz223}/swagger.yaml`.

## Решения (зафиксированы с пользователем)

| Вопрос | Решение |
|---|---|
| Дыра покрытия 223-ФЗ в ГосПлан | **Только ГосПлан, скрап убрать целиком.** Непокрытые 223-ФЗ закупки не скачиваются — это осознанный размен. Обязательно внятное сообщение об ошибке, не молчаливый сбой. |
| Документы контракта (КС-2/КС-3/приёмка) | **Подтверждено спайком 2026-05-18.** Сам договор — `/contracts/{reg_num}` (`scanDocuments.CPEPAttachment[]`); закрывающие (КС-2/КС-3/приёмка/платёжки/экспертиза) — `/contracts/{reg_num}/procedures`. Схема контрактов ОТЛИЧАЕТСЯ от закупок (не `attachmentsInfo`). На тесте: 3 файла договора + 11 файлов исполнения = как старый скрап. |
| Подход к коду | **Чистая реализация с нуля** по `_gosplan_spike.md` + OpenAPI. Код из «Zakupki 3.0» НЕ переносим. |

## Ключевые факты об API (из `_gosplan_spike.md` + OpenAPI)

- База: `https://v2.gosplan.info` (тест: `https://v2test.gosplan.info`).
- До **2026-07-01** запросы без API-ключа. Потом ключ обязателен.
- Лимит prod: 600 req/min. `429` → пауза 60 сек, retry до 3 раз.
- Только HTTP GET. Рекомендуется заголовок `User-Agent`.
- Эндпоинты:
  - `GET /fz{44|223}/purchases/{purchase_number}` — карточка закупки.
  - `GET /fz{44|223}/contracts/{reg_num}` — карточка контракта (сам договор).
  - `GET /fz{44|223}/contracts/{reg_num}/procedures` — этапы исполнения (КС-2/КС-3/приёмка/платёжки/экспертиза).

**Закупка (purchases) — всё в `docs[0].source`:**
  - `attachmentsInfo.attachmentInfo[]` → `{publishedContentId, fileName, fileSize, docKindInfo.{code,name}, url}`. `url` — прямая ссылка zakupki.gov.ru/filestore, качается без авторизации.
  - `notificationInfo.purchaseObjectsInfo.{notDrug|drug}PurchaseObjectsInfo.purchaseObject[]` — позиции с характеристиками.
  - `notificationInfo.{customerRequirementsInfo, preferensesInfo, procedureInfo, contractConditionsInfo}`, `commonInfo`, `purchaseResponsibleInfo`.
  - 223-ФЗ: схема параллельная, ключи плоские (`attachments.document[]`, `lots.lot.lotData.lotItems`).
  - `docKindInfo.code` → подпапка: `POD→1_ТЗ`, `CP→2_Контракт`, `MRJ→3_НМЦК`, `CAR→5_Документация`, `AD→7_Прочее`; незнакомые — эвристика по словам в `name`.
  - Пустые attachments у свежих закупок — нормальная ситуация, не ошибка.

**Контракт (contracts) — схема ДРУГАЯ, чем у закупок** (установлено спайком 2026-05-18, см. Риски):
  - `GET /contracts/{reg_num}` → `docs[0].source.scanDocuments.CPEPAttachment[]` — сам договор: проект контракта `.doc`, печатная форма `.html`, электронный контракт `.xml`. Плюс `docs[0].source.printForm.url`. Поля `docKindInfo` НЕТ.
  - `GET /contracts/{reg_num}/procedures` → **JSON-массив**, элементы `doc_type: "contractProcedure"`. Закрывающие документы в каждом элементе `[i].source`:
    - `executions.execution.docAcceptance.receiptDocuments.attachment[]` → КС-2, КС-3, УПД, документы о приёмке.
    - `paymentDocuments.attachment[]` → счёт, платёжные поручения.
    - `examinationResultsDocuments.attachment[]` → акт экспертизы.
  - `attachment` бывает **и объектом, и массивом** — нормализовать к списку. Ключи вложения: `fileName`, `url`, `publishedContentId`, `docDescription`, `docRegNumber`. Типа документа (`docKindInfo`) нет — тип определяется родительским узлом (receipt/payment/examination).
  - Контракт раскладывается **плоско в подпапку `Контракт/`** (без под-подпапок — `docKindInfo` отсутствует; совпадает с прежним поведением скрапа).

## Архитектура

`mcp/zakupki_scraper.py` удаляется целиком. Новые модули в `mcp/`, каждый с
одной ответственностью:

| Модуль | Ответственность | Зависимости |
|---|---|---|
| `gosplan_client.py` | Только HTTP к API: `get_purchase(fz, number)`, `get_contract(fz, reg_num)`, `get_contract_procedures(fz, reg_num)`, `download_file(url, dest)`. База URL, User-Agent, API-ключ из env, ретраи 429, классификация ошибок. | `requests` |
| `doc_kind_map.py` | Чистая функция `folder_for(code, name) -> str`: `docKindInfo` → подпапка + эвристика по словам в `name`. | — |
| `gosplan_extract.py` | Из JSON: `iter_attachments` (закупки, 44 vs 223) + текстовая сводка `print_form.txt` + `iter_contract_attachments` (договор из `scanDocuments.CPEPAttachment[]` + закрывающие из procedures-массива). **Единственное место, где зашиты пути `docs[].source.*`.** | — |
| `gosplan_store.py` | Раскладка по папкам, санитайз имён (Windows, длина >180 → обрезка с сохранением расширения), `gosplan_meta.json`, `.tender_meta.json`, diff обновлений. | — |
| `server.py` | FastMCP, 4 инструмента — тонкий оркестратор. | модули выше |

Сигнатуры 4 инструментов **не меняются** — потребители (скиллы, проект
«Zakupki 3.0») не ломаются. Раскладка `1_ТЗ`…`7_Прочее` + `Контракт/`
сохраняется. `print_form.txt` сохраняется (его читает `scan-zakupki`), но
синтезируется из структурного JSON. `print_form.html` упраздняется (его
источника — HTML-страницы — больше нет).

## Поведение инструментов

**Определение ФЗ:** инструменты принимают только номер. Пробуем `/fz44/...`,
при 404 — `/fz223/...`. Автоопределение, сигнатуры не меняются.

### `download_tender(reg_number, folder)`
1. `get_purchase(fz, reg_number)` → сохранить сырой ответ `gosplan_meta.json`.
2. Извлечь вложения (44: `docs[0].source.attachmentsInfo.attachmentInfo[]`; 223: `attachments.document[]`).
3. Каждый файл: подпапка через `doc_kind_map`, скачать по прямому `url`, имя санитайзится, качаем во временный файл → rename при успехе (нет битых частичных файлов).
4. Собрать `print_form.txt` из `commonInfo` + `notificationInfo` (заказчик, объект, позиции с характеристиками, требования к участникам, преференции/нацрежим, сроки).
5. Записать `.tender_meta.json` (`fz`, номер, `updated_at`/`doc_updated_at`, набор `publishedContentId`).
6. Пустые attachments → `_no_attachments.txt` («извещение свежее, повторите позже»), не ошибка.

**Изменение поведения:** сейчас `download_tender` дополнительно сам ищет и
качает подписанный контракт. Линковка «извещение → контракт» в API не
подтверждена → `download_tender` теперь качает **только извещение**. В выводе —
подсказка «контракт подписан? → `download_contract(номер)`».

### `download_contract(contract_reestr_number, folder)`
1. `get_contract(fz, reg_num)` → сам договор из `docs[0].source.scanDocuments.CPEPAttachment[]` (+ `printForm.url`).
2. `get_contract_procedures(fz, reg_num)` → массив этапов; из каждого `[i].source` забрать закрывающие: `executions.execution.docAcceptance.receiptDocuments.attachment[]` (КС-2/КС-3/приёмка), `paymentDocuments.attachment[]` (платёжки), `examinationResultsDocuments.attachment[]` (экспертиза). `attachment` нормализуется obj→[obj].
3. Все файлы — **плоско в `Контракт/`** (без под-подпапок, у контрактов нет `docKindInfo`). Сырые ответы (контракт + procedures) → `Контракт/.contract_meta.json`.
4. Если `/procedures` пуст или нет узлов исполнения — не ошибка (контракт без актов / ещё в исполнении): качаем только сам договор, в выводе помечаем «закрывающих документов в API пока нет».

### `check_tender_updates(folder)`
Без скачивания: читаем `.tender_meta.json`, повторный `get_purchase`,
сравниваем `updated_at`/`doc_updated_at` и набор `publishedContentId` →
отчёт «новые / убранные документы».

### `update_tender(folder)`
То же + докачивает новые/изменённые, пишет `_changes.md`, старые версии не трёт.

## Обработка ошибок

- **404** → «Закупка `<номер>` не найдена в ГосПлан API. Для 223-ФЗ возможно вне покрытия API — проверьте номер или скачайте вручную с zakupki.gov.ru.» (явно, не молчаливо).
- **429** → пауза 60 сек, retry ≤3, потом «лимит ГосПлан, повторите позже».
- **Таймаут/сеть** → чёткое сообщение; частично скачанные файлы не остаются (temp → rename).
- **Пустые attachments** → не ошибка (см. выше).
- **Неожиданный JSON** (нет `docs[0].source`) → «структура ответа не распознана, сырой ответ в `gosplan_meta.json`» — данные не теряются.
- **API-ключ:** клиент читает `GOSPLAN_API_KEY` из env (через `env` в `.mcp.json` или системную переменную). Нет ключа — работает как сейчас (до 2026-07-01). Forward-compat; когда ключи станут обязательны — отсутствие даст внятную ошибку, не загадочный 401.

## Риски

1. **[СНЯТ 2026-05-18 спайком]** Реальный закрытый контракт `3366503536925000015` подтвердил схему: договор — `docs[0].source.scanDocuments.CPEPAttachment[]`; закрывающие (КС-2/КС-3/приёмка/платёжки/экспертиза) — `/contracts/{reg_num}/procedures` (узлы `receiptDocuments`/`paymentDocuments`/`examinationResultsDocuments`). 3+11 файлов = как старый скрап. Схема ОТЛИЧАЕТСЯ от закупок (не `attachmentsInfo`) — учтено в архитектуре и поведении. Остаточная страховка: если `/procedures` без узлов исполнения — `download_contract` не падает, качает сам договор и помечает отсутствие закрывающих.
2. **Дрейф схемы ГосПлан.** API внешний. Защита: все пути `docs[].source.*` собраны в одном модуле `gosplan_extract.py` — при изменении схемы правится одно место.
3. **223-ФЗ вне покрытия.** Принято пользователем. Митигация — внятное сообщение 404, а не тихий пропуск.

## Тестирование

**Юнит (без сети, фикстуры в `mcp/tests/fixtures/`):**
- `doc_kind_map` — известные коды + эвристика по `name`.
- `gosplan_extract` — фикстуры 44-ФЗ, 223-ФЗ, контракта: список вложений + `print_form.txt`. Кейсы: пустые attachments, нет `docs[0].source`.
- Санитайз имён (запрещённые символы, длина >180).
- Diff `.tender_meta.json` (новые/убранные `publishedContentId`, изменение `updated_at`).

Фикстуры снимаются один раз с реальных ответов API. Сеть в юнит-тестах не дёргаем.

**Проверочный шаг (ручной, с сетью) — ПЕРВЫМ в плане реализации:**
Снять живой ответ `/fz44/contracts/{реальный_номер_прошлого_контракта}` и
глазами проверить наличие `attachmentsInfo` с КС-2/КС-3. Снимает риск №1 до
завязки кода на гипотезу.

## Упаковка

- `launcher.py` REQUIRED + `requirements.txt`: убрать `beautifulsoup4`, `lxml`; оставить `requests`.
- Удалить `mcp/zakupki_scraper.py`.
- Обновить `mcp/CLAUDE.md` (источник данных = ГосПлан API) и проектные доки (`PROJECT.md`, `project/CHANGELOG.md`, `TODO.md`).
- Bump версии плагина 0.6.0 → **0.7.0** (смена источника данных; сигнатуры инструментов сохранены → minor, не major).

## Вне scope (YAGNI)

- Поиск закупок через API — в MCP его нет, не добавляем (отдельная задача).
- Миграция уже скачанных папок — старые `.tender_meta.json` от скрапа просто перезапишутся при первом `check`/`update`.
- Перенос/реюз кода из «Zakupki 3.0» — решено делать с нуля.
