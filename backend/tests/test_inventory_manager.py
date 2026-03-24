import pytest

from src.inventory_manager import (
    convert_currency,
    currency_to_copper,
    get_weight_capacity,
    get_weight_penalty,
    normalize_currency,
    sum_inventory_weight,
)


def test_sum_inventory_weight_empty():
    assert sum_inventory_weight([], {}) == pytest.approx(0.0)


def test_sum_inventory_weight_with_known_items():
    inventory = [
        {"name": "Espada Básica", "quantity": 1},
        {"name": "Ração", "quantity": 3},
    ]
    catalog = {
        "espada basica": {"weight": 3.5},
        "racao": {"weight": 0.5},
    }
    assert sum_inventory_weight(inventory, catalog) == pytest.approx(5.0)


def test_sum_inventory_weight_unknown_item_uses_default():
    inventory = [{"name": "Item Desconhecido", "quantity": 2}]
    assert sum_inventory_weight(inventory, {}, unknown_item_weight=0.2) == pytest.approx(0.4)


def test_weight_capacity_formula():
    assert get_weight_capacity(10, 10) == pytest.approx(80.0)
    assert get_weight_capacity(14, 12) == pytest.approx(106.0)


def test_weight_penalty_none_below_80_percent():
    penalty = get_weight_penalty(current_weight=39.0, weight_capacity=50.0)
    assert penalty["state"] == "normal"
    assert penalty["penalty_percent"] == 0


def test_weight_penalty_slow_from_80_to_99_percent():
    penalty = get_weight_penalty(current_weight=85.0, weight_capacity=100.0)
    assert penalty["state"] == "encumbered"
    assert penalty["penalty_percent"] > 0


def test_weight_penalty_overloaded_from_100_to_119_percent():
    penalty = get_weight_penalty(current_weight=110.0, weight_capacity=100.0)
    assert penalty["state"] == "overloaded"
    assert penalty["penalty_percent"] >= 20


def test_weight_penalty_immobilized_at_120_percent_plus():
    penalty = get_weight_penalty(current_weight=120.0, weight_capacity=100.0)
    assert penalty["state"] == "immobilized"
    assert penalty["penalty_percent"] == 100


def test_currency_to_copper_and_back():
    wallet = {"copper": 50, "silver": 3, "gold": 2, "platinum": 1}
    total = currency_to_copper(wallet)
    assert total == 1020350

    normalized = normalize_currency(total)
    assert normalized == wallet


def test_convert_currency_100_to_1_rule():
    assert convert_currency(100, "copper", "silver") == 1
    assert convert_currency(100, "silver", "gold") == 1
    assert convert_currency(100, "gold", "platinum") == 1


def test_convert_currency_1_to_100_rule_reverse():
    assert convert_currency(1, "silver", "copper") == 100
    assert convert_currency(1, "gold", "silver") == 100
    assert convert_currency(1, "platinum", "gold") == 100
