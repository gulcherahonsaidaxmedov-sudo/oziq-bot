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


# =========================
# LOGGING
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


# =========================
# BOT
# =========================

bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

dp = Dispatcher(
    storage=MemoryStorage()
)


# =========================
# BUYURTMA HOLATLARI
# =========================

STATUS_LABELS = {
    "new": "🆕 Yangi",
    "accepted": "⏳ Tayyorlanmoqda",
    "ready": "✅ Tayyor",
    "cancelled": "❌ Bekor qilingan",
}


# =========================
# ADMIN TEKSHIRISH
# =========================

def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


# =========================
# ASOSIY MENU
# =========================

def main_menu(user_id: int) -> ReplyKeyboardMarkup:
    rows = [
        [
            KeyboardButton(
                text="🛒 Do'kon",
                web_app=WebAppInfo(
                    url=config.WEBAPP_URL
                )
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
        resize_keyboard=True
    )


# =========================
# ADMIN MENU
# =========================

def admin_menu() -> ReplyKeyboardMarkup:
    rows = [
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
    ]

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True
    )


# =========================
# FSM HOLATLAR
# =========================

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


# =========================
# TELEFON RAQAM TUGMASI
# =========================

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
