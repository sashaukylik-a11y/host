#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  🤖 CLAUDE ACCESS BOT — Premium Subscription Service                ║
║  Owner: @snapwave  |  ID: 8209837049                                ║
║  Stack: Python 3.11+ | aiogram 3.7+                                  ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    CallbackQuery, Message, WebAppInfo
)
from aiogram.utils.markdown import hbold, hitalic, hcode

# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════
BOT_TOKEN = "8616697286:AAGgLf4VwW6GWtCWHPLcNQb58z_CmGAR1DM"
OWNER_USERNAME = "@snapwave"
OWNER_ID = 8209837049

CHANNEL_ID = "@snapclient"
TERMS_URL = "https://telegra.ph/Polzovatelskoe-soglashenie-08-27-61"
ACCEPTED_FILE = "accepted_users.json"
SUBS_FILE = "subscribed_users.json"

# TON Keeper wallet
TON_WALLET = "EQAe7VARyerPTc2GyFYenYAMoog0DtNmRP411QOlkMKJe7KW"
TON_EXPLORER = f"https://tonviewer.com/{TON_WALLET}"

# Payment link (Telegram Wallet / Stars external)
PAYMENT_BASE_URL = "https://t.me/send?start=IV0pacHEUyiD"

# ═══════════════════════════════════════════════════════════════════════
# SUBSCRIPTION TIERS
# ═══════════════════════════════════════════════════════════════════════
TIERS = {
    "opus_46": {
        "name": "Claude Opus 4.6",
        "price": 5,
        "emoji": "⚡",
        "badge": "STARTER",
        "color": "🟢",
        "desc": "Доступ к Claude Opus 4.6 — идеально для студентов, фрилансеров и личных проектов. Мощь нейросети без переплат.",
        "features": [
            "✅ Неограниченные запросы к Opus 4.6",
            "✅ Контекст до 200K токенов",
            "✅ Приоритетная скорость ответа",
            "✅ Поддержка 24/7",
        ],
    },
    "opus_47": {
        "name": "Claude Opus 4.7",
        "price": 10,
        "emoji": "🔥",
        "badge": "POPULAR",
        "color": "🔵",
        "desc": "Самый популярный тариф. Claude Opus 4.7 — баланс цены и возможностей для профессионалов.",
        "features": [
            "✅ Всё из Starter +",
            "✅ Расширенный контекст до 400K токенов",
            "✅ Распознавание изображений (Vision)",
            "✅ Ранний доступ к новым фичам",
            "✅ Персональный менеджер",
        ],
    },
    "opus_50": {
        "name": "Claude Opus 5.0",
        "price": 20,
        "emoji": "🚀",
        "badge": "PRO",
        "color": "🟣",
        "desc": "Максимальная производительность для команд и агентств. Claude Opus 5.0 — топовая модель для сложных задач.",
        "features": [
            "✅ Всё из Popular +",
            "✅ Контекст до 1M токенов",
            "✅ API-доступ для интеграций",
            "✅ Совместный доступ до 3 пользователей",
            "✅ Экспорт диалогов и аналитика",
            "✅ Гарантия uptime 99.9%",
        ],
    },
    "fable_50": {
        "name": "Claude Fable 5.0",
        "price": 50,
        "emoji": "👑",
        "badge": "HIT — LIMITED",
        "color": "🟡",
        "desc": "🔥 ХИТ ПРОДАЖ! Эксклюзивный доступ к Claude Fable 5.0 — ограниченная серия для тех, кто выбирает лучшее. Творческий интеллект нового поколения.",
        "features": [
            "✅ Всё из Pro +",
            "🌟 Эксклюзивная модель Fable 5.0",
            "🌟 Бесконечный контекст в рамках сессии",
            "🌟 Генерация кода + автодеплой",
            "🌟 Совместный доступ до 10 пользователей",
            "🌟 White-label интеграция",
            "🌟 Прямая линия с командой разработки",
            "🌟 Lifetime обновления",
        ],
    },
}

# ═══════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# JSON STORAGE
# ═══════════════════════════════════════════════════════════════════════

def load_json(path: str) -> set:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("users", []))
        except Exception as e:
            logger.error(f"Failed to load {path}: {e}")
    return set()


def save_json(path: str, users: set):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"users": sorted(users)}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save {path}: {e}")


accepted_users = load_json(ACCEPTED_FILE)
subscribed_users = load_json(SUBS_FILE)

# ═══════════════════════════════════════════════════════════════════════
# BOT & DISPATCHER INIT
# ═══════════════════════════════════════════════════════════════════════
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════

async def check_channel_subscription(user_id: int) -> bool:
    """Проверяет, подписан ли пользователь на канал @snapclient"""
    if user_id == OWNER_ID:
        return True
    if user_id in subscribed_users:
        return True
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        is_sub = member.status in ["member", "administrator", "creator"]
        if is_sub:
            subscribed_users.add(user_id)
            save_json(SUBS_FILE, subscribed_users)
        return is_sub
    except Exception as e:
        logger.warning(f"Subscription check failed for {user_id}: {e}")
        return False


def divider() -> str:
    return "━━━━━━━━━━━━━━━━━━━━━━━"


def spacer() -> str:
    return "\n"


# ═══════════════════════════════════════════════════════════════════════
# KEYBOARDS — REPLY (COLORFUL STYLE)
# ═══════════════════════════════════════════════════════════════════════

def reply_main_menu() -> ReplyKeyboardMarkup:
    """Главное меню с ReplyKeyboard — красивые "цветные" кнопки через emoji"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🟢 💳 ТАРИФЫ")],
            [KeyboardButton(text="🔵 📋 Мои подписки"), KeyboardButton(text="🟣 💬 Поддержка")],
            [KeyboardButton(text="🟡 ℹ️ О сервисе")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def reply_back_only() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Назад в меню")]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


# ═══════════════════════════════════════════════════════════════════════
# KEYBOARDS — INLINE
# ═══════════════════════════════════════════════════════════════════════

def terms_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📄 Прочитать соглашение", url=TERMS_URL)],
            [InlineKeyboardButton(text="✅ Я прочитал(а) и ознакомлен(а)", callback_data="accept_terms")],
        ]
    )


def channel_sub_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться на канал", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}")],
            [InlineKeyboardButton(text="🔄 Я подписался — проверить", callback_data="check_sub")],
        ]
    )


def tiers_kb() -> InlineKeyboardMarkup:
    buttons = []
    for key, tier in TIERS.items():
        label = f"{tier['emoji']} {tier['name']} — ${tier['price']}/мес"
        if tier['badge'] == "HIT — LIMITED":
            label = f"👑🔥 {tier['name']} — ${tier['price']}/мес"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"tier:{key}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def payment_kb(tier_key: str) -> InlineKeyboardMarkup:
    tier = TIERS[tier_key]
    # Telegram Wallet
    pay_url = f"{PAYMENT_BASE_URL}&amount={tier['price']}&plan={tier_key}"
    # TON Keeper deep link (nanoTON = price * 1e9, but we keep it simple with memo)
    ton_url = f"https://app.tonkeeper.com/transfer/{TON_WALLET}?amount={tier['price']}000000000&text=CLAUDE_{tier_key}_{tier['price']}USD"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"💳 Telegram Wallet ${tier['price']}", url=pay_url),
            ],
            [
                InlineKeyboardButton(text=f"💎 TON Keeper ${tier['price']}", url=ton_url),
            ],
            [
                InlineKeyboardButton(text="📨 Я оплатил — отправить чек", callback_data=f"paid:{tier_key}"),
            ],
            [
                InlineKeyboardButton(text="⬅️ К тарифам", callback_data="show_tiers"),
            ],
        ]
    )


def admin_notify_kb(user_id: int, tier_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_approve:{user_id}:{tier_key}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject:{user_id}:{tier_key}"),
            ]
        ]
    )


# ═══════════════════════════════════════════════════════════════════════
# MESSAGE BUILDERS
# ═══════════════════════════════════════════════════════════════════════

def build_terms_text() -> str:
    return (
        f"{hbold('📜 ПОЛЬЗОВАТЕЛЬСКОЕ СОГЛАШЕНИЕ')}\n"
        f"{divider()}\n"
        f"{hitalic('Прежде чем начать использование сервиса, пожалуйста, ознакомьтесь с условиями.')}\n"
        f"\n"
        f"{hbold('В соглашении указаны:')}\n"
        f"  • Правила использования сервиса\n"
        f"  • Условия подписки и возврата\n"
        f"  • Ответственность сторон\n"
        f"  • Политика конфиденциальности\n"
        f"{divider()}\n"
        f"{hbold('👇 Действия:')}"
    )


def build_channel_text() -> str:
    return (
        f"{hbold('📢 ОБЯЗАТЕЛЬНАЯ ПОДПИСКА')}\n"
        f"{divider()}\n"
        f"{hitalic('Для доступа к боту необходимо подписаться на наш канал.')}\n"
        f"\n"
        f"{hbold('Что вы получите в канале:')}\n"
        f"  🔔 Уведомления о новых тарифах\n"
        f"  🎁 Эксклюзивные промокоды\n"
        f"  📰 Новости нейросетей и ИИ\n"
        f"  💡 Лайфхаки по использованию Claude\n"
        f"{divider()}\n"
        f"{hbold('👇 Подпишитесь и нажмите проверку:')}"
    )


def build_welcome_text(user_name: str) -> str:
    return (
        f"{hbold('🧠 CLAUDE ACCESS')} {hitalic('— Премиум-доступ к нейросетям')}\n"
        f"{divider()}\n"
        f"Привет, {hbold(user_name)}! 👋\n"
        f"\n"
        f"{hitalic('Профессиональный доступ к Claude без VPN и сложных настроек.')}\n"
        f"\n"
        f"{hbold('💎 Почему выбирают нас?')}\n"
        f"  ⚡ Мгновенная активация после оплаты\n"
        f"  🛡 Работаем 24/7 без перебоев\n"
        f"  🔑 Официальные API-ключи\n"
        f"  💬 Поддержка {OWNER_USERNAME}\n"
        f"  💎 Оплата через Telegram Wallet & TON Keeper\n"
        f"{divider()}\n"
        f"{hbold('👇 Выберите действие в меню ниже:')}"
    )


def build_tier_text(tier_key: str) -> str:
    t = TIERS[tier_key]
    badge_line = f"\n{t['color']} {hbold(t['badge'])}\n" if t['badge'] else "\n"
    features = "\n".join(f"  {f}" for f in t['features'])
    return (
        f"{t['emoji']} {hbold(t['name'])} {t['emoji']}\n"
        f"{divider()}\n"
        f"{badge_line}"
        f"{hitalic(t['desc'])}\n"
        f"\n"
        f"{hbold('💰 Стоимость:')} {hcode(f'${t[chr(39)+chr(39)]price}/месяц')}\n"
        f"\n"
        f"{hbold('📦 Что включено:')}\n"
        f"{features}\n"
        f"{divider()}\n"
        f"{hbold('💎 Способы оплаты:')}\n"
        f"  💳 Telegram Wallet (Stars/карты)\n"
        f"  💎 TON Keeper (TON/USDT)\n"
        f"\n"
        f"{hbold('🆔 ID тарифа:')} {hcode(tier_key)}"
    )


def build_paid_request_text(user: types.User, tier_key: str) -> str:
    t = TIERS[tier_key]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"{hbold('🛎 НОВАЯ ЗАЯВКА НА ОПЛАТУ')}\n"
        f"{divider()}\n"
        f"👤 Пользователь: {hbold(user.full_name)}\n"
        f"🆔 User ID: {hcode(str(user.id))}\n"
        f"📛 Username: @{user.username or 'нет'}\n"
        f"\n"
        f"📦 Тариф: {t['emoji']} {hbold(t['name'])}\n"
        f"💵 Сумма: {hcode(f'${t[chr(39)+chr(39)]price}')}\n"
        f"⏰ Время: {hcode(now)}\n"
        f"{divider()}\n"
        f"{hbold('Действие:')} подтвердите или отклоните оплату."
    )


def build_about_text() -> str:
    return (
        f"{hbold('ℹ️ О СЕРВИСЕ CLAUDE ACCESS')}\n"
        f"{divider()}\n"
        f"{hitalic('Мы предоставляем премиум-доступ к Claude — самой мощной нейросети от Anthropic.')}\n"
        f"\n"
        f"{hbold('🚀 Наши преимущества:')}\n"
        f"  • Без VPN и прокси — работает из любой точки мира\n"
        f"  • Официальные API-ключи — стабильность и скорость\n"
        f"  • Поддержка 24/7 — ответим в течение 15 минут\n"
        f"  • Гибкие тарифы — от $5 до $50 в месяц\n"
        f"  • Оплата криптой — TON Keeper + Telegram Wallet\n"
        f"\n"
        f"{hbold('👤 Владелец:')} {OWNER_USERNAME}\n"
        f"{hbold('💎 TON-кошелёк:')}\n"
        f"{hcode(TON_WALLET)}\n"
        f"{divider()}\n"
        f"{hitalic('По всем вопросам обращайтесь в поддержку.')}\n"
    )


# ═══════════════════════════════════════════════════════════════════════
# HANDLERS
# ═══════════════════════════════════════════════════════════════════════

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id

    # Step 1: Terms
    if user_id not in accepted_users:
        await message.answer(
            build_terms_text(),
            reply_markup=terms_kb(),
            disable_web_page_preview=True,
        )
        return

    # Step 2: Channel subscription
    is_subbed = await check_channel_subscription(user_id)
    if not is_subbed:
        await message.answer(
            build_channel_text(),
            reply_markup=channel_sub_kb(),
            disable_web_page_preview=True,
        )
        return

    # Step 3: Main menu
    await message.answer(
        build_welcome_text(message.from_user.first_name),
        reply_markup=reply_main_menu(),
        disable_web_page_preview=True,
    )


@dp.callback_query(F.data == "accept_terms")
async def cb_accept_terms(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in accepted_users:
        accepted_users.add(user_id)
        save_json(ACCEPTED_FILE, accepted_users)
        logger.info(f"User {user_id} accepted terms")

    # After accepting terms -> check channel sub
    is_subbed = await check_channel_subscription(user_id)
    if not is_subbed:
        await callback.message.edit_text(
            build_channel_text(),
            reply_markup=channel_sub_kb(),
        )
    else:
        await callback.message.edit_text(
            build_welcome_text(callback.from_user.first_name),
        )
        await callback.message.answer(
            "👇 Главное меню:",
            reply_markup=reply_main_menu(),
        )
    await callback.answer("Добро пожаловать! ✅")


@dp.callback_query(F.data == "check_sub")
async def cb_check_sub(callback: CallbackQuery):
    user_id = callback.from_user.id
    is_subbed = await check_channel_subscription(user_id)
    if is_subbed:
        await callback.message.edit_text(
            build_welcome_text(callback.from_user.first_name),
        )
        await callback.message.answer(
            "👇 Главное меню:",
            reply_markup=reply_main_menu(),
        )
        await callback.answer("Подписка подтверждена! 🎉")
    else:
        await callback.answer("❌ Вы ещё не подписались на канал!", show_alert=True)


# ═══════════════════════════════════════════════════════════════════════
# REPLY KEYBOARD HANDLERS
# ═══════════════════════════════════════════════════════════════════════

@dp.message(F.text == "🟢 💳 ТАРИФЫ")
async def reply_tiers(message: Message):
    user_id = message.from_user.id
    is_subbed = await check_channel_subscription(user_id)
    if not is_subbed:
        await message.answer(build_channel_text(), reply_markup=channel_sub_kb())
        return

    text = (
        f"{hbold('📋 ВЫБЕРИТЕ ТАРИФ')}\n"
        f"{divider()}\n"
        f"{hitalic('Все тарифы включают полный доступ к Claude через наш шлюз.')}\n"
        f"{hitalic('Оплата производится единоразово за месяц.')}\n"
        f"\n"
        f"{hbold('💡 Совет:')} Claude Fable 5.0 — лучший выбор для команд и бизнеса.\n"
        f"{divider()}"
    )
    await message.answer(text, reply_markup=tiers_kb())


@dp.message(F.text == "🔵 📋 Мои подписки")
async def reply_subs(message: Message):
    user_id = message.from_user.id
    is_subbed = await check_channel_subscription(user_id)
    if not is_subbed:
        await message.answer(build_channel_text(), reply_markup=channel_sub_kb())
        return

    text = (
        f"{hbold('📋 МОИ ПОДПИСКИ')}\n"
        f"{divider()}\n"
        f"{hitalic('У вас пока нет активных подписок.')}\n"
        f"\n"
        f"После оплаты и подтверждения администратором ({OWNER_USERNAME})\n"
        f"ваш доступ будет активирован в течение 5 минут.\n"
        f"{divider()}"
    )
    await message.answer(text, reply_markup=reply_main_menu())


@dp.message(F.text == "🟣 💬 Поддержка")
async def reply_support(message: Message):
    text = (
        f"{hbold('💬 ПОДДЕРЖКА')}\n"
        f"{divider()}\n"
        f"{hitalic('Напишите нам напрямую — отвечаем в течение 15 минут.')}\n"
        f"\n"
        f"{hbold('👤 Владелец:')} {OWNER_USERNAME}\n"
        f"{hbold('💎 TON-кошелёк для донатов:')}\n"
        f"{hcode(TON_WALLET)}\n"
        f"{divider()}"
    )
    await message.answer(text, reply_markup=reply_main_menu())


@dp.message(F.text == "🟡 ℹ️ О сервисе")
async def reply_about(message: Message):
    await message.answer(build_about_text(), reply_markup=reply_main_menu())


@dp.message(F.text == "⬅️ Назад в меню")
async def reply_back(message: Message):
    await message.answer(
        build_welcome_text(message.from_user.first_name),
        reply_markup=reply_main_menu(),
    )


# ═══════════════════════════════════════════════════════════════════════
# INLINE CALLBACK HANDLERS
# ═══════════════════════════════════════════════════════════════════════

@dp.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        build_welcome_text(callback.from_user.first_name),
    )
    await callback.message.answer(
        "👇 Главное меню:",
        reply_markup=reply_main_menu(),
    )
    await callback.answer()


@dp.callback_query(F.data == "show_tiers")
async def cb_show_tiers(callback: CallbackQuery):
    text = (
        f"{hbold('📋 ВЫБЕРИТЕ ТАРИФ')}\n"
        f"{divider()}\n"
        f"{hitalic('Все тарифы включают полный доступ к Claude через наш шлюз.')}\n"
        f"{hitalic('Оплата производится единоразово за месяц.')}\n"
        f"\n"
        f"{hbold('💡 Совет:')} Claude Fable 5.0 — лучший выбор для команд и бизнеса.\n"
        f"{divider()}"
    )
    await callback.message.edit_text(text, reply_markup=tiers_kb())
    await callback.answer()


@dp.callback_query(F.data.startswith("tier:"))
async def cb_tier_detail(callback: CallbackQuery):
    tier_key = callback.data.split(":", 1)[1]
    if tier_key not in TIERS:
        await callback.answer("❌ Тариф не найден", show_alert=True)
        return

    text = build_tier_text(tier_key)
    await callback.message.edit_text(text, reply_markup=payment_kb(tier_key))
    await callback.answer()


@dp.callback_query(F.data.startswith("paid:"))
async def cb_paid(callback: CallbackQuery):
    tier_key = callback.data.split(":", 1)[1]
    if tier_key not in TIERS:
        await callback.answer("❌ Ошибка тарифа", show_alert=True)
        return

    t = TIERS[tier_key]
    user = callback.from_user

    # Notify admin (skip if user is owner testing)
    if user.id != OWNER_ID:
        admin_text = build_paid_request_text(user, tier_key)
        try:
            await bot.send_message(
                chat_id=OWNER_ID,
                text=admin_text,
                reply_markup=admin_notify_kb(user.id, tier_key),
            )
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")
    else:
        logger.info("Owner self-payment detected, skipping admin notify.")

    # Answer user
    user_text = (
        f"{hbold('✅ ЗАЯВКА ОТПРАВЛЕНА')}\n"
        f"{divider()}\n"
        f"{t['emoji']} Тариф: {hbold(t['name'])}\n"
        f"💵 Сумма: {hcode(f'${t[chr(39)+chr(39)]price}')}\n"
        f"\n"
        f"{hitalic('Ваш платёж находится на проверке.')}\n"
        f"{hitalic('Администратор')} {OWNER_USERNAME} {hitalic('подтвердит доступ в течение 5-15 минут.')}\n"
        f"\n"
        f"{hbold('📌 Что дальше?')}\n"
        f"1. Дождитесь подтверждения\n"
        f"2. Получите персональную ссылку для входа\n"
        f"3. Начните использовать Claude\n"
        f"{divider()}\n"
        f"{hbold('🆔 Номер заявки:')} {hcode(str(callback.id[:12]))}"
    )
    await callback.message.edit_text(user_text, reply_markup=tiers_kb())
    await callback.answer("Заявка отправлена! Ожидайте подтверждения.", show_alert=True)


@dp.callback_query(F.data.startswith("admin_approve:"))
async def cb_admin_approve(callback: CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("❌ Неверный формат", show_alert=True)
        return
    _, user_id_str, tier_key = parts
    user_id = int(user_id_str)

    t = TIERS.get(tier_key, {"name": "Unknown", "emoji": "❓"})
    expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                f"{hbold('🎉 ДОСТУП АКТИВИРОВАН!')}\n"
                f"{divider()}\n"
                f"{t['emoji']} Тариф: {hbold(t['name'])}\n"
                f"\n"
                f"{hitalic('Ваша подписка успешно активирована.')}\n"
                f"\n"
                f"{hbold('🔗 Ваша персональная ссылка:')}\n"
                f"{hcode(f'https://claude-access.snapwave.io/u/{user_id}')}\n"
                f"\n"
                f"{hbold('📅 Действует до:')} {hcode(expiry)}\n"
                f"{divider()}\n"
                f"По вопросам обращайтесь: {OWNER_USERNAME}"
            ),
        )
    except Exception as e:
        logger.error(f"Failed to notify user {user_id}: {e}")

    await callback.message.edit_text(
        callback.message.text + f"\n{divider()}\n{hbold('✅ ПОДТВЕРЖДЕНО')} админом",
        reply_markup=None,
    )
    await callback.answer("Пользователь уведомлён", show_alert=True)


@dp.callback_query(F.data.startswith("admin_reject:"))
async def cb_admin_reject(callback: CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("❌ Неверный формат", show_alert=True)
        return
    _, user_id_str, tier_key = parts
    user_id = int(user_id_str)

    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                f"{hbold('❌ ОПЛАТА НЕ ПОДТВЕРЖДЕНА')}\n"
                f"{divider()}\n"
                f"Администратор не обнаружил ваш платёж.\n"
                f"Пожалуйста, проверьте реквизиты и попробуйте снова.\n"
                f"\n"
                f"{hbold('💎 TON-кошелёк:')}\n"
                f"{hcode(TON_WALLET)}\n"
                f"{divider()}\n"
                f"Поддержка: {OWNER_USERNAME}"
            ),
        )
    except Exception as e:
        logger.error(f"Failed to notify user {user_id}: {e}")

    await callback.message.edit_text(
        callback.message.text + f"\n{divider()}\n{hbold('❌ ОТКЛОНЕНО')} админом",
        reply_markup=None,
    )
    await callback.answer("Пользователь уведомлён об отказе", show_alert=True)


# ═══════════════════════════════════════════════════════════════════════
# MAIN ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════════

async def main():
    logger.info("🚀 Starting Claude Access Bot...")
    logger.info(f"👤 Owner: {OWNER_USERNAME} | ID: {OWNER_ID}")
    logger.info(f"📢 Channel: {CHANNEL_ID}")
    logger.info(f"📜 Terms URL: {TERMS_URL}")
    logger.info(f"💎 TON Wallet: {TON_WALLET}")
    logger.info(f"👥 Accepted users: {len(accepted_users)} | Subscribed: {len(subscribed_users)}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
