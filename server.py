"""
MCP-сервер для работы с закупками.
Данные берутся напрямую с zakupki.gov.ru — бесплатно, без API-ключей.

Инструменты:
  1. download_tender      — скачать все документы закупки по номеру извещения
  2. check_tender_updates — проверить обновились ли документы на сайте
  3. update_tender        — скачать обновления и показать что изменилось

Запуск для теста: python server.py
Подключение: прописать в конфиг Claude Desktop (см. CLAUDE.md)
"""

from mcp.server.fastmcp import FastMCP
import zakupki_scraper

# Создаём MCP-сервер
mcp = FastMCP("Закупки ЕИС")


@mcp.tool()
def download_tender(reg_number: str, folder: str) -> str:
    """
    Скачать все документы закупки с zakupki.gov.ru в указанную папку.
    Работает бесплатно — напрямую с сайта ЕИС, без API-ключей.

    Файлы автоматически раскладываются по подпапкам:
      1_ТЗ, 2_Контракт, 3_НМЦК, 4_Смета, 5_Документация, 6_Протоколы, 7_Прочее

    Когда использовать:
    - Пользователь говорит "скачай документы закупки НОМЕР"
    - Пользователь говорит "загрузи файлы по закупке НОМЕР в папку ПУТЬ"

    Параметры:
    - reg_number: номер извещения закупки (например 0373200082122000012)
    - folder: путь к папке куда сохранять файлы.
      Если папка не существует — будет создана автоматически.
      Примеры: ".", "./docs", "C:/zakupki/0373200082122000012"

    После скачивания в папке появится .tender_meta.json — служебный файл
    для отслеживания обновлений. Не удаляй его.
    """
    result = zakupki_scraper.download_tender(reg_number, folder)

    if not result.get("ok"):
        return f"Ошибка: {result.get('error', 'Неизвестная ошибка')}"

    lines = [
        f"Закупка {reg_number} — документы скачаны в папку: {result['folder']}",
        f"Скачано файлов: {result['downloaded']}",
        "",
    ]

    # Группируем по категориям для наглядного вывода
    by_cat = {}
    for f in result["files"]:
        cat = f.get("category", "7_Прочее")
        by_cat.setdefault(cat, []).append(f)

    for cat in sorted(by_cat):
        lines.append(f"📁 {cat}/")
        for f in by_cat[cat]:
            size_kb = f["size_bytes"] // 1024
            lines.append(f"   • {f['filename']} ({size_kb} КБ)")

    if result["errors"] > 0:
        lines.append(f"\nНе удалось скачать: {result['errors']} файл(ов)")
        for e in result["error_list"]:
            lines.append(f"  ! {e['name']}: {e['error']}")

    lines.append(f"\nДля проверки обновлений: check_tender_updates('{folder}')")
    return "\n".join(lines)


@mcp.tool()
def check_tender_updates(folder: str) -> str:
    """
    Проверить, обновились ли документы закупки на zakupki.gov.ru.
    Файлы НЕ скачиваются — только сравнение с текущим состоянием сайта.

    Когда использовать:
    - Пользователь говорит "проверь актуальность документов"
    - Пользователь говорит "есть ли обновления по закупке"
    - Перед началом работы с документами (убедиться что они свежие)

    Параметры:
    - folder: путь к папке закупки (та же что использовалась в download_tender)
      В папке должен быть .tender_meta.json

    Если есть обновления — предложи пользователю выполнить update_tender.
    """
    result = zakupki_scraper.check_updates(folder)

    if not result.get("ok"):
        return f"Ошибка: {result.get('error', 'Неизвестная ошибка')}"

    if not result["has_updates"]:
        return (
            f"Закупка {result['reg_number']}: документы актуальны.\n"
            f"Без изменений: {result['unchanged_count']} файл(ов).\n"
            f"Проверено: {result['checked_at']}"
        )

    lines = [
        f"Закупка {result['reg_number']}: НАЙДЕНЫ ИЗМЕНЕНИЯ!",
        f"Проверено: {result['checked_at']}",
        "",
    ]

    if result["new"]:
        lines.append(f"Новые документы ({len(result['new'])}):")
        for d in result["new"]:
            lines.append(f"  + {d['name']}")

    if result["removed"]:
        lines.append(f"\nУбраны с сайта ({len(result['removed'])}):")
        for d in result["removed"]:
            lines.append(f"  - {d['filename']}")

    lines.append(f"\nБез изменений: {result['unchanged_count']} файл(ов)")
    lines.append(f"\nДля загрузки обновлений: update_tender('{folder}')")
    return "\n".join(lines)


@mcp.tool()
def update_tender(folder: str) -> str:
    """
    Скачать обновлённые документы закупки и создать лог изменений.

    Когда использовать:
    - После check_tender_updates сообщил что есть изменения
    - Пользователь говорит "обнови документы", "скачай новые версии"

    Параметры:
    - folder: путь к папке закупки (та же что использовалась в download_tender)

    После выполнения в папке появится файл _changes.md с описанием что изменилось.
    Старые версии файлов НЕ удаляются — остаются рядом для сравнения.
    """
    result = zakupki_scraper.update_tender(folder)

    if not result.get("ok"):
        return f"Ошибка: {result.get('error', 'Неизвестная ошибка')}"

    if "message" in result:
        return result["message"]

    lines = [
        f"Закупка {result['reg_number']} — обновление выполнено.",
        f"Скачано новых файлов: {result['new_downloaded']}",
    ]

    for f in result["files"]:
        size_kb = f["size_bytes"] // 1024
        lines.append(f"  + {f['filename']} ({size_kb} КБ)")

    if result["removed_on_site"] > 0:
        lines.append(f"Убрано с сайта: {result['removed_on_site']} файл(ов) (локальные копии сохранены)")

    if result["errors"] > 0:
        lines.append(f"Ошибок при скачивании: {result['errors']}")

    lines.append(f"\nЛог изменений: {result['changes_file']}")
    return "\n".join(lines)


if __name__ == "__main__":
    # Запуск сервера в режиме stdio (для Claude Desktop)
    mcp.run(transport="stdio")
