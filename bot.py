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
# ASOSIY MENYU
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
            "Assalomu alaykum! 👋\n"
            "Oziq-ovqat do'koniga xush kelibsiz.\n\n"
            "Davom etish uchun telefon raqamingizni yuboring:",
            reply_markup=phone_request_kb(),
        )
        return

    await state.clear()

    await message.answer(
        "Assalomu alaykum! 👋\n"
        "Oziq-ovqat do'koniga xush kelibsiz.\n"
        "Quyidagi tugmalardan foydalaning:",
        reply_markup=main_menu(
            message.from_user.id
        ),
    )


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
        "✅ Rahmat! Endi do'konimizdan "
        "foydalanishingiz mumkin.",
        reply_markup=main_menu(
            message.from_user.id
        ),
    )


@dp.message(Onboarding.phone)
async def onboarding_phone_invalid(
    message: Message,
):
    await message.answer(
        'Iltimos, pastdagi "📱 Raqamni yuborish" '
        "tugmasi orqali yuboring:",
        reply_markup=phone_request_kb(),
    )


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


@dp.message(F.text == "📜 Mening buyurtmalarim")
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
        "Admin panel:",
        reply_markup=admin_menu(),
    )


# =========================================================
# MAHSULOTLAR RO'YXATI
# =========================================================


@dp.message(F.text == "📋 Mahsulotlar ro'yxati")
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
            f"{active} #{product['id']} "
            f"{product['name']} — "
            f"{product['price']} so'm "
            f"({category})"
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
        "➕ <b>Mahsulot qo'shish</b>\n\n"
        "1️⃣ Mahsulot nomini kiriting:",
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
            "❌ Mahsulot nomi bo'sh bo'lmasin.\n"
            "Qaytadan kiriting:"
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
        "Masalan: <b>15000</b>"
    )


@dp.message(AddProduct.price)
async def add_product_price(
    message: Message,
    state: FSMContext,
):
    text = (
        message.text or ""
    ).strip()

    text = (
        text.replace(" ", "")
        .replace(",", "")
        .replace(".", "")
    )

    if not text.isdigit():
        await message.answer(
            "❌ Narx faqat son bo'lishi kerak.\n"
            "Masalan: <b>15000</b>"
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
        "Masalan: Non mahsulotlari"
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
        "4️⃣ Mahsulot tavsifini kiriting.\n\n"
        "Agar tavsif kerak bo'lmasa, <b>-</b> yuboring."
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
        "5️⃣ Mahsulot rasmini yuboring 📷\n\n"
        "Agar rasm bo'lmasa, <b>-</b> yuboring."
    )


@dp.message(
    AddProduct.image,
    F.photo,
)
async def add_product_image(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    photo = message.photo[-1]

    os.makedirs(
        "webapp/images",
        exist_ok=True,
    )

    filename = (
        f"{message.from_user.id}_"
        f"{photo.file_unique_id}.jpg"
    )

    path = os.path.join(
        "webapp",
        "images",
        filename,
    )

    try:
        await bot.download(
            photo,
            destination=path,
        )
    except Exception as e:
        logging.exception(
            "Rasmni yuklashda xato"
        )

        await message.answer(
            f"❌ Rasmni saqlab bo'lmadi:\n"
            f"<code>{e}</code>"
        )
        return

    image_url = (
        f"/images/{filename}"
    )

    try:
        database.add_product(
            data["name"],
            data["price"],
            data["category"],
            data["description"],
            image_url=image_url,
            old_price=None,
        )

    except Exception as e:
        logging.exception(
            "Mahsulot qo'shishda xato"
        )

        await state.clear()

        await message.answer(
            "❌ Mahsulot saqlanmadi.\n\n"
            f"<code>{e}</code>",
            reply_markup=admin_menu(),
        )
        return

    await state.clear()

    await message.answer(
        "✅ <b>Mahsulot muvaffaqiyatli qo'shildi!</b>\n\n"
        f"📦 Nomi: <b>{data['name']}</b>\n"
        f"💰 Narxi: <b>{data['price']} so'm</b>\n"
        f"📂 Kategoriya: <b>{data['category']}</b>",
        reply_markup=admin_menu(),
    )


@dp.message(
    AddProduct.image,
    F.text,
)
async def add_product_no_image(
    message: Message,
    state: FSMContext,
):
    text = (
        message.text or ""
    ).strip()

    if text != "-":
        await message.answer(
            "📷 Iltimos, mahsulot rasmini yuboring.\n"
            "Agar rasm bo'lmasa, <b>-</b> yuboring."
        )
        return

    data = await state.get_data()

    try:
        database.add_product(
            data["name"],
            data["price"],
            data["category"],
            data["description"],
            image_url=None,
            old_price=None,
        )

    except Exception as e:
        logging.exception(
            "Mahsulot qo'shishda xato"
        )

        await state.clear()

        await message.answer(
            "❌ Mahsulot saqlanmadi.\n\n"
            f"<code>{e}</code>",
            reply_markup=admin_menu(),
        )
        return

    await state.clear()

    await message.answer(
        "✅ <b>Mahsulot muvaffaqiyatli qo'shildi!</b>\n\n"
        f"📦 Nomi: <b>{data['name']}</b>\n"
        f"💰 Narxi: <b>{data['price']} so'm</b>\n"
        f"📂 Kategoriya: <b>{data['category']}</b>",
        reply_markup=admin_menu(),
    )


@dp.message(AddProduct.image)
async def add_product_image_invalid(
    message: Message,
):
    await message.answer(
        "📷 Rasm yuboring yoki rasm kerak bo'lmasa <b>-</b> yuboring."
    )


# =========================================================
# MAHSULOT O'CHIRISH
# =========================================================


@dp.message(F.text == "🗑 Mahsulotni o'chirish")
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
        "mahsulotning ID raqamini kiriting:\n\n"
        + "\n".join(lines),
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(DeleteProduct.product_id)
async def delete_product_confirm(
    message: Message,
    state: FSMContext,
):
    text = (
        message.text or ""
    ).strip()

    if not text.isdigit():
        await message.answer(
            "❌ Iltimos, faqat ID raqamini kiriting:"
        )
        return

    product_id = int(text)

    product = database.get_product(
        product_id
    )

    if not product:
        await message.answer(
            "❌ Bunday ID topilmadi."
        )
        return

    database.deactivate_product(
        product["id"]
    )

    await state.clear()

    await message.answer(
        f"🗑 <b>{product['name']}</b> "
        "mahsulot o'chirildi.",
        reply_markup=admin_menu(),
    )


# =========================================================
# XABAR YUBORISH
# =========================================================


@dp.message(F.text == "📢 Xabar yuborish")
async def broadcast_start(
    message: Message,
    state: FSMContext,
):
    if not is_admin(
        message.from_user.id
    ):
        return

    await state.set_state(
        Broadcast.text
    )

    await message.answer(
        "📢 Barcha foydalanuvchilarga "
        "yuboriladigan xabarni kiriting:",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(Broadcast.text)
async def broadcast_send(
    message: Message,
    state: FSMContext,
):
    if not is_admin(
        message.from_user.id
    ):
        await state.clear()
        return

    text = (
        message.text or ""
    ).strip()

    if not text:
        await message.answer(
            "❌ Xabar bo'sh bo'lmasligi kerak."
        )
        return

    await state.clear()

    user_ids = database.get_all_user_ids()

    sent = 0

    for user_id in user_ids:
        try:
            await bot.send_message(
                user_id,
                text,
            )
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


# =========================================================
# BUYURTMA HOLATI
# =========================================================


def order_ready_kb(
    order_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🍳 Tayyor deb belgilash",
                    callback_data=f"ready:{order_id}",
                )
            ]
        ]
    )


@dp.callback_query(
    F.data.startswith("accept:")
)
async def order_accept(
    callback: CallbackQuery,
):
    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "Ruxsat yo'q",
            show_alert=True,
        )
        return

    try:
        order_id = int(
            callback.data.split(
                ":",
                1,
            )[1]
        )
    except (ValueError, IndexError):
        await callback.answer(
            "Noto'g'ri buyurtma ID.",
            show_alert=True,
        )
        return

    order = database.get_order(
        order_id
    )

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

    order = database.get_order(
        order_id
    )

    current_text = (
        callback.message.html_text
        or ""
    )

    await callback.message.edit_text(
        current_text
        + "\n\n⏳ <b>Qabul qilindi.</b>",
        reply_markup=order_ready_kb(
            order_id
        ),
    )

    try:
        await bot.send_message(
            order["user_id"],
            f"⏳ Buyurtmangiz "
            f"(№{order['daily_number']}) "
            "qabul qilindi va tayyorlanmoqda!",
        )

    except Exception:
        logging.exception(
            "Buyurtma qabul qilingani haqida "
            "foydalanuvchiga xabar yuborilmadi"
        )

    await callback.answer(
        "Buyurtma qabul qilindi."
    )


@dp.callback_query(
    F.data.startswith("cancel:")
)
async def order_cancel(
    callback: CallbackQuery,
):
    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "Ruxsat yo'q",
            show_alert=True,
        )
        return

    try:
        order_id = int(
            callback.data.split(
                ":",
                1,
            )[1]
        )
    except (ValueError, IndexError):
        await callback.answer(
            "Noto'g'ri buyurtma ID.",
            show_alert
