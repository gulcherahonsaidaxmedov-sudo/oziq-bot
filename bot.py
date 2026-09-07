import asyncio
import json
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery, WebAppInfo,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

import config
import database

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
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
        [KeyboardButton(text="🛒 Do'kon", web_app=WebAppInfo(url=config.WEBAPP_URL))],
        [KeyboardButton(text="📜 Mening buyurtmalarim")],
    ]
    if is_admin(user_id):
        rows.append([KeyboardButton(text="⚙️ Admin panel")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def admin_menu() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="➕ Mahsulot qo'shish")],
        [KeyboardButton(text="📋 Mahsulotlar ro'yxati")],
        [KeyboardButton(text="📊 Buyurtmalar")],
        [KeyboardButton(text="📢 Xabar yuborish")],
        [KeyboardButton(text="⬅️ Orqaga")],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


class AddProduct(StatesGroup):
    name = State()
    price = State()
    category = State()
    description = State()


class Broadcast(StatesGroup):
    text = State()


# ---------- Asosiy menyu ----------

@dp.message(CommandStart())
async def cmd_start(message: Message):
    database.add_user(message.from_user.id)
    await message.answer(
        "Assalomu alaykum! 👋\nOziq-ovqat do'koniga xush kelibsiz.\n"
        "Quyidagi tugmalardan foydalaning:",
        reply_markup=main_menu(message.from_user.id),
    )


@dp.message(F.text == "⬅️ Orqaga")
async def back_to_main(message: Message):
    await message.answer("Bosh menyu:", reply_markup=main_menu(message.from_user.id))


@dp.message(F.text == "📜 Mening buyurtmalarim")
async def my_orders(message: Message):
    orders = database.get_user_orders(message.from_user.id)
    if not orders:
        await message.answer("Sizda hali buyurtmalar yo'q.")
        return
    lines = []
    for o in orders:
        items = json.loads(o["items"])
        items_text = ", ".join(f"{i['name']} x{i['qty']}" for i in items)
        lines.append(
            f"#{o['id']} — {STATUS_LABELS.get(o['status'], o['status'])}\n"
            f"{items_text}\nJami: {o['total']} so'm"
        )
    await message.answer("\n\n".join(lines))


# ---------- Admin panel ----------

@dp.message(F.text == "⚙️ Admin panel")
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Admin panel:", reply_markup=admin_menu())


@dp.message(F.text == "📋 Mahsulotlar ro'yxati")
async def list_products(message: Message):
    if not is_admin(message.from_user.id):
        return
    products = database.get_products(active_only=False)
    if not products:
        await message.answer("Mahsulotlar yo'q.")
        return
    lines = [
        f"#{p['id']} {p['name']} — {p['price']} so'm ({p['category'] or '—'})"
        for p in products
    ]
    await message.answer("\n".join(lines))


@dp.message(F.text == "📊 Buyurtmalar")
async def list_orders(message: Message):
    if not is_admin(message.from_user.id):
        return
    orders = database.get_recent_orders()
    if not orders:
        await message.answer("Buyurtmalar yo'q.")
        return
    lines = []
    for o in orders:
        items = json.loads(o["items"])
        items_text = ", ".join(f"{i['name']} x{i['qty']}" for i in items)
        lines.append(
            f"#{o['id']} — {STATUS_LABELS.get(o['status'], o['status'])} — {o['total']} so'm\n{items_text}"
        )
    await message.answer("\n\n".join(lines))


# ---------- Mahsulot qo'shish (FSM) ----------

@dp.message(F.text == "➕ Mahsulot qo'shish")
async def add_product_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AddProduct.name)
    await message.answer("Mahsulot nomini kiriting:", reply_markup=ReplyKeyboardRemove())


@dp.message(AddProduct.name)
async def add_product_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddProduct.price)
    await message.answer("Narxini kiriting (faqat raqam, so'm):")


@dp.message(AddProduct.price)
async def add_product_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, faqat raqam kiriting:")
        return
    await state.update_data(price=int(message.text))
    await state.set_state(AddProduct.category)
    await message.answer("Kategoriyasini kiriting (masalan: Non, Sut mahsulotlari):")


@dp.message(AddProduct.category)
async def add_product_category(message: Message, state: FSMContext):
    await state.update_data(category=message.text)
    await state.set_state(AddProduct.description)
    await message.answer("Qisqacha tavsif kiriting (yo'q bo'lsa, - deb yozing):")


@dp.message(AddProduct.description)
async def add_product_description(message: Message, state: FSMContext):
    data = await state.get_data()
    description = "" if message.text.strip() == "-" else message.text
    database.add_product(data["name"], data["price"], data["category"], description)
    await state.clear()
    await message.answer(
        f"✅ Mahsulot qo'shildi: {data['name']} — {data['price']} so'm",
        reply_markup=admin_menu(),
    )


# ---------- Xabar yuborish (FSM) ----------

@dp.message(F.text == "📢 Xabar yuborish")
async def broadcast_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(Broadcast.text)
    await message.answer("Barcha foydalanuvchilarga yuboriladigan xabarni kiriting:")


@dp.message(Broadcast.text)
async def broadcast_send(message: Message, state: FSMContext):
    await state.clear()
    user_ids = database.get_all_user_ids()
    sent = 0
    for uid in user_ids:
        try:
            await bot.send_message(uid, message.text)
            sent += 1
        except Exception:
            pass
    await message.answer(f"✅ Xabar {sent} foydalanuvchiga yuborildi.", reply_markup=admin_menu())


# ---------- Buyurtma holati tugmalari ----------

@dp.callback_query(F.data.startswith("accept:"))
async def order_accept(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    order_id = int(callback.data.split(":")[1])
    database.update_order_status(order_id, "accepted")
    order = database.get_order(order_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍳 Tayyor deb belgilash", callback_data=f"ready:{order_id}")]
    ])
    await callback.message.edit_text(callback.message.html_text + "\n\n⏳ Qabul qilindi.", reply_markup=kb)
    try:
        await bot.send_message(order["user_id"], f"⏳ Buyurtmangiz (#{order_id}) qabul qilindi va tayyorlanmoqda!")
    except Exception:
        pass
    await callback.answer()


@dp.callback_query(F.data.startswith("cancel:"))
async def order_cancel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    order_id = int(callback.data.split(":")[1])
    database.update_order_status(order_id, "cancelled")
    order = database.get_order(order_id)
    await callback.message.edit_text(callback.message.html_text + "\n\n❌ Bekor qilindi.")
    try:
        await bot.send_message(order["user_id"], f"❌ Afsuski, buyurtmangiz (#{order_id}) bekor qilindi.")
    except Exception:
        pass
    await callback.answer()


@dp.callback_query(F.data.startswith("ready:"))
async def order_ready(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    order_id = int(callback.data.split(":")[1])
    database.update_order_status(order_id, "ready")
    order = database.get_order(order_id)
    await callback.message.edit_text(callback.message.html_text + "\n\n✅ Tayyor!")
    try:
        await bot.send_message(order["user_id"], f"✅ Buyurtmangiz (#{order_id}) tayyor!")
    except Exception:
        pass
    await callback.answer()


async def notify_admins_new_order(order_id: int):
    order = database.get_order(order_id)
    items = json.loads(order["items"])
    items_text = "\n".join(f"• {i['name']} x{i['qty']} — {i['price'] * i['qty']} so'm" for i in items)
    text = (
        f"🆕 Yangi buyurtma #{order_id}\n"
        f"👤 {order['username'] or order['user_id']}\n\n"
        f"{items_text}\n\nJami: {order['total']} so'm"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"accept:{order_id}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"cancel:{order_id}"),
        ]
    ])
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, reply_markup=kb)
        except Exception:
            pass


# ---------- Web server: mini-ilova + API ----------

async def handle_products(request: web.Request):
    return web.json_response(database.get_products())


async def handle_order(request: web.Request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid json"}, status=400)

    user_id = data.get("user_id")
    items = data.get("items") or []
    if not user_id or not items:
        return web.json_response({"error": "invalid data"}, status=400)

    username = data.get("username", "")
    total = sum(i.get("price", 0) * i.get("qty", 0) for i in items)

    database.add_user(user_id)
    order_id = database.add_order(user_id, username, items, total)
    await notify_admins_new_order(order_id)
    return web.json_response({"order_id": order_id, "total": total})


def create_web_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/api/products", handle_products)
    app.router.add_post("/api/order", handle_order)
    app.router.add_static("/webapp/", path="webapp", name="webapp", show_index=False)
    return app


async def main():
    database.init_db()

    web_app = create_web_app()
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", config.PORT)
    await site.start()
    logging.info(f"Web server {config.PORT}-portda ishga tushdi")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
