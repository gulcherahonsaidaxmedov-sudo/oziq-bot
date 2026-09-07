import asyncio
import json
import logging
import os

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    WebAppInfo,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

import config
import database

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher(storage=MemoryStorage())

STATUS_LABELS = {
    "new": "🆕 Yangi",
    "accepted": "⏳ Tayyorlanmoqda",
    "ready": "✅ Tayyor",
    "cancelled": "❌ Bekor qilingan",
}


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


def main_menu(user_id: int) -> ReplyKeyboardMarkup:
    rows = [
        [
            KeyboardButton(
                text="🛒 Do'kon",
                web_app=WebAppInfo(url=config.WEBAPP_URL),
            )
        ],
        [KeyboardButton(text="📜 Mening buyurtmalarim")],
    ]

    if is_admin(user_id):
        rows.append([KeyboardButton(text="⚙️ Admin panel")])

    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def admin_menu() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="➕ Mahsulot qo'shish")],
        [KeyboardButton(text="📋 Mahsulotlar ro'yxati")],
        [KeyboardButton(text="🗑 Mahsulotni o'chirish")],
        [KeyboardButton(text="📊 Buyurtmalar")],
        [KeyboardButton(text="📈 Statistika")],
        [KeyboardButton(text="📢 Xabar yuborish")],
        [KeyboardButton(text="⬅️ Orqaga")],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


class AddProduct(StatesGroup):
    name = State()
    price = State()
    category = State()
    description = State()
    image = State()


class DeleteProduct(StatesGroup):
    product_id = State()


class Onboarding(StatesGroup):
    phone = State()


class Broadcast(StatesGroup):
    text = State()


def phone_request_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Raqamni yuborish", request_contact=True)]
        ],
        resize_keyboard=True,
    )


# ==================== ASOSIY MENYU ====================

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    database.add_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
    )

    phone = database.get_user_phone(message.from_user.id)

    if not phone:
        await state.set_state(Onboarding.phone)
        await message.answer(
            "Assalomu alaykum! 👋\n"
            "Oziq-ovqat do'koniga xush kelibsiz.\n\n"
            "Davom etish uchun, iltimos, telefon raqamingizni yuboring:",
            reply_markup=phone_request_kb(),
        )
        return

    await state.clear()
    await message.answer(
        "Assalomu alaykum! 👋\n"
        "Oziq-ovqat do'koniga xush kelibsiz.\n"
        "Quyidagi tugmalardan foydalaning:",
        reply_markup=main_menu(message.from_user.id),
    )


@dp.message(Onboarding.phone, F.contact)
async def onboarding_phone_received(message: Message, state: FSMContext):
    # Faqat foydalanuvchining o'z kontaktini qabul qilamiz.
    if message.contact.user_id and message.contact.user_id != message.from_user.id:
        await message.answer(
            "Iltimos, o'zingizning telefon raqamingizni yuboring:",
            reply_markup=phone_request_kb(),
        )
        return

    database.set_user_phone(
        message.from_user.id,
        message.contact.phone_number,
    )
    await state.clear()

    await message.answer(
        "✅ Rahmat! Endi do'konimizdan foydalanishingiz mumkin.",
        reply_markup=main_menu(message.from_user.id),
    )


@dp.message(Onboarding.phone)
async def onboarding_phone_invalid(message: Message):
    await message.answer(
        'Iltimos, pastdagi "📱 Raqamni yuborish" tugmasi orqali yuboring:',
        reply_markup=phone_request_kb(),
    )


@dp.message(F.text == "⬅️ Orqaga")
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Bosh menyu:",
        reply_markup=main_menu(message.from_user.id),
    )


@dp.message(F.text == "📜 Mening buyurtmalarim")
async def my_orders(message: Message):
    orders = database.get_user_orders(message.from_user.id)

    if not orders:
        await message.answer("Sizda hali buyurtmalar yo'q.")
        return

    lines = []

    for order in orders:
        try:
            items = json.loads(order["items"])
        except Exception:
            items = []

        items_text = ", ".join(
            f"{item['name']} x{item['qty']}"
            for item in items
        )

        lines.append(
            f"№{order['daily_number']} — "
            f"{STATUS_LABELS.get(order['status'], order['status'])}\n"
            f"{items_text}\n"
            f"Jami: {order['total']} so'm"
        )

    await message.answer("\n\n".join(lines))


# ==================== ADMIN PANEL ====================

@dp.message(F.text == "⚙️ Admin panel")
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "Admin panel:",
        reply_markup=admin_menu(),
    )


@dp.message(F.text == "📋 Mahsulotlar ro'yxati")
async def list_products(message: Message):
    if not is_admin(message.from_user.id):
        return

    products = database.get_products(active_only=False)

    if not products:
        await message.answer("Mahsulotlar yo'q.")
        return

    lines = []

    for product in products:
        active = "✅" if product["active"] else "❌"
        category = product["category"] or "—"

        lines.append(
            f"{active} #{product['id']} "
            f"{product['name']} — {product['price']} so'm "
            f"({category})"
        )

    await message# ==================== MAHSULOT O'CHIRISH ====================

@dp.message(F.text == "🗑 Mahsulotni o'chirish")
async def delete_product_start(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    products = database.get_products(active_only=True)

    if not products:
        await message.answer("Mahsulotlar yo'q.")
        return

    lines = [
        f"#{product['id']} "
        f"{product['name']} — "
        f"{product['price']} so'm"
        for product in products
    ]

    await state.set_state(DeleteProduct.product_id)

    await message.answer(
        "O'chirmoqchi bo'lgan mahsulotning ID raqamini kiriting:\n\n"
        + "\n".join(lines),
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(DeleteProduct.product_id)
async def delete_product_confirm(
    message: Message,
    state: FSMContext,
):
    text = (message.text or "").strip()

    if not text.isdigit():
        await message.answer(
            "Iltimos, faqat ID raqamini kiriting:"
        )
        return

    product_id = int(text)
    product = database.get_product(product_id)

    if not product:
        await message.answer(
            "Bunday ID topilmadi. Qaytadan kiriting:"
        )
        return

    database.deactivate_product(product["id"])
    await state.clear()

    await message.answer(
        f"🗑 \"{product['name']}\" mahsulot ro'yxatdan o'chirildi.",
        reply_markup=admin_menu(),
    )


# ==================== XABAR YUBORISH ====================

@dp.message(F.text == "📢 Xabar yuborish")
async def broadcast_start(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    await state.set_state(Broadcast.text)

    await message.answer(
        "Barcha foydalanuvchilarga yuboriladigan xabarni kiriting:",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(Broadcast.text)
async def broadcast_send(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    text = (message.text or "").strip()

    if not text:
        await message.answer(
            "Xabar bo'sh bo'lmasligi kerak. Qaytadan kiriting:"
        )
        return

    await state.clear()

    user_ids = database.get_all_user_ids()
    sent = 0

    for user_id in user_ids:
        try:
            await bot.send_message(user_id, text)
            sent += 1
        except Exception:
            logging.exception(
                "Foydalanuvchiga xabar yuborilmadi: %s",
                user_id,
            )

    await message.answer(
        f"✅ Xabar {sent} foydalanuvchiga yuborildi.",
        reply_markup=admin_menu(),
    )


# ==================== BUYURTMA HOLATI ====================

@dp.callback_query(F.data.startswith("accept:"))
async def order_accept(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Ruxsat yo'q",
            show_alert=True,
        )
        return

    try:
        order_id = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer(
            "Noto'g'ri buyurtma ID.",
            show_alert=True,
        )
        return

    order = database.get_order(order_id)

    if not order:
        await callback.answer(
            "Buyurtma topilmadi.",
            show_alert=True,
        )
        return

    if order["status"] != "new":
        await callback.answer(
            "Bu buyurtma allaqachon ko'rib chiqilgan.",
            show_alert=True,
        )
        return

    database.update_order_status(
        order_id,
        "accepted",
    )

    order = database.get_order(order_id)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🍳 Tayyor deb belgilash",
                    callback_data=f"ready:{order_id}",
                )
            ]
        ]
    )

    current_text = callback.message.html_text or ""

    await callback.message.edit_text(
        current_text + "\n\n⏳ <b>Qabul qilindi.</b>",
        reply_markup=kb,
    )

    try:
        await bot.send_message(
            order["user_id"],
            f"⏳ Buyurtmangiz "
            f"(№{order['daily_number']}) "
            f"qabul qilindi va tayyorlanmoqda!",
        )
    except Exception:
        logging.exception(
            "Buyurtma qabul qilingani haqida foydalanuvchiga "
            "xabar yuborilmadi",
        )

    await callback.answer(
        "Buyurtma qabul qilindi.",
    )


@dp.callback_query(F.data.startswith("cancel:"))
async def order_cancel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Ruxsat yo'q",
            show_alert=True,
        )
        return

    try:
        order_id = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer(
            "Noto'g'ri buyurtma ID.",
            show_alert=True,
        )
        return

    order = database.get_order(order_id)

    if not order:
        await callback.answer(
            "Buyurtma topilmadi.",
            show_alert=True,
        )
        return

    if order["status"] in ("ready", "cancelled"):
        await callback.answer(
            "Bu buyurtma allaqachon yakunlangan.",
            show_alert=True,
        )
        return

    database.update_order_status(
        order_id,
        "cancelled",
    )

    order = database.get_order(order_id)

    current_text = callback.message.html_text or ""

    await callback.message.edit_text(
        current_text + "\n\n❌ <b>Bekor qilindi.</b>",
    )

    try:
        await bot.send_message(
            order["user_id"],
            f"❌ Afsuski, buyurtmangiz "
            f"(№{order['daily_number']}) bekor qilindi.",
        )
    except Exception:
        logging.exception(
            "Bekor qilingan buyurtma haqida "
            "foydalanuvchiga xabar yuborilmadi",
        )

    await callback.answer(
        "Buyurtma bekor qilindi.",
    )


@dp.callback_query(F.data.startswith("ready:"))
async def order_ready(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Ruxsat yo'q",
            show_alert=True,
        )
        return

    try:
        order_id = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer(
            "Noto'g'ri buyurtma ID.",
            show_alert=True,
        )
        return

    order = database.get_order(order_id)

    if not order:
        await callback.answer(
            "Buyurtma topilmadi.",
            show_alert=True,
        )
        return

    if order["status"] != "accepted":
        await callback.answer(
            "Bu buyurtma tayyorlanayotgan holatda emas.",
            show_alert=True,
        )
        return

    database.update_order_status(
        order_id,
        "ready",
    )

    order = database.get_order(order_id)

    current_text = callback.message.html_text or ""

    await callback.message.edit_text(
        current_text + "\n\n✅ <b>Tayyor!</b>",
    )

    try:
        await bot.send_message(
            order["user_id"],
            f"✅ Buyurtmangiz "
            f"(№{order['daily_number']}) tayyor!",
        )
    except Exception:
        logging.exception(
            "Tayyor buyurtma haqida "
            "foydalanuvchiga xabar yuborilmadi",
        )

    await callback.answer(
        "Buyurtma tayyor deb belgilandi.",
    )


# ==================== ADMIN YANGI BUYURTMA XABARI ====================

async def notify_admins_new_order(order_id: int):
    order = database.get_order(order_id)

    if not order:
        logging.error(
            "Yangi buyurtma topilmadi: %s",
            order_id,
        )
        return

    try:
        items = json.loads(order["items"])
    except Exception:
        items = []

    items_text = "\n".join(
        f"• {item['name']} x{item['qty']} — "
        f"{item['price'] * item['qty']} so'm"
        for item in items
    )

    phone = database.get_user_phone(
        order["user_id"]
    )

    text = (
        f"🆕 <b>Yangi buyurtma №{order['daily_number']}</b>\n"
        f"👤 {order['username'] or order['user_id']}\n"
        f"📱 {phone or 'Raqam yo‘q'}\n\n"
        f"{items_text}\n\n"
        f"💰 <b>Jami: {order['total']} so'm</b>"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Qabul qilish",
                    callback_data=f"accept:{order_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data=f"cancel:{order_id}",
                ),
            ]
        ]
    )

    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                text,
                reply_markup=kb,
            )
        except Exception:
            logging.exception(
                "Admin %s ga yangi buyurtma yuborilmadi",
                admin_id,
      )# ==================== WEB APP API ====================

async def handle_products(request: web.Request):
    try:
        products = database.get_products()
        return web.json_response(products)
    except Exception:
        logging.exception("Mahsulotlarni olishda xato")
        return web.json_response(
            {"error": "server_error"},
            status=500,
        )


async def handle_settings(request: web.Request):
    try:
        return web.json_response(
            {
                "background_url": database.get_setting(
                    "background_url",
                    "",
                )
            }
        )
    except Exception:
        logging.exception("Sozlamalarni olishda xato")
        return web.json_response(
            {"error": "server_error"},
            status=500,
        )


async def handle_order(request: web.Request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response(
            {"error": "invalid json"},
            status=400,
        )

    try:
        user_id = int(data.get("user_id", 0))
    except (TypeError, ValueError):
        user_id = 0

    items = data.get("items") or []

    if not user_id or not isinstance(items, list) or not items:
        return web.json_response(
            {"error": "invalid data"},
            status=400,
        )

    # Brauzerdan kelgan narxga ishonmaymiz.
    # Haqiqiy narxni bazadan olamiz.
    clean_items = []
    total = 0

    for item in items:
        try:
            product_id = int(item.get("id", 0))
            qty = int(item.get("qty", 0))
        except (TypeError, ValueError):
            continue

        if product_id <= 0 or qty <= 0:
            continue

        product = database.get_product(product_id)

        if not product:
            continue

        if not product["active"]:
            continue

        price = int(product["price"])

        clean_item = {
            "id": product["id"],
            "name": product["name"],
            "price": price,
            "qty": qty,
        }

        clean_items.append(clean_item)
        total += price * qty

    if not clean_items:
        return web.json_response(
            {"error": "products_not_found"},
            status=400,
        )

    username = data.get("username", "")

    if username is None:
        username = ""

    database.add_user(
        user_id,
        username,
        data.get("full_name", ""),
    )

    order_id = database.add_order(
        user_id,
        username,
        clean_items,
        total,
    )

    order = database.get_order(order_id)

    if not order:
        return web.json_response(
            {"error": "order_create_failed"},
            status=500,
        )

    await notify_admins_new_order(order_id)

    return web.json_response(
        {
            "order_id": order_id,
            "total": total,
            "daily_number": order["daily_number"],
        }
    )


async def handle_order_search(request: web.Request):
    try:
        user_id = int(
            request.query.get("user_id", 0)
        )
        daily_number = int(
            request.query.get("number", 0)
        )
    except (TypeError, ValueError):
        return web.json_response(
            {"error": "invalid data"},
            status=400,
        )

    if not user_id or not daily_number:
        return web.json_response(
            {"error": "invalid data"},
            status=400,
        )

    order = database.find_order_by_daily_number(
        user_id,
        daily_number,
    )

    if not order:
        return web.json_response(
            {"error": "not_found"},
            status=404,
        )

    try:
        items = json.loads(order["items"])
    except Exception:
        items = []

    return web.json_response(
        {
            "order_id": order["id"],
            "daily_number": order["daily_number"],
            "status": order["status"],
            "status_label": STATUS_LABELS.get(
                order["status"],
                order["status"],
            ),
            "total": order["total"],
            "items": items,
        }
    )


async def handle_webapp_index(request: web.Request):
    return web.FileResponse(
        "webapp/index.html"
    )


async def handle_root(request: web.Request):
    return web.json_response(
        {
            "status": "ok",
            "service": "telegram-shop-bot",
        }
    )


async def handle_health(request: web.Request):
    return web.json_response(
        {
            "status": "healthy",
        }
    )


def create_web_app() -> web.Application:
    app = web.Application()

    # Railway health/root
    app.router.add_get(
        "/",
        handle_root,
    )

    app.router.add_get(
        "/health",
        handle_health,
    )

    # API
    app.router.add_get(
        "/api/products",
        handle_products,
    )

    app.router.add_get(
        "/api/settings",
        handle_settings,
    )

    app.router.add_get(
        "/api/order/search",
        handle_order_search,
    )

    app.router.add_post(
        "/api/order",
        handle_order,
    )

    # WebApp
    app.router.add_get(
        "/webapp/",
        handle_webapp_index,
    )

    app.router.add_get(
        "/webapp/index.html",
        handle_webapp_index,
    )

    app.router.add_static(
        "/webapp/",
        path="webapp",
        name="webapp",
        show_index=False,
    )

    return app# ==================== WEB SERVER ====================

async def start_web_server():
    app = create_web_app()

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(config.PORT)

    site = web.TCPSite(
        runner,
        host="0.0.0.0",
        port=port,
    )

    await site.start()

    logging.info(
        "Web server ishga tushdi: port %s",
        port,
    )

    return runner


# ==================== BOTNI ISHGA TUSHIRISH ====================

async def main():
    database.init_db()

    runner = await start_web_server()

    try:
        logging.info("Bot ishga tushmoqda...")

        await bot.delete_webhook(
            drop_pending_updates=True,
        )

        await dp.start_polling(
            bot,
        )

    finally:
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot to'xtatildi.")
