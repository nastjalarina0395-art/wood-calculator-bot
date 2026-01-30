# calc.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


MM3_IN_M3 = 1_000_000_000  # 1 м3 = 1e9 мм3


@dataclass(frozen=True)
class WoodPricing:
    name: str
    buy_per_m3: int
    sell_per_m3_big: int     # категория: "от 500x100x50"
    sell_per_m3_small: int   # категория: "до 500x100x50"


@dataclass(frozen=True)
class SpecialItem:
    key: str
    name: str
    size_mm: Tuple[int, int, int]
    buy_price_each: int
    sell_price_each: int


WOODS: Dict[str, WoodPricing] = {
    "падук": WoodPricing("Падук", 550_000, 1_575_000, 1_880_000),
    "зебрано": WoodPricing("Зебрано", 720_000, 1_800_000, 2_000_000),
    "венге": WoodPricing("Венге", 820_000, 2_050_000, 2_460_000),
    "амарант": WoodPricing("Амарант", 620_000, 1_550_000, 1_860_000),
    "бубинга": WoodPricing("Бубинга", 720_000, 1_800_000, 2_000_000),
    "лайсвуд": WoodPricing("Лайсвуд", 750_000, 1_875_000, 2_250_000),
    "мербау": WoodPricing("Мербау", 710_000, 1_775_000, 2_130_000),
    "тик": WoodPricing("Тик", 945_000, 2_362_000, 2_835_000),
    "палисандр": WoodPricing("Палисандр", 1_350_000, 3_000_000, 3_375_000),
    "сапеле": WoodPricing("Сапеле", 430_000, 1_075_000, 1_290_000),
    "термоясень": WoodPricing("Термоясень", 150_000, 375_000, 450_000),
}

ALIASES: Dict[str, str] = {
    "термо ясень": "термоясень",
    "термо-ясень": "термоясень",
    "лайс": "лайсвуд",
    "сапелле": "сапеле",
    "саппеле": "сапеле",
}

SPECIAL_ITEMS: Dict[str, SpecialItem] = {
    "E1": SpecialItem("E1", "Эбен чёрный (брусок)", (800, 40, 40), 7_000, 210_000),
    "E2": SpecialItem("E2", "Эбен макассар (брусок)", (350, 34, 34), 675, 3_000),
}


def normalize_text(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("×", "x").replace("х", "x").replace("*", "x")
    while "  " in s:
        s = s.replace("  ", " ")
    return s


def resolve_wood_key(raw: str) -> str | None:
    raw = normalize_text(raw)
    if raw in WOODS:
        return raw
    if raw in ALIASES:
        return ALIASES[raw]
    return None


def parse_size_to_mm(size_str: str) -> Tuple[int, int, int]:
    s = normalize_text(size_str)
    is_cm = "см" in s
    s = s.replace("мм", "").replace("см", "").strip()

    parts = [p.strip() for p in s.split("x") if p.strip()]
    if len(parts) != 3:
        raise ValueError("Размер должен быть в формате 300х200х50")

    try:
        l, w, h = float(parts[0]), float(parts[1]), float(parts[2])
    except ValueError as e:
        raise ValueError("В размере должны быть только числа") from e

    if is_cm:
        l, w, h = l * 10, w * 10, h * 10

    L, W, H = int(round(l)), int(round(w)), int(round(h))
    if L <= 0 or W <= 0 or H <= 0:
        raise ValueError("Размеры должны быть больше 0")
    return L, W, H


def volume_m3(L_mm: int, W_mm: int, H_mm: int) -> float:
    return (L_mm * W_mm * H_mm) / MM3_IN_M3


def tier_for_size(L_mm: int, W_mm: int, H_mm: int) -> str:
    if (L_mm < 500) and (W_mm < 100) and (H_mm < 50):
        return "до 500x100x50"
    return "от 500x100x50"


def calc_wood_blank(wood_key: str, L_mm: int, W_mm: int, H_mm: int) -> dict:
    wood_key = resolve_wood_key(wood_key) or ""
    if wood_key not in WOODS:
        raise ValueError("Не знаю такую породу. Напиши /prices чтобы увидеть список.")
    w = WOODS[wood_key]

    v = volume_m3(L_mm, W_mm, H_mm)
    tier = tier_for_size(L_mm, W_mm, H_mm)

    sell_per_m3 = w.sell_per_m3_big if tier.startswith("от") else w.sell_per_m3_small
    cost = w.buy_per_m3 * v
    revenue = sell_per_m3 * v
    margin = revenue - cost

    return {
        "type": "wood_blank",
        "wood_key": wood_key,
        "name": w.name,
        "size_mm": (L_mm, W_mm, H_mm),
        "tier": tier,
        "volume_m3": v,
        "buy_per_m3": w.buy_per_m3,
        "sell_per_m3": sell_per_m3,
        "cost": cost,
        "revenue": revenue,
        "margin": margin,
    }


def calc_special(item_code: str, qty: int = 1) -> dict:
    code = (item_code or "").strip().upper()
    if code not in SPECIAL_ITEMS:
        raise ValueError("Не знаю этот код. Доступно: E1, E2")
    if qty <= 0:
        raise ValueError("Количество должно быть больше 0")

    it = SPECIAL_ITEMS[code]
    cost = it.buy_price_each * qty
    revenue = it.sell_price_each * qty
    margin = revenue - cost

    return {
        "type": "special",
        "code": code,
        "name": it.name,
        "size_mm": it.size_mm,
        "qty": qty,
        "buy_each": it.buy_price_each,
        "sell_each": it.sell_price_each,
        "cost": cost,
        "revenue": revenue,
        "margin": margin,
    }


def format_rub(x: float) -> str:
    r = int(round(x))
    return f"{r:,}".replace(",", " ") + " ₽"


def format_result(res: dict) -> str:
    if res["type"] == "wood_blank":
        L, W, H = res["size_mm"]
        return "\n".join([
            f"🪵 *{res['name']}*",
            f"📏 Размер: `{L}×{W}×{H} мм`",
            f"🏷 Категория: *{res['tier']}*",
            f"🧊 Объём: `{res['volume_m3']:.6f} м³`",
            "",
            f"💰 Продажа: *{format_rub(res['revenue'])}*",
            f"🧾 Себестоимость: {format_rub(res['cost'])}",
            f"📈 Маржа: *{format_rub(res['margin'])}*",
            "",
            f"Цена продажи за м³: `{format_rub(res['sell_per_m3'])}`",
            f"Закупка за м³: `{format_rub(res['buy_per_m3'])}`",
        ])

    if res["type"] == "special":
        L, W, H = res["size_mm"]
        return "\n".join([
            f"🧱 *{res['name']}* ({res['code']})",
            f"📏 Размер: `{L}×{W}×{H} мм`",
            f"🔢 Кол-во: `{res['qty']} шт`",
            "",
            f"💰 Продажа: *{format_rub(res['revenue'])}*",
            f"🧾 Себестоимость: {format_rub(res['cost'])}",
            f"📈 Маржа: *{format_rub(res['margin'])}*",
            "",
            f"Цена продажи за шт: `{format_rub(res['sell_each'])}`",
            f"Закупка за шт: `{format_rub(res['buy_each'])}`",
        ])

    return "Неизвестный результат расчёта"


def prices_text() -> str:
    lines = ["📌 *Прайсы (м³)*", "", "Формат: `порода 300х200х50`", ""]
    for _, w in WOODS.items():
        lines.append(
            f"• *{w.name}* — закуп `{format_rub(w.buy_per_m3)}` | "
            f"от `{format_rub(w.sell_per_m3_big)}` | до `{format_rub(w.sell_per_m3_small)}`"
        )
    lines += [
        "",
        "📌 *Эбен (штучно)*",
        f"• *E1* — {SPECIAL_ITEMS['E1'].name} — продажа `{format_rub(SPECIAL_ITEMS['E1'].sell_price_each)}`",
        f"• *E2* — {SPECIAL_ITEMS['E2'].name} — продажа `{format_rub(SPECIAL_ITEMS['E2'].sell_price_each)}`",
    ]
    return "\n".join(lines)

