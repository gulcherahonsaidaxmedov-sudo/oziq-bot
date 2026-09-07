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


# =========================================================
# SOZLAMALAR
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    ),
)

dp = Dispatcher(storage=MemoryStorage())


STATUS_LABELS = {
    "new": "🆕 Yangi",
    "accepted": "⏳ Tayyorlanmoqda",
    "ready": "✅ Tayyor",
    "cancelled": "❌ Bekor qilingan",
}


# =========================================================
# YORDAMCHI FUNKSIYALAR
# =========================================================

def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


def main_menu(user_id: int) -> ReplyKeyboardMarkup:
    rows = [
        [
            KeyboardButton(
                text="🛒 Do'kon",
                web_app=WebAppInfo(
                    url=config.WEBAPP_URL
                ),
            )
        ],
        [
            KeyboardButton(
                text="📜 Mening buyurtmalarim"
            )
        ],
    ]

    if is_admin(user_id):
        rows.append(
            [
                KeyboardButton(
                    text="⚙️ Admin panel"
                )
            ]
        )

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
    )


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="➕ Mahsulot qo'shish"
                )
            ],
            [
                KeyboardButton(
                    text="📋 Mahsulotlar ro'yxati"
                )
            ],
            [
                KeyboardButton(
                    text="🗑 Mahsulotni o'chirish"
                )
            ],
            [
                KeyboardButton(
                    text="📊 Buyurtmalar"
                )
            ],
            [
                KeyboardButton(
                    text="📈 Statistika"
                )
            ],
            [
                KeyboardButton(
                    text="📢 Xabar yuborish"
                )
            ],
            [
                KeyboardButton(
                    text="⬅️ Orqaga"
                )
            ],
        ],
        resize_keyboard=True,
    )


def phone_request_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📱 Raqamni yuborish",
                    request_contact=True,
                )
            ]
        ],
        resize_keyboard=True,
    )


# =========================================================
# FSM HOLATLAR
# =========================================================

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


# =========================================================
# START
# =========================================================

@dp.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
):
    database.add_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
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
            "Oziq-ovqat do'koniga xush kelibsiz.\n\n"
            "Davom etish uchun telefon raqamingizni "
            "yuboring:",
            reply_markup=phone_request_kb(),
        )
        return

    await state.clear()

    await message.answer(
        "Assalomu alaykum! 👋\n\n"
        "Do'konimizga xush kelibsiz!\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=main_menu(
            message.from_user.id
        ),
    )


# =========================================================
# TELEFON RAQAM
# =========================================================

@dp.message(
    Onboarding.phone,
    F.contact,
)
async def onboarding_phone_received(
    message: Message,
    state: FSMContext,
):
    if (
        message.contact.user_id
        and message.contact.user_id
        != message.from_user.id
    ):
        await message.answer(
            "Iltimos, o'zingizning telefon "
            "raqamingizni yuboring:",
            reply_markup=phone_request_kb(),
        )
        return

    database.set_user_phone(
        message.from_user.id,
        message.contact.phone_number,
    )

    await state.clear()

    await message.answer(
        "✅ Raqamingiz saqlandi!\n\n"
        "Endi do'konimizdan foydalanishingiz mumkin.",
        reply_markup=main_menu(
            message.from_user.id
        ),
    )


@dp.message(Onboarding.phone)
async def onboarding_phone_invalid(
    message: Message,
):
    await message.answer(
        'Iltimos, "📱 Raqamni yuborish" '
        "tugmasini bosing:",
        reply_markup=phone_request_kb(),
    )


# =========================================================
# ORQAGA
# =========================================================

@dp.message(F.text == "⬅️ Orqaga")
async def back_to_main(
    message: Message,
    state: FSMContext,
):
    await state.clear()

    await message.answer(
        "Bosh menyu:",
        reply_markup=main_menu(
            message.from_user.id
        ),
    )


# =========================================================
# MENING BUYURTMALARIM
# =========================================================

@dp.message(
    F.text == "📜 Mening buyurtmalarim"
)
async def my_orders(message: Message):
    orders = database.get_user_orders(
        message.from_user.id
    )

    if not orders:
        await message.answer(
            "Sizda hali buyurtmalar yo'q."
        )
        return

    lines = []

    for order in orders:
        try:
            items = json.loads(
                order["items"]
            )
        except Exception:
            items = []

        item_lines = []

        for item in items:
            item_lines.append(
                f"• {item['name']} x{item['qty']}"
            )

        items_text = "\n".join(
            item_lines
        )

        lines.append(
            f"🧾 <b>Buyurtma №"
            f"{order['daily_number']}</b>\n"
            f"{items_text}\n\n"
            f"💰 Jami: "
            f"{order['total']} so'm\n"
            f"Holati: "
            f"{STATUS_LABELS.get("
            f"order['status'], "
            f"order['status']"
            f")}"
        )

    await message.answer(
        "\n\n".join(lines)
    )


# =========================================================
# ADMIN PANEL
# =========================================================

@dp.message(F.text == "⚙️ Admin panel")
async def admin_panel(message: Message):
    if not is_admin(
        message.from_user.id
    ):
        return

    await message.answer(
        "⚙️ <b>Admin panel</b>\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=admin_menu(),
    )


# =========================================================
# MAHSULOT QO'SHISH
# =========================================================

@dp.message(
    F.text == "➕ Mahsulot qo'shish"
)
async def add_product_start(
    message: Message,
    state: FSMContext,
):
    if not is_admin(
        message.from_user.id
    ):
        return

    await state.clear()
    await state.set_state(
        AddProduct.name
    )

    await message.answer(
        "➕ <b>Yangi mahsulot</b>\n\n"
        "1️⃣ Mahsulot nomini kiriting:\n\n"
        "Masalan: Coca Cola 1.5L",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(AddProduct.name)
async def add_product_name(
    message: Message,
    state: FSMContext,
):
    name = (
        message.text or ""
    ).strip()

    if not name:
        await message.answer(
            "❌ Mahsulot nomi bo'sh bo'lmasin."
        )
        return

    await state.update_data(
        name=name
    )

    await state.set_state(
        AddProduct.price
    )

    await message.answer(
        "2️⃣ Mahsulot narxini kiriting.\n\n"
        "Faqat raqam yozing.\n"
        "Masalan: 15000"
    )


@dp.message(AddProduct.price)
async def add_product_price(
    message: Message,
    state: FSMContext,
):
    text = (
        message.text or ""
    ).strip().replace(" ", "")

    if not text.isdigit():
        await message.answer(
            "❌ Narx noto'g'ri.\n\n"
            "Faqat raqam kiriting.\n"
            "Masalan: 15000"
        )
        return

    price = int(text)

    if price <= 0:
        await message.answer(
            "❌ Narx 0 dan katta bo'lishi kerak."
        )
        return

    await state.update_data(
        price=price
    )

    await state.set_state(
        AddProduct.category
    )

    await message.answer(
        "3️⃣ Mahsulot kategoriyasini kiriting.\n\n"
        "Masalan:\n"
        "Ichimliklar\n"
        "Shirinliklar\n"
        "Oziq-ovqat"
    )


@dp.message(AddProduct.category)
async def add_product_category(
    message: Message,
    state: FSMContext,
):
    category = (
        message.text or ""
    ).strip()

    if not category:
        await message.answer(
            "❌ Kategoriya bo'sh bo'lmasin."
        )
        return

    await state.update_data(
        category=category
    )

    await state.set_state(
        AddProduct.description
    )

    await message.answer(
        "4️⃣ Mahsulot haqida qisqa "
        "ma'lumot yozing.\n\n"
        "Masalan:\n"
        "Gazlangan ichimlik, 1.5 litr.\n\n"
        "Agar tavsif kerak bo'lmasa, "
        "<code>-</code> yozing."
    )


@dp.message(AddProduct.description)
async def add_product_description(
    message: Message,
    state: FSMContext,
):
    description = (
        message.text or ""
    ).strip()

    if description == "-":
        description = ""

    await state.update_data(
        description=description
    )

    await state.set_state(
        AddProduct.image
    )

    await message.answer(
        "5️⃣ Endi mahsulot rasmini yuboring 📸\n\n"
        "Agar rasm qo'shmoqchi bo'lmasangiz, "
        "<code>-</code> yuboring."
    )


@dp.message(AddProduct.image, F.photo)
async def add_product_photo(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    name = data.get("name", "")
    price = data.get("price", 0)
    category = data.get("category", "")
    description = data.get(
        "description", ""
    )

    try:
        images_dir = os.path.join(
            "webapp",
            "images",
        )

        os.makedirs(
            images_dir,
            exist_ok=True,
        )

        photo = message.photo[-1]

        file = await bot.get_file(
            photo.file_id
        )

        filename = (
            f"product_{photo.file_unique_id}.jpg"
        )

        filepath = os.path.join(
            images_dir,
            filename,
        )

        await bot.download_file(
            file.file_path,
            destination=filepath,
        )

        image_url = (
            config.WEBAPP_URL.rstrip("/")
            + "/images/"
            + filename
        )

        product_id = database.add_product(
            name=name,
            price=price,
            category=category,
            description=description,
            image_url=image_url,
        )

        await state.clear()

        await message.answer(
            "✅ <b>Mahsulot qo'shildi!</b>\n\n"
            f"🆔 ID: {product_id}\n"
            f"📦 Nomi: {name}\n"
            f"💰 Narxi: {price} so'm\n"
            f"📂 Kategoriya: {category}",
            reply_markup=admin_menu(),
        )

    except Exception as e:
        logging.exception(
            "Mahsulot qo'shishda xato"
        )

        await message.answer(
            "❌ Mahsulot qo'shishda xatolik yuz berdi.\n\n"
            f"<code>{str(e)}</code>\n\n"
            "Qaytadan urinib ko'ring."
        )


@dp.message(
    AddProduct.image,
    F.text == "-"
)
async def add_product_without_image(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    name = data.get("name", "")
    price = data.get("price", 0)
    category = data.get("category", "")
    description = data.get(
        "description", ""
    )

    try:
        product_id = database.add_product(
            name=name,
            price=price,
            category=category,
            description=description,
            image_url=None,
        )

        await state.clear()

        await message.answer(
            "✅ <b>Mahsulot qo'shildi!</b>\n\n"
            f"🆔 ID: {product_id}\n"
            f"📦 Nomi: {name}\n"
            f"💰 Narxi: {price} so'm\n"
            f"📂 Kategoriya: {category}",
            reply_markup=admin_menu(),
        )

    except Exception as e:
        logging.exception(
            "Rasmsiz mahsulot qo'shishda xato"
        )

        await message.answer(
            "❌ Mahsulotni saqlashda xatolik.\n\n"
            f"<code>{str(e)}</code>"
        )


@dp.message(AddProduct.image)
async def add_product_invalid_image(
    message: Message,
):
    await message.answer(
        "📸 Iltimos, mahsulot rasmini yuboring.\n\n"
        "Rasmsiz qo'shish uchun <code>-</code> yuboring."
    )


# =========================================================
# MAHSULOTLAR RO'YXATI
# =========================================================

@dp.message(
    F.text == "📋 Mahsulotlar ro'yxati"
)
async def list_products(
    message: Message,
):
    if not is_admin(
        message.from_user.id
    ):
        return

    products = database.get_products(
        active_only=False
    )

    if not products:
        await message.answer(
            "Mahsulotlar yo'q."
        )
        return

    lines = []

    for product in products:
        active = (
            "✅"
            if product["active"]
            else "❌"
        )

        category = (
            product["category"]
            or "—"
        )

        lines.append(
            f"{active} <b>#{product['id']}</b> "
            f"{product['name']}\n"
            f"💰 {product['price']} so'm\n"
            f"📂 {category}"
        )

    await message.answer(
        "\n\n".join(lines),
        reply_markup=admin_menu(),
    )


# =========================================================
# MAHSULOT O'CHIRISH
# =========================================================

@dp.message(
    F.text == "🗑 Mahsulotni o'chirish"
)
async def delete_product_start(
    message: Message,
    state: FSMContext,
):
    if not is_admin(
        message.from_user.id
    ):
        return

    products = database.get_products(
        active_only=True
    )

    if not products:
        await message.answer(
            "Mahsulotlar yo'q."
        )
        return

    lines = []

    for product in products:
        lines.append(
            f"#{product['id']} "
            f"{product['name']} — "
            f"{product['price']} so'm"
        )

    await state.set_state(
        DeleteProduct.product_id
    )

    await message.answer(
        "🗑 O'chirmoqchi bo'lgan "
        "mahsulot ID raqamini kiriting:\n\n"
        + "\n".join(lines)
    )


@dp.message(
    DeleteProduct.product_id
)
async def delete_product_confirm(
    message: Message,
    state: FSMContext,
):
    text = (
        message.text or ""
    ).strip()

    if not text.isdigit():
        await message.answer(
            "❌ Faqat ID raqamini kiriting."
        )
        return

    product_id = int(text)

    product = database.get_product(
        product_id
    )

    if not product:
        await message.answer(
            "❌ Bunday mahsulot topilmadi."
        )
        return

    database.deactivate_product(
        product["id"]
    )

    await state.clear()

    await message.answer(
        f"🗑 <b>{product['name']}</b> "
        "o'chirildi.",
        reply_markup=admin_menu(),
    )


# =========================================================
# BUYURTMALAR
# =========================================================

@dp.message(F.text == "📊 Buyurtmalar")
async def admin_orders(
    message: Message,
):
    if not is_admin(
        message.from_user.id
    ):
        return

    orders = database.get_all_orders()

    if not orders:
        await message.answer(
            "Hozircha buyurtmalar yo'q."
        )
        return

    for order in orders[:20]:
        try:
            items = json.loads(
                order["items"]
            )
        except Exception:
            items = []

        item_text = "\n".join(
            f"• {item['name']} x{item['qty']}"
            for item in items
        )

        status = STATUS_LABELS.get(
            order["status"],
            order["status"],
        )

        text = (
            f"🧾 <b>Buyurtma №"
            f"{order['daily_number']}</b>\n\n"
            f"{item_text}\n\n"
            f"💰 Jami: {order['total']} so'm\n"
            f"Holati: {status}"
        )

        await message.answer(text)


# =========================================================
# STATISTIKA
# =========================================================

@dp.message(F.text == "📈 Statistika")
async def admin_statistics(
    message: Message,
):
    if not is_admin(
        message.from_user.id
    ):
        return

    try:
        users = database.get_all_user_ids()

        products = database.get_products(
            active_only=True
        )

        orders = database.get_all_orders()

        total_orders = len(orders)

        new_orders = sum(
            1
            for order in orders
            if order["status"] == "new"
        )

        accepted_orders = sum(
            1
            for order in orders
            if order["status"] == "accepted"
        )

        ready_orders = sum(
            1
            for order in orders
            if order["status"] == "ready"
        )

        cancelled_orders = sum(
            1
            for order in orders
            if order["status"] == "cancelled"
        )

        total_sales = sum(
            int(order["total"])
            for order in orders
            if order["status"] == "ready"
        )

        await message.answer(
            "📈 <b>Statistika</b>\n\n"
            f"👥 Foydalanuvchilar: {len(users)}\n"
            f"📦 Mahsulotlar: {len(products)}\n"
            f"🧾 Jami buyurtmalar: {total_orders}\n\n"
            f"🆕 Yangi: {new_orders}\n"
            f"⏳ Tayyorlanmoqda: {accepted_orders}\n"
            f"✅ Tayyor: {ready_orders}\n"
            f"❌ Bekor qilingan: {cancelled_orders}\n\n"
            f"💰 Tayyor buyurtmalar savdosi: "
            f"{total_sales} so'm",
            reply_markup=admin_menu(),
        )

    except Exception as e:
        logging.exception(
            "Statistika xatosi"
        )

        await message.answer(
            "❌ Statistikani olishda xato:\n
