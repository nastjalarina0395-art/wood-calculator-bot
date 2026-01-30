# bot.py
from __future__ import annotations

import os
import re
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from calc import (
    normalize_text,
    parse_size_to_mm,
    calc_wood_blank,
    calc_special,
    format_result,
    prices_text,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")  # токен берём из переменной окружения


# --- парсинг сообщений ---
# "амарант 300х200х50", "падук 60x60x20 см"
SIZE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*[xх×*]\s*(\d+(?:[.,]\d+)?)\s*[xх×*]\s*(\d+(?:[.,]\d+)?)(?:\s*(мм|см))?",
                     re.IGNORECASE)

# "E1 2" или "e2"
SPECIAL_RE = re.compile(r"^(e1|e2)\s*(\d+)?$", re.IGNORECASE)


def split_wood_and_size(text: str) -> tuple[str | None, str | None]:
    t = normalize_text(text)
    m = SIZE_RE.search(t)
    if not m:
        return None, None

    size_part = m.group(0)
    wood_part = t[:m.start()].strip()

    # иногда пишут "вуд амарант 300х..." — уберем служебные слова
    for prefix in ("вуд", "wood", "calc", "кальк"):
        if wood_part.startswith(prefix + " "):
            wood_part = wood_part[len(prefix) + 1 :].strip()

    return wood_part or None, size_part


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет 👋 Я калькулятор древесины.\n\n"
        "Напиши так:\n"
        "• `амарант 300х200х50`\n"
        "• `падук 60x60x20 см`\n\n"
        "Прайсы: /prices",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_prices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(prices_text(), parse_mode=ParseMode.MARKDOWN)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    if not text:
        return

    t = normalize_text(text)

    # 1) Эбен штучно: "E1 2"
    sm = SPECIAL_RE.match(t.replace(" ", ""))
    if sm:
        code = sm.group(1).upper()
        qty = int(sm.group(2)) if sm.group(2) else 1
        try:
            res = calc_special(code, qty)
            await update.message.reply_text(format_result(res), parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await update.message.reply_text(f"Ошибка: {e}")
        return

    # 2) Доска по размерам: "порода 300х200х50"
    wood_part, size_part = split_wood_and_size(t)
    if not size_part:
        await update.message.reply_text(
            "Я не вижу размер.\n\nПример:\n`амарант 300х200х50`\n`падук 60x60x20 см`\n\nПрайсы: /prices",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if not wood_part:
        await update.message.reply_text(
            "Я не вижу породу перед размером.\nПример: `амарант 300х200х50`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    try:
        L, W, H = parse_size_to_mm(size_part)
        res = calc_wood_blank(wood_part, L, W, H)
        await update.message.reply_text(format_result(res), parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")


def main() -> None:
    if not TOKEN:
        raise RuntimeError(
            "Не найден TELEGRAM_TOKEN.\n"
            "Сделай в терминале:\n"
            "export TELEGRAM_TOKEN='твой_токен'\n"
            "и запусти снова: python bot.py"
        )

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("prices", cmd_prices))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    app.run_polling()


if __name__ == "__main__":
    main()
