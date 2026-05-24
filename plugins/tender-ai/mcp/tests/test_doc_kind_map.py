from doc_kind_map import folder_for


def test_known_codes():
    assert folder_for("POD", "Описание объекта закупки") == "1_ТЗ"
    assert folder_for("CP", "Проект контракта") == "2_Контракт"
    assert folder_for("MRJ", "Обоснование НМЦК") == "3_НМЦК"
    assert folder_for("CAR", "Требование к составу заявки") == "5_Документация"
    assert folder_for("AD", "Дополнительная информация") == "7_Прочее"


def test_heuristic_by_name_when_code_unknown():
    assert folder_for("ZZZ", "Локальный сметный расчёт") == "4_Смета"
    assert folder_for("", "Протокол подведения итогов") == "6_Протоколы"
    assert folder_for(None, "Проект контракта на монтаж") == "2_Контракт"


def test_fallback_to_misc():
    assert folder_for("UNKNOWN", "невнятное название") == "7_Прочее"
