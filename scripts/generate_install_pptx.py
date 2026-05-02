"""
Генерирует презентацию «Установка Tender AI Tools» в формате .pptx.

Использование:
    python scripts/generate_install_pptx.py
    python scripts/generate_install_pptx.py --output "Установка.pptx"
"""

import argparse
from pathlib import Path
from datetime import datetime

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
from pptx.oxml.ns import qn
from lxml import etree


# ── палитра ────────────────────────────────────────────────────────────────
BLUE       = RGBColor(0x1F, 0x63, 0xB5)
BLUE_LIGHT = RGBColor(0xD9, 0xE4, 0xF5)
BLUE_MED   = RGBColor(0x5B, 0x9B, 0xD5)
WHITE      = RGBColor(0xFF, 0xFF, 0xFF)
DARK       = RGBColor(0x1A, 0x1A, 0x2E)
GRAY       = RGBColor(0x55, 0x55, 0x55)
GRAY_LIGHT = RGBColor(0xF4, 0xF4, 0xF4)
YELLOW_BG  = RGBColor(0xFF, 0xF8, 0xE1)
YELLOW_ACC = RGBColor(0xF5, 0x7F, 0x17)
RED_BG     = RGBColor(0xFD, 0xE8, 0xE8)
RED_ACC    = RGBColor(0xB7, 0x1C, 0x1C)
GREEN      = RGBColor(0x2E, 0x7D, 0x32)

# ── размер слайда 16:9 ─────────────────────────────────────────────────────
W = Inches(13.33)
H = Inches(7.5)


def new_prs() -> Presentation:
    prs = Presentation()
    prs.slide_width  = W
    prs.slide_height = H
    return prs


def blank_slide(prs: Presentation):
    layout = prs.slide_layouts[6]   # полностью пустой
    return prs.slides.add_slide(layout)


# ── низкоуровневые хелперы ─────────────────────────────────────────────────

def add_rect(slide, left, top, width, height, fill_color, *, alpha=None):
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        left, top, width, height
    )
    shape.line.fill.background()        # нет рамки
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    return shape


def add_textbox(slide, left, top, width, height, text, *,
                font_size=18, bold=False, color=WHITE,
                align=PP_ALIGN.LEFT, font_name="Calibri",
                wrap=True, italic=False):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.name  = font_name
    run.font.size  = Pt(font_size)
    run.font.bold  = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return txBox


def add_para(tf, text, *, font_size=16, bold=False, italic=False,
             color=DARK, bullet=False, indent=0, font_name="Calibri",
             space_before=0, space_after=2):
    p = tf.add_paragraph()
    p.alignment = PP_ALIGN.LEFT
    p.space_before = Pt(space_before)
    p.space_after  = Pt(space_after)
    if bullet:
        p.level = indent
    run = p.add_run()
    run.text = text
    run.font.name   = font_name
    run.font.size   = Pt(font_size)
    run.font.bold   = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return p


def code_box(slide, left, top, width, text, *, font_size=13):
    """Серый блок с моноширинным текстом (команда терминала)."""
    height = Inches(0.42)
    add_rect(slide, left, top, width, height, GRAY_LIGHT)
    tb = slide.shapes.add_textbox(
        left + Inches(0.12), top + Inches(0.05),
        width - Inches(0.24), height - Inches(0.1)
    )
    tf = tb.text_frame
    tf.word_wrap = False
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = text
    run.font.name  = "Courier New"
    run.font.size  = Pt(font_size)
    run.font.bold  = True
    run.font.color.rgb = DARK
    return tb


def tip_box(slide, left, top, width, text, *, bg=YELLOW_BG, acc=YELLOW_ACC,
            label=">> Совет", font_size=13):
    height = Inches(0.65)
    add_rect(slide, left, top, width, height, bg)
    tb = slide.shapes.add_textbox(
        left + Inches(0.12), top + Inches(0.06),
        width - Inches(0.24), height - Inches(0.12)
    )
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    r1 = p.add_run()
    r1.text = label + "  "
    r1.font.bold  = True
    r1.font.size  = Pt(font_size)
    r1.font.color.rgb = acc
    r2 = p.add_run()
    r2.text = text
    r2.font.size  = Pt(font_size)
    r2.font.color.rgb = DARK
    return tb


def warn_box(slide, left, top, width, text, *, font_size=13):
    return tip_box(slide, left, top, width, text,
                   bg=RED_BG, acc=RED_ACC, label="(!) Важно", font_size=font_size)


def header_bar(slide, title, step_num=None, step_total=6):
    """Синяя полоса сверху с заголовком шага."""
    add_rect(slide, 0, 0, W, Inches(1.2), BLUE)
    if step_num:
        badge_w = Inches(1.0)
        badge_h = Inches(0.7)
        bx = Inches(0.3)
        by = Inches(0.25)
        add_rect(slide, bx, by, badge_w, badge_h, WHITE)
        add_textbox(slide, bx, by, badge_w, badge_h,
                    f"{step_num}/{step_total}",
                    font_size=22, bold=True, color=BLUE, align=PP_ALIGN.CENTER)
        title_left = Inches(1.5)
    else:
        title_left = Inches(0.4)

    add_textbox(slide, title_left, Inches(0.22), W - title_left - Inches(0.3),
                Inches(0.8), title,
                font_size=28, bold=True, color=WHITE)


def progress_dots(slide, current, total=6):
    """Точки прогресса внизу слайда."""
    dot_r  = Inches(0.09)
    spacing = Inches(0.22)
    total_w = total * dot_r + (total - 1) * (spacing - dot_r)
    start_x = (W - total_w) / 2
    y = H - Inches(0.28)
    for i in range(total):
        color = WHITE if i + 1 == current else BLUE_MED
        add_rect(slide, start_x + i * spacing, y, dot_r, dot_r, color)


# ── слайды ─────────────────────────────────────────────────────────────────

def slide_title(prs):
    sl = blank_slide(prs)
    # фон — две полосы
    add_rect(sl, 0, 0, W, H, BLUE)
    add_rect(sl, 0, H * 0.62, W, H * 0.38, RGBColor(0x16, 0x4F, 0x96))

    # лого-блок
    add_rect(sl, Inches(0.5), Inches(0.5), Inches(0.08), Inches(1.4),
             RGBColor(0xFF, 0xC1, 0x07))

    add_textbox(sl, Inches(0.8), Inches(0.5), W - Inches(1.0), Inches(1.2),
                "Tender AI Tools",
                font_size=52, bold=True, color=WHITE)
    add_textbox(sl, Inches(0.8), Inches(1.8), W - Inches(1.0), Inches(0.8),
                "Руководство по установке",
                font_size=28, color=BLUE_LIGHT)
    add_textbox(sl, Inches(0.8), Inches(2.6), W - Inches(1.0), Inches(0.5),
                "AI-ассистент для участия в госзакупках по 44-ФЗ",
                font_size=18, color=BLUE_LIGHT, italic=True)

    today = datetime.now().strftime("%d.%m.%Y")
    add_textbox(sl, Inches(0.8), H - Inches(1.1), Inches(4), Inches(0.5),
                today, font_size=16, color=BLUE_LIGHT)


def slide_whats_inside(prs):
    sl = blank_slide(prs)
    add_rect(sl, 0, 0, W, H, RGBColor(0xF7, 0xF9, 0xFF))
    header_bar(sl, "Что в архиве")

    items = [
        ("skills/",  BLUE,  "4 zip-архива скиллов для загрузки в Cowork"),
        ("mcp/",     GREEN, "MCP-сервер для скачивания документов с ЕИС"),
        ("README.md",GRAY,  "Краткий обзор проекта"),
        ("Установка Tender AI Tools.pptx", RGBColor(0x8B,0x00,0x8B),
         "Этот файл — инструкция по установке"),
    ]

    col_w  = Inches(5.8)
    left1  = Inches(0.5)
    left2  = Inches(6.9)

    for i, (name, color, desc) in enumerate(items):
        row = i // 2
        col = i % 2
        x = left1 if col == 0 else left2
        y = Inches(1.5) + row * Inches(2.3)

        card = add_rect(sl, x, y, col_w, Inches(1.9), WHITE)
        add_rect(sl, x, y, Inches(0.12), Inches(1.9), color)

        tb = slide.shapes.add_textbox(x + Inches(0.25), y + Inches(0.15),
                                       col_w - Inches(0.35), Inches(0.55)) \
            if False else \
            sl.shapes.add_textbox(x + Inches(0.25), y + Inches(0.15),
                                  col_w - Inches(0.35), Inches(0.55))
        tf = tb.text_frame
        tf.word_wrap = False
        r = tf.paragraphs[0].add_run()
        r.text = name
        r.font.name  = "Courier New"
        r.font.size  = Pt(18)
        r.font.bold  = True
        r.font.color.rgb = color

        tb2 = sl.shapes.add_textbox(x + Inches(0.25), y + Inches(0.8),
                                     col_w - Inches(0.35), Inches(0.8))
        tf2 = tb2.text_frame
        tf2.word_wrap = True
        r2 = tf2.paragraphs[0].add_run()
        r2.text = desc
        r2.font.size  = Pt(15)
        r2.font.color.rgb = GRAY


def slide_requirements(prs):
    sl = blank_slide(prs)
    add_rect(sl, 0, 0, W, H, RGBColor(0xF7, 0xF9, 0xFF))
    header_bar(sl, "Что нужно установить заранее")

    reqs = [
        ("Python 3.10+",
         "python.org → Downloads → Python 3.x.x\nОбязательно: галочка «Add Python to PATH»",
         BLUE),
        ("Claude Code",
         "Десктоп-приложение Anthropic\nПолучи ссылку у своего партнёра",
         RGBColor(0xD4, 0x80, 0x00)),
        ("Аккаунт Cowork",
         "Платформа для скиллов\nПопроси приглашение у партнёра",
         GREEN),
    ]

    card_w = Inches(3.9)
    gap    = Inches(0.3)
    start_x = Inches(0.5)
    top    = Inches(1.45)
    card_h = Inches(4.8)

    for i, (title, body, color) in enumerate(reqs):
        x = start_x + i * (card_w + gap)
        add_rect(sl, x, top, card_w, card_h, WHITE)
        add_rect(sl, x, top, card_w, Inches(0.55), color)

        tb_t = sl.shapes.add_textbox(x + Inches(0.12), top + Inches(0.07),
                                      card_w - Inches(0.24), Inches(0.42))
        r = tb_t.text_frame.paragraphs[0].add_run()
        r.text = title
        r.font.size  = Pt(15)
        r.font.bold  = True
        r.font.color.rgb = WHITE

        tb_b = sl.shapes.add_textbox(x + Inches(0.12), top + Inches(0.7),
                                      card_w - Inches(0.24), card_h - Inches(0.85))
        tf = tb_b.text_frame
        tf.word_wrap = True
        for line in body.split("\n"):
            p = tf.paragraphs[0] if line == body.split("\n")[0] \
                else tf.add_paragraph()
            r = p.add_run()
            r.text = line
            r.font.size  = Pt(13.5)
            r.font.color.rgb = DARK


def slide_step(prs, step_num, title, content_fn):
    sl = blank_slide(prs)
    add_rect(sl, 0, 0, W, H, RGBColor(0xF7, 0xF9, 0xFF))
    header_bar(sl, title, step_num=step_num)
    progress_dots(sl, step_num)
    content_fn(sl)


def content_step1(sl):
    """Установить Python."""
    steps = [
        "Перейди на python.org → Downloads → скачай Python 3.x",
        'Запусти установщик (.exe)',
        'ОБЯЗАТЕЛЬНО поставь галочку "Add Python 3.x to PATH"',
        'Нажми "Install Now" — дождись окончания',
    ]
    y = Inches(1.4)
    for i, s in enumerate(steps, 1):
        add_rect(sl, Inches(0.5), y, Inches(0.55), Inches(0.55),
                 BLUE)
        tb = sl.shapes.add_textbox(Inches(0.5), y, Inches(0.55), Inches(0.55))
        r = tb.text_frame.paragraphs[0].add_run()
        r.text = str(i)
        r.font.size = Pt(20)
        r.font.bold = True
        r.font.color.rgb = WHITE
        tb.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

        add_textbox(sl, Inches(1.2), y + Inches(0.07),
                    Inches(8.5), Inches(0.5),
                    s, font_size=16, color=DARK)
        y += Inches(0.85)

    tip_box(sl, Inches(0.5), Inches(5.1), Inches(9.5),
            "Если пункт PATH не отмечен — команды python и pip не будут работать в терминале. "
            "В этом случае переустанови Python заново с этой галочкой.")

    add_textbox(sl, Inches(0.5), Inches(5.95), Inches(4), Inches(0.35),
                "Проверка — открой cmd (Win+R → cmd) и введи:",
                font_size=13, color=GRAY)
    code_box(sl, Inches(0.5), Inches(6.4), Inches(5),
             "python --version")


def content_step2(sl):
    """Распаковать архив."""
    add_textbox(sl, Inches(0.5), Inches(1.45), Inches(12),
                Inches(0.5),
                "Распакуй файл  tender-ai-tools.zip  в любое удобное место.",
                font_size=17, color=DARK)

    tip_box(sl, Inches(0.5), Inches(2.1), Inches(12.3),
            "Рекомендуем:  C:\\ClaudeCode\\  — путь без пробелов и кириллицы. "
            "С такими путями команды в терминале работают надёжнее.")

    add_textbox(sl, Inches(0.5), Inches(3.1), Inches(12),
                Inches(0.4),
                "После распаковки должна появиться папка:",
                font_size=15, color=GRAY)
    code_box(sl, Inches(0.5), Inches(3.6), Inches(7),
             "C:\\ClaudeCode\\tender-ai-tools\\")

    add_textbox(sl, Inches(0.5), Inches(4.25), Inches(12),
                Inches(0.4),
                "Внутри — три объекта:",
                font_size=15, color=GRAY)

    items = [
        ("skills/",     "zip-архивы скиллов для Cowork"),
        ("mcp/",        "MCP-сервер для скачивания с ЕИС"),
        ("README.md",   "краткий обзор проекта"),
    ]
    y = Inches(4.85)
    for folder, desc in items:
        tb = sl.shapes.add_textbox(Inches(0.7), y, Inches(10), Inches(0.4))
        tf = tb.text_frame
        tf.word_wrap = False
        p = tf.paragraphs[0]
        r1 = p.add_run()
        r1.text = folder + "  "
        r1.font.name  = "Courier New"
        r1.font.size  = Pt(14)
        r1.font.bold  = True
        r1.font.color.rgb = BLUE
        r2 = p.add_run()
        r2.text = "— " + desc
        r2.font.size  = Pt(14)
        r2.font.color.rgb = GRAY
        y += Inches(0.42)


def content_step3(sl):
    """Установить зависимости."""
    add_textbox(sl, Inches(0.5), Inches(1.42), Inches(12),
                Inches(0.42),
                "Открой Терминал: нажми  Win+R,  введи  cmd,  нажми  Enter.",
                font_size=17, color=DARK)

    add_textbox(sl, Inches(0.5), Inches(2.05), Inches(12),
                Inches(0.38),
                "Выполни по очереди три команды (вставь каждую и нажми Enter):",
                font_size=15, color=GRAY)

    cmds = [
        ("cd C:\\ClaudeCode\\tender-ai-tools\\mcp",
         "перейти в папку MCP"),
        ("pip install -r requirements.txt",
         "установить зависимости MCP-сервера"),
        ("pip install python-docx",
         "установить библиотеку для Word-файлов"),
    ]
    y = Inches(2.62)
    for cmd, hint in cmds:
        code_box(sl, Inches(0.5), y, Inches(9.5), cmd)
        add_textbox(sl, Inches(10.1), y + Inches(0.06), Inches(3.1),
                    Inches(0.35), hint,
                    font_size=12, color=GRAY, italic=True)
        y += Inches(0.72)

    warn_box(sl, Inches(0.5), Inches(5.1), Inches(12.3),
             'Ошибка "Access denied" — запусти cmd от имени администратора '
             '(правая кнопка на cmd → «Запустить от имени администратора»).')


def content_step4(sl):
    """Подключить MCP к Claude Code."""
    add_textbox(sl, Inches(0.5), Inches(1.42), Inches(12),
                Inches(0.42),
                "MCP-сервер скачивает документы напрямую с zakupki.gov.ru — бесплатно, без ключей.",
                font_size=15, italic=True, color=GRAY)

    add_textbox(sl, Inches(0.5), Inches(1.95), Inches(12),
                Inches(0.42),
                "Открой Claude Code → Настройки (⚙) → MCP Servers → Add server",
                font_size=17, color=DARK)

    # таблица настроек
    rows = [
        ("Name",    "zakupki-eis"),
        ("Type",    "stdio"),
        ("Command", "python"),
        ("Args",    "C:\\ClaudeCode\\tender-ai-tools\\mcp\\server.py"),
    ]
    col_w1 = Inches(2.0)
    col_w2 = Inches(8.5)
    x1 = Inches(0.5)
    x2 = x1 + col_w1 + Inches(0.05)
    row_h = Inches(0.48)
    y = Inches(2.65)

    add_rect(sl, x1, y, col_w1, row_h, BLUE)
    add_rect(sl, x2, y, col_w2, row_h, BLUE)
    for lbl, val in [("Поле", "Значение")]:
        add_textbox(sl, x1 + Inches(0.1), y + Inches(0.08),
                    col_w1, row_h, lbl,
                    font_size=14, bold=True, color=WHITE)
        add_textbox(sl, x2 + Inches(0.1), y + Inches(0.08),
                    col_w2, row_h, val,
                    font_size=14, bold=True, color=WHITE)
    y += row_h

    for i, (field, val) in enumerate(rows):
        bg = RGBColor(0xEB, 0xF2, 0xFB) if i % 2 == 0 else WHITE
        add_rect(sl, x1, y, col_w1, row_h, bg)
        add_rect(sl, x2, y, col_w2, row_h, bg)
        add_textbox(sl, x1 + Inches(0.1), y + Inches(0.1),
                    col_w1, row_h, field, font_size=14, bold=True, color=DARK)
        tb = sl.shapes.add_textbox(x2 + Inches(0.1), y + Inches(0.1),
                                    col_w2 - Inches(0.2), row_h)
        r = tb.text_frame.paragraphs[0].add_run()
        r.text = val
        r.font.name  = "Courier New"
        r.font.size  = Pt(14)
        r.font.color.rgb = BLUE
        y += row_h

    add_textbox(sl, Inches(0.5), Inches(5.65), Inches(12),
                Inches(0.4),
                "Сохрани → перезапусти Claude Code → создай новый чат и напечатай:",
                font_size=14, color=GRAY)
    code_box(sl, Inches(0.5), Inches(6.1), Inches(5), "@zakupki-eis")
    add_textbox(sl, Inches(5.7), Inches(6.17), Inches(7),
                Inches(0.35),
                "— должен появиться список инструментов",
                font_size=13, italic=True, color=GRAY)


def content_step5(sl):
    """Установить скиллы в Cowork."""
    add_textbox(sl, Inches(0.5), Inches(1.42), Inches(12),
                Inches(0.42),
                "В папке  skills/  лежат 4 zip-файла. Каждый загружается отдельно.",
                font_size=17, color=DARK)

    skills = [
        ("verdikt-zakupki",      "'берёмся / не берёмся'",     BLUE),
        ("scan-zakupki",         "анализ ТЗ и смет",            GREEN),
        ("zhaloba-fas",          "жалобы в УФАС / защита РНП",  RED_ACC),
        ("zapros-razyasneniy",   "запрос разъяснений + Word",   RGBColor(0x6A,0x1B,0x9A)),
    ]
    card_w = Inches(2.9)
    gap    = Inches(0.22)
    y = Inches(2.15)
    card_h = Inches(1.9)

    for i, (name, desc, color) in enumerate(skills):
        x = Inches(0.4) + i * (card_w + gap)
        add_rect(sl, x, y, card_w, card_h, WHITE)
        add_rect(sl, x, y, card_w, Inches(0.08), color)

        tb1 = sl.shapes.add_textbox(x + Inches(0.12), y + Inches(0.2),
                                     card_w - Inches(0.24), Inches(0.55))
        r = tb1.text_frame.paragraphs[0].add_run()
        r.text = name
        r.font.name  = "Courier New"
        r.font.size  = Pt(13)
        r.font.bold  = True
        r.font.color.rgb = color

        tb2 = sl.shapes.add_textbox(x + Inches(0.12), y + Inches(0.85),
                                     card_w - Inches(0.24), Inches(0.8))
        r2 = tb2.text_frame.paragraphs[0].add_run()
        r2.text = desc
        r2.font.size  = Pt(13)
        r2.font.color.rgb = GRAY

    steps_y = Inches(4.35)
    add_textbox(sl, Inches(0.5), steps_y, Inches(12),
                Inches(0.38),
                "Для каждого zip: открой Cowork → Skills → Upload → выбери файл → статус Active",
                font_size=15, color=DARK)

    warn_box(sl, Inches(0.5), Inches(5.05), Inches(12.3),
             "Загружай именно zip-файл целиком, не распакованную папку. "
             "Cowork ожидает архив.")


def content_step6(sl):
    """Проверить работу."""
    add_textbox(sl, Inches(0.5), Inches(1.42), Inches(12),
                Inches(0.42),
                "Создай новый чат в Claude Code, прикрепи документ из закупки и напиши:",
                font_size=17, color=DARK)

    code_box(sl, Inches(0.5), Inches(2.1), Inches(8), "оцени закупку")

    add_textbox(sl, Inches(0.5), Inches(2.75), Inches(12),
                Inches(0.42),
                "ИИ запустит скилл verdikt-zakupki и выдаст отчёт «берёмся / не берёмся».",
                font_size=15, italic=True, color=GRAY)

    add_textbox(sl, Inches(0.5), Inches(3.4), Inches(12),
                Inches(0.38),
                "Другие команды:",
                font_size=15, bold=True, color=DARK)

    cmds = [
        ("составь жалобу",             "→ жалоба в УФАС или защита от РНП"),
        ("сделай запрос разъяснений",  "→ Word-файл запроса на разъяснение"),
    ]
    y = Inches(3.95)
    for cmd, hint in cmds:
        code_box(sl, Inches(0.5), y, Inches(6.0), cmd)
        add_textbox(sl, Inches(6.6), y + Inches(0.07), Inches(6.5),
                    Inches(0.35), hint,
                    font_size=14, italic=True, color=GRAY)
        y += Inches(0.65)

    tip_box(sl, Inches(0.5), Inches(5.45), Inches(12.3),
            "Скилл не запустился? Убедись, что он в статусе Active в Cowork "
            "и что файл был загружен как zip-архив.")

    add_textbox(sl, Inches(0.5), H - Inches(0.6), Inches(12),
                Inches(0.38),
                "Готово! Если что-то не работает — напиши своему партнёру.",
                font_size=14, bold=True, color=BLUE, align=PP_ALIGN.CENTER)


# ── финальный слайд ────────────────────────────────────────────────────────

def slide_done(prs):
    sl = blank_slide(prs)
    add_rect(sl, 0, 0, W, H, BLUE)
    add_rect(sl, 0, H * 0.7, W, H * 0.3, RGBColor(0x16, 0x4F, 0x96))

    add_textbox(sl, 0, Inches(2.0), W, Inches(1.4),
                "Всё готово!",
                font_size=60, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    add_textbox(sl, 0, Inches(3.6), W, Inches(0.8),
                "Если что-то не получилось — напиши своему партнёру.",
                font_size=22, color=BLUE_LIGHT, align=PP_ALIGN.CENTER)
    add_textbox(sl, 0, H - Inches(1.0), W, Inches(0.5),
                "Tender AI Tools  •  " + datetime.now().strftime("%d.%m.%Y"),
                font_size=14, color=BLUE_MED, align=PP_ALIGN.CENTER)


# ── сборка ─────────────────────────────────────────────────────────────────

def generate(output_path: Path):
    prs = new_prs()

    slide_title(prs)
    slide_whats_inside(prs)
    slide_requirements(prs)
    slide_step(prs, 1, "Шаг 1 — Установить Python",          content_step1)
    slide_step(prs, 2, "Шаг 2 — Распаковать архив",          content_step2)
    slide_step(prs, 3, "Шаг 3 — Установить зависимости",     content_step3)
    slide_step(prs, 4, "Шаг 4 — Подключить MCP к Claude",    content_step4)
    slide_step(prs, 5, "Шаг 5 — Установить скиллы в Cowork", content_step5)
    slide_step(prs, 6, "Шаг 6 — Проверить работу",           content_step6)
    slide_done(prs)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))
    size_kb = output_path.stat().st_size // 1024
    print(f"OK: {output_path}  ({size_kb} KB, {len(prs.slides)} слайдов)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", "-o", type=Path,
                        default=Path("Установка Tender AI Tools.pptx"))
    args = parser.parse_args()
    generate(args.output)


if __name__ == "__main__":
    main()
