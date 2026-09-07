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
    Message, CallbackQuery, WebAppInfo,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

import config
import database

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

UPLOAD_DIR = os.path.join("webapp", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

STATUS_LABELS = {
    "new": "🆕 Yangi",
    "accepted": "⏳ Tayyorlanmoqda",
    "ready": "✅ Tayyor",
    "cancelled": "❌ Bekor qilingan",
}


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


def contact_request_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
    )


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
        [KeyboardButton(text="📈 Savdo statistikasi")],
        [KeyboardButton(text="🖼 Fon rasmini o'rnatish")],
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


class Broadcast(StatesGroup):
    text = State()


class SetBackground(StatesGroup):
    image = State()


async def save_telegram_photo(message: Message, prefix: str) -> str:
    """Telegramdan kelgan rasmni webapp/uploads ichiga saqlaydi va URL manzilini qaytaradi."""
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    filename = f"{prefix}_{photo.file_unique_id}.jpg"
    path = os.path.join(UPLOAD_DIR, filename)
    await bot.download_file(file.file_path, destination=path)
    return f"/webapp/uploads/{filename}"


# ---------- Asosiy menyu ----------

@dp.message(CommandStart())
async def cmd_start(message: Message):
    database.add_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    phone = database.get_user_phone(message.from_user.id)
    if not phone:
        await message.answer(
            "Assalomu alaykum! 👋\nOziq-ovqat do'koniga xush kelibsiz.\n\n"
            "Davom etish uchun, iltimos, telefon raqamingizni yuboring — "
            "bu buyurtmangiz tayyor bo'lganda siz bilan bog'lanish uchun kerak bo'ladi:",
            reply_markup=contact_request_kb(),
        )
        return
    await message.answer(
        "Assalomu alaykum! 👋\nOziq-ovqat do'koniga xush kelibsiz.\n"
        "Quyidagi tugmalardan foydalaning:",
        reply_markup=main_menu(message.from_user.id),
    )


@dp.message(F.contact)
async def contact_received(message: Message):
    if not message.contact or message.contact.user_id != message.from_user.id:
        await message.answer(
            "Iltimos, tugma orqali faqat o'zingizning raqamingizni yuboring.",
            reply_markup=contact_request_kb(),
        )
        return
    database.add_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    database.set_user_phone(message.from_user.id, message.contact.phone_number)
    await message.answer(
        "Rahmat! ✅ Endi do'kondan foydalanishingiz mumkin.",
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
            f"№{o['daily_number']} — {STATUS_LABELS.get(o['status'], o['status'])}\n"
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
        + (" 🖼" if p.get("image_url") else "")
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
            f"№{o['daily_number']} (ID {o['id']}) — {STATUS_LABELS.get(o['status'], o['status'])} — "
            f"{o['total']} so'm\n{items_text}"
        )
    await message.answer("\n\n".join(lines))


@dp.message(F.text == "📈 Savdo statistikasi")
async def sales_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    stats = database.get_sales_summary()
    labels = {
        "kun": "📅 1 kun",
        "hafta": "🗓 1 hafta",
        "oy": "📆 1 oy",
        "yil": "📊 1 yil",
    }
    lines = ["📈 Savdo statistikasi:\n"]
    for key, label in labels.items():
        s = stats[key]
        lines.append(f"{label}: {s['total']:,}".replace(",", " ") + f" so'm ({s['count']} ta buyurtma)")
    lines.append("\n(Bekor qilingan buyurtmalar hisobga olinmagan)")
    await message.answer("\n".join(lines))


# ---------- Fon rasmini o'rnatish (FSM) ----------

@dp.message(F.text == "🖼 Fon rasmini o'rnatish")
async def set_background_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(SetBackground.image)
    await message.answer(
        "Do'kon uchun fon rasmini yuboring (o'chirish uchun '-' deb yozing):",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(SetBackground.image, F.photo)
async def set_background_photo(message: Message, state: FSMContext):
    url = await save_telegram_photo(message, "bg")
    database.set_setting("background_url", url)
    await state.clear()
    await message.answer("✅ Fon rasmi o'rnatildi.", reply_markup=admin_menu())


@dp.message(SetBackground.image, F.text == "-")
async def clear_background(message: Message, state: FSMContext):
    database.set_setting("background_url", "")
    await state.clear()
    await message.answer("✅ Fon rasmi o'chirildi.", reply_markup=admin_menu())


@dp.message(SetBackground.image)
async def set_background_invalid(message: Message):
    await message.answer("Iltimos, rasm yuboring yoki o'chirish uchun '-' deb yozing.")


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
    description = "" if message.text.strip() == "-" else message.text
    await state.update_data(description=description)
    await state.set_state(AddProduct.image)
    await message.answer("Mahsulot rasmini yuboring (rasm bo'lmasa, - deb yozing):")


@dp.message(AddProduct.image, F.photo)
async def add_product_image(message: Message, state: FSMContext):
    image_url = await save_telegram_photo(message, "product")
    await finish_add_product(message, state, image_url)


@dp.message(AddProduct.image, F.text == "-")
async def add_product_no_image(message: Message, state: FSMContext):
    await finish_add_product(message, state, None)


@dp.message(AddProduct.image)
async def add_product_image_invalid(message: Message):
    await message.answer("Iltimos, rasm yuboring yoki '-' deb yozing.")


async def finish_add_product(message: Message, state: FSMContext, image_url):
    data = await state.get_data()
    database.add_product(data["name"], data["price"], data["category"], data["description"], image_url)
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
        await bot.send_message(order["user_id"], f"⏳ Buyurtmangiz (№{order['daily_number']}) qabul qilindi va tayyorlanmoqda!")
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
        await bot.send_message(order["user_id"], f"❌ Afsuski, buyurtmangiz (№{order['daily_number']}) bekor qilindi.")
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
        await bot.send_message(order["user_id"], f"✅ Buyurtmangiz (№{order['daily_number']}) tayyor!")
    except Exception:
        pass
    await callback.answer()


async def notify_admins_new_order(order_id: int):
    order = database.get_order(order_id)
    items = json.loads(order["items"])
    items_text = "\n".join(f"• {i['name']} x{i['qty']} — {i['price'] * i['qty']} so'm" for i in items)
    phone = database.get_user_phone(order["user_id"])
    phone_text = f"\n📞 {phone}" if phone else "\n📞 Raqami yo'q"
    text = (
        f"🆕 Yangi buyurtma №{order['daily_number']} (ID {order_id})\n"
        f"👤 {order['username'] or order['user_id']}{phone_text}\n\n"
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
        except Exception as e:
            logging.warning(f"Adminga xabar yuborilmadi ({admin_id}): {e}")


# ---------- Web server: mini-ilova + API ----------

async def handle_products(request: web.Request):
    return web.json_response(database.get_products())


async def handle_settings(request: web.Request):
    return web.json_response({
        "background_url": database.get_setting("background_url", "") or "",
    })


async def handle_order(request: web.Request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Noto'g'ri so'rov (invalid json)"}, status=400)

    user_id = data.get("user_id")
    items = data.get("items") or []

    # MUHIM TUZATISH: agar mini-ilova Telegram tashqarisida (masalan brauzerda)
    # ochilgan bo'lsa, user_id topilmaydi va buyurtma "qabul qilinmagandek"
    # ko'rinardi. Endi bu holatda aniq xato xabari qaytariladi.
    if not user_id:
        return web.json_response(
            {"error": "Foydalanuvchi aniqlanmadi. Do'konni Telegram bot ichidagi \"🛒 Do'kon\" tugmasi orqali oching."},
            status=400,
        )
    if not items:
        return web.json_response({"error": "Savat bo'sh"}, status=400)

    try:
        total = sum(int(i.get("price", 0)) * int(i.get("qty", 0)) for i in items)
    except (TypeError, ValueError):
        return web.json_response({"error": "Mahsulot ma'lumotlari noto'g'ri"}, status=400)

    username = data.get("username", "")
    database.add_user(user_id, username)

    try:
        order_id = database.add_order(user_id, username, items, total)
        order = database.get_order(order_id)
        await notify_admins_new_order(order_id)
    except Exception as e:
        logging.exception("Buyurtma yaratishda xatolik")
        return web.json_response({"error": f"Server xatoligi: {e}"}, status=500)

    return web.json_response({
        "order_id": order_id,
        "daily_number": order["daily_number"],
        "total": total,
    })


async def handle_webapp_index(request: web.Request):
    return web.FileResponse("webapp/index.html")


def create_web_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/api/products", handle_products)
    app.router.add_get("/api/settings", handle_settings)
    app.router.add_post("/api/order", handle_order)
    app.router.add_get("/webapp/", handle_webapp_index)
    app.router.add_get("/webapp/index.html", handle_webapp_index)
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
  
