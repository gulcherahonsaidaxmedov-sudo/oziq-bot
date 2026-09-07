import asyncio
import json
import logging
import os
from html import escape

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


# =========================================================
# LOG
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


# =========================================================
# BOT
# =========================================================

bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

dp = Dispatcher(
    storage=MemoryStorage()
)


# =========================================================
# STATUS
# =========================================================

STATUS_LABELS = {
    "new": "🆕 Yangi",
    "accepted": "⏳ Tayyorlanmoqda",
    "ready": "✅ Tayyor",
    "cancelled": "❌ Bekor qilingan",
}


# =========================================================
# ADMIN
# =========================================================

def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


# =========================================================
# MENULAR
# =========================================================

def main_menu(user_id: int) -> ReplyKeyboardMarkup:
    rows = [
        [
            KeyboardButton(
                text="🛒 Do'kon",
                web_app=WebAppInfo(url=config.WEBAPP_URL)
            )
        ],
        [
            KeyboardButton(text="📜 Mening buyurtmalarim")
        ],
    ]

    if is_admin(user_id):
        rows.append([
            KeyboardButton(text="⚙️ Admin panel")
        ])

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True
    )


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

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True
    )


def phone_request_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📱 Raqamni yuborish",
                    request_contact=True
                )
            ]
        ],
        resize_keyboard=True
    )


# =========================================================
# STATES
# =========================================================

class AddProduct(StatesGroup):
    name = State()
    price = State()
    old_price = State()
    category = State()
    description = State()
    image = State()


class DeleteProduct(StatesGroup):
    product_id = State()


class Onboarding(StatesGroup):
    phone = State()


class Broadcast(StatesGroup):
    text = State()


# =========================================================
# START
# =========================================================

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):

    database.add_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name
    )

    phone = database.get_user_phone(
        message.from_user.id
    )

    if not phone:

        await state.set_state(
            Onboarding.phone
        )

        await message.answer(
            "Assalomu alaykum! 👋\n\n"
            "🛒 <b>TEGEN</b> do'koniga xush kelibsiz!\n\n"
            "Buyurtma berish uchun telefon raqamingizni yuboring:",
            reply_markup=phone_request_kb()
        )

        return

    await state.clear()

    await message.answer(
        "Assalomu alaykum! 👋\n\n"
        "🛒 <b>TEGEN</b> do'koniga xush kelibsiz!\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=main_menu(
            message.from_user.id
        )
    )


# =========================================================
# TELEFON RAQAMI
# =========================================================

@dp.message(Onboarding.phone, F.contact)
async def onboarding_phone_received(
    message: Message,
    state: FSMContext
):

    # Faqat foydalanuvchining o'z kontaktini qabul qilamiz
    if (
        message.contact.user_id
        and message.contact.user_id != message.from_user.id
    ):
        await message.answer(
            "❌ Iltimos, o'zingizning telefon raqamingizni yuboring.",
            reply_markup=phone_request_kb()
        )
        return

    database.set_user_phone(
        message.from_user.id,
        message.contact.phone_number
    )

    await state.clear()

    await message.answer(
        "✅ <b>Rahmat!</b>\n\n"
        "Endi TEGEN do'konidan foydalanishingiz mumkin. 🛒",
        reply_markup=main_menu(
            message.from_user.id
        )
    )


@dp.message(Onboarding.phone)
async def onboarding_phone_invalid(
    message: Message
):

    await message.answer(
        "📱 Davom etish uchun pastdagi "
        "<b>«Raqamni yuborish»</b> tugmasini bosing.",
        reply_markup=phone_request_kb()
    )


# =========================================================
# ORQAGA
# =========================================================

@dp.message(F.text == "⬅️ Orqaga")
async def back_to_main(message: Message):

    await message.answer(
        "Bosh menyu:",
        reply_markup=main_menu(
            message.from_user.id
        )
    )


# =========================================================
# MENING BUYURTMALARIM
# =========================================================

@dp.message(F.text == "📜 Mening buyurtmalarim")
async def my_orders(message: Message):

    orders = database.get_user_orders(
        message.from_user.id
    )

    if not orders:
        await message.answer(
            "📭 Sizda hali buyurtmalar yo'q."
        )
        return

    lines = [
        "<b>📜 Mening buyurtmalarim</b>\n"
    ]

    for order in orders:

        try:
            items = json.loads(
                order["items"]
            )
        except Exception:
            items = []

        items_text = ", ".join(
            f"{escape(str(item.get('name', 'Mahsulot')))} "
            f"x{item.get('qty', 0)}"
            for item in items
        )

        status = STATUS_LABELS.get(
            order["status"],
            order["status"]
        )

        lines.append(
            f"🧾 <b>№{order['daily_number']}</b>\n"
            f"{status}\n"
            f"🛍 {items_text}\n"
            f"💰 Jami: <b>{order['total']:,}</b> so'm"
            .replace(",", " ")
        )

    await message.answer(
        "\n\n".join(lines)
    )


# =========================================================
# ADMIN PANEL
# =========================================================

@dp.message(F.text == "⚙️ Admin panel")
async def admin_panel(message: Message):

    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "⚙️ <b>Admin panel</b>\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=admin_menu()
    )


# =========================================================
# MAHSULOTLAR RO'YXATI
# =========================================================

@dp.message(F.text == "📋 Mahsulotlar ro'yxati")
async def list_products(message: Message):

    if not is_admin(message.from_user.id):
        return

    products = database.get_products(
        active_only=False
    )

    if not products:
        await message.answer(
            "📭 Mahsulotlar yo'q."
        )
        return

    lines = [
        "<b>📋 Mahsulotlar</b>\n"
    ]

    for product in products:

        status = (
            "🟢 Aktiv"
            if product["active"]
            else "🔴 O'chirilgan"
        )

        old_price = product.get("old_price")

        if old_price:
            price_text = (
                f"<s>{old_price:,}</s> → "
                f"<b>{product['price']:,}</b> so'm"
            )
        else:
            price_text = (
                f"<b>{product['price']:,}</b> so'm"
            )

        lines.append(
            f"#{product['id']} "
            f"<b>{escape(str(product['name']))}</b>\n"
            f"💰 {price_text}\n"
            f"📂 {escape(str(product['category'] or '—'))}\n"
            f"{status}"
            .replace(",", " ")
        )

    await message.answer(
        "\n\n".join(lines)
    )


# =========================================================
# BUYURTMALAR
# =========================================================

@dp.message(F.text == "📊 Buyurtmalar")
async def list_orders(message: Message):

    if not is_admin(message.from_user.id):
        return

    orders = database.get_recent_orders()

    if not orders:
        await message.answer(
            "📭 Buyurtmalar yo'q."
        )
        return

    lines = [
        "<b>📊 So'nggi buyurtmalar</b>\n"
    ]

    for order in orders:

        try:
            items = json.loads(
                order["items"]
            )
        except Exception:
            items = []

        items_text = ", ".join(
            f"{escape(str(item.get('name', 'Mahsulot')))} "
            f"x{item.get('qty', 0)}"
            for item in items
        )

        status = STATUS_LABELS.get(
            order["status"],
            order["status"]
        )

        lines.append(
            f"🧾 <b>№{order['daily_number']}</b> — {status}\n"
            f"👤 {escape(str(order['username'] or order['user_id']))}\n"
            f"🛍 {items_text}\n"
            f"💰 {order['total']:,} so'm"
            .replace(",", " ")
        )

    await message.answer(
        "\n\n".join(lines)
    )


# =========================================================
# STATISTIKA
# =========================================================

@dp.message(F.text == "📈 Statistika")
async def sales_stats(message: Message):

    if not is_admin(message.from_user.id):
        return

    summary = database.get_sales_summary()

    labels = {
        "kun": "📅 1 kun",
        "hafta": "🗓 1 hafta",
        "oy": "📆 1 oy",
        "yil": "📈 1 yil"
    }

    lines = [
        "<b>📈 Savdo statistikasi</b>\n"
    ]

    for key, label in labels.items():

        data = summary[key]

        total = f"{data['total']:,}".replace(
            ",", " "
        )

        lines.append(
            f"{label}: "
            f"{data['count']} ta buyurtma — "
            f"<b>{total} so'm</b>"
        )

    await message.answer(
        "\n".join(lines)
    )


# =========================================================
# MAHSULOT QO'SHISH
# =========================================================

@dp.message(F.text == "➕ Mahsulot qo'shish")
async def add_product_start(
    message: Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        return

    await state.set_state(
        AddProduct.name
    )

    await message.answer(
        "➕ <b>Yangi mahsulot</b>\n\n"
        "1️⃣ Mahsulot nomini kiriting:",
        reply_markup=ReplyKeyboardRemove()
    )


@dp.message(AddProduct.name)
async def add_product_name(
    message: Message,
    state: FSMContext
):

    if not message.text or not message.text.strip():
        await message.answer(
            "❌ Mahsulot nomi bo'sh bo'lmasin:"
        )
        return

    await state.update_data(
        name=message.text.strip()
    )

    await state.set_state(
        AddProduct.price
    )

    await message.answer(
        "2️⃣ Mahsulotning sotuv narxini kiriting:\n\n"
        "Masalan: <code>15000</code>"
    )


@dp.message(AddProduct.price)
async def add_product_price(
    message: Message,
    state: FSMContext
):

    if (
        not message.text
        or not message.text.strip().isdigit()
    ):
        await message.answer(
            "❌ Iltimos, faqat raqam kiriting.\n\n"
            "Masalan: <code>15000</code>"
        )
        return

    price = int(
        message.text.strip()
    )

    if price <= 0:
        await message.answer(
            "❌ Narx 0 dan katta bo'lishi kerak:"
        )
        return

    await state.update_data(
        price=price
    )

    await state.set_state(
        AddProduct.old_price
    )

    await message.answer(
        "3️⃣ Eski narxni kiriting.\n\n"
        "Agar chegirma bo'lmasa, <code>-</code> yuboring.\n\n"
        "Masalan: <code>20000</code>"
    )


@dp.message(AddProduct.old_price)
async def add_product_old_price(
    message: Message,
    state: FSMContext
):

    text = (
        message.text.strip()
        if message.text
        else ""
    )

    if text == "-":
        old_price = None

    elif text.isdigit():
        old_price = int(text)

        if old_price <= 0:
            await message.answer(
                "❌ Eski narx 0 dan katta bo'lishi kerak:"
            )
            return

    else:
        await message.answer(
            "❌ Faqat raqam kiriting yoki <code>-</code> yuboring:"
        )
        return

    await state.update_data(
        old_price=old_price
    )

    await state.set_state(
        AddProduct.category
    )

    await message.answer(
        "4️⃣ Kategoriyasini kiriting.\n\n"
        "Masalan: <i>Non mahsulotlari</i>"
    )


@dp.message(AddProduct.category)
async def add_product_category(
    message: Message,
    state: FSMContext
):

    category = (
        message.text.strip()
        if message.text
        else ""
    )

    if not category:
        await message.answer(
            "❌ Kategoriya bo'sh bo'lmasin:"
        )
        return

    await state.update_data(
        category=category
    )

    await state.set_state(
        AddProduct.description
    )

    await message.answer(
        "5️⃣ Mahsulot tavsifini kiriting.\n\n"
        "Tavsif bo'lmasa <code>-</code> yuboring."
    )


@dp.message(AddProduct.description)
async def add_product_description(
    message: Message,
    state: FSMContext
):

    text = (
        message.text.strip()
        if message.text
        else ""
    )

    description = (
        ""
        if text == "-"
        else text
    )

    await state.update_data(
        description=description
    )

    await state.set_state(
        AddProduct.image
    )

    await message.answer(
        "6️⃣ Endi mahsulot rasmini yuboring 📷\n\n"
        "Rasm bo'lmasa <code>-</code> yuboring."
    )


# =========================================================
# RASM BILAN MAHSULOT
# =========================================================

@dp.message(AddProduct.image, F.photo)
async def add_product_image(
    message: Message,
    state: FSMContext
):

    data = await state.get_data()

    os.makedirs(
        "webapp/images",
        exist_ok=True
    )

    photo = message.photo[-1]

    try:
        file_info = await bot.get_file(
            photo.file_id
        )

        filename = (
            f"{photo.file_unique_id}.jpg"
        )

        file_path = (
            f"webapp/images/{filename}"
        )

        await bot.download_file(
            file_info.file_path,
            file_path
        )

        image_url = (
            f"/webapp/images/{filename}"
        )

        database.add_product(
            data["name"],
            data["price"],
            data["category"],
            data["description"],
            image_url,
            data.get("old_price")
        )

    except Exception as error:

        logging.exception(
            "Mahsulot rasmini yuklashda xato"
        )

        await message.answer(
            "❌ Rasmni saqlashda xatolik yuz berdi.\n"
            "Qaytadan rasm yuboring."
        )

        return

    await state.clear()

    await message.answer(
        "✅ <b>Mahsulot qo'shildi!</b>\n\n"
        f"🛍 {escape(str(data['name']))}\n"
        f"💰 {data['price']:,} so'm".replace(",", " "),
        reply_markup=admin_menu()
    )


# =========================================================
# RASMSIZ MAHSULOT
# =========================================================

@dp.message(AddProduct.image, F.text == "-")
async def add_product_no_image(
    message: Message,
    state: FSMContext
):

    data = await state.get_data()

    database.add_product(
        data["name"],
        data["price"],
        data["category"],
        data["description"],
        None,
        data.get("old_price")
    )

    await state.clear()

    await message.answer(
        "✅ <b>Mahsulot qo'shildi!</b>\n\n"
        f"🛍 {escape(str(data['name']))}\n"
        f"💰 {data['price']:,} so'm".replace(",", " "),
        reply_markup=admin_menu()
    )


@dp.message(AddProduct.image)
async def add_product_image_invalid(
    message: Message
):

    await message.answer(
        "📷 Iltimos, mahsulot rasmini yuboring "
        "yoki rasm bo'lmasa <code>-</code> yozing."
    )


# =========================================================
# MAHSULOT O'CHIRISH
# =========================================================

@dp.message(F.text == "🗑 Mahsulotni o'chirish")
async def delete_product_start(
    message: Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        return

    products = database.get_products(
        active_only=True
    )

    if not products:
        await message.answer(
            "📭 Aktiv mahsulotlar yo'q."
        )
        return

    lines = [
        f"#{p['id']} "
        f"{escape(str(p['name']))} — "
        f"{p['price']:,} so'm".replace(",", " ")
        for p in products
    ]

    await state.set_state(
        DeleteProduct.product_id
    )

    await message.answer(
        "🗑 <b>Mahsulotni o'chirish</b>\n\n"
        "O'chirmoqchi bo'lgan mahsulot ID raqamini kiriting:\n\n"
        + "\n".join(lines),
        reply_markup=ReplyKeyboardRemove()
    )


@dp.message(DeleteProduct.product_id)
async def delete_product_confirm(
    message: Message,
    state: FSMContext
):

    if (
        not message.text
        or not message.text.isdigit()
    ):
        await message.answer(
            "❌ Iltimos, faqat mahsulot ID raqamini kiriting:"
        )
        return

    product_id = int(
        message.text
    )

    product = database.get_product(
        product_id
    )

    if not product:
        await message.answer(
            "❌ Bunday mahsulot ID topilmadi."
        )
        return

    database.deactivate_product(
        product["id"]
    )

    await state.clear()

    await message.answer(
        "🗑 <b>Mahsulot o'chirildi.</b>\n\n"
        f"🛍 {escape(str(product['name']))}",
        reply_markup=admin_menu()
    )


# =========================================================
# BROADCAST
# =========================================================

@dp.message(F.text == "📢 Xabar yuborish")
async def broadcast_start(
    message: Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        return

    await state.set_state(
        Broadcast.text
    )

    await message.answer(
        "📢 Barcha foydalanuvchilarga yuboriladigan "
        "xabarni kiriting:"
    )


@dp.message(Broadcast.text)
async def broadcast_send(
    message: Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        await state.clear()
        return

    if not message.text:
     
