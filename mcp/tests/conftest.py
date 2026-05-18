import json
import sys
from pathlib import Path

import pytest

MCP_DIR = Path(__file__).resolve().parents[1]
if str(MCP_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_DIR))

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def purchase_44() -> dict:
    return _load("purchase_44.json")


@pytest.fixture
def purchase_223() -> dict:
    return _load("purchase_223.json")


@pytest.fixture
def purchase_44_single() -> dict:
    """Реальная закупка 0318300008826000165 — ровно 1 позиция,
    purchaseObject приходит одиночным dict (EIS схлопывает
    одноэлементный массив). Регрессия бага 'str' object has no
    attribute 'get'."""
    return _load("purchase_44_single.json")


@pytest.fixture
def contract_44() -> dict:
    return _load("contract_44.json")


@pytest.fixture
def contract_44_procedures() -> list:
    return _load("contract_44_procedures.json")
