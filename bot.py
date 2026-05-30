"""
🔮 Stella — AI астролог, таролог и хиромант
"""
import asyncio
import base64
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand, CallbackQuery, InlineKeyboardButton,
    InlineKeyboardMarkup, Message
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

import database as db
from agent import chat
from config import TELEGRAM_TOKEN
from scheduler import setup_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# ─── Helpers ───

async def agent_reply(message: Message, text: str, image_b64: str = None):
    await bot.send_chat_action(message.chat.id, "typing")
    user = await db.get_user(message.from_user.id)
    name = (user or {}).get("first_name") or message.from_user.first_name or "искатель"
    history = await db.get_chat_history(message.from_user.id)

    response = await chat(
        user_id=message.from_user.id,
        message=text,
        history=history,
        user_name=name,
        image_base64=image_b64,
    )
    await db.save_message(message.from_user.id, "user", text[:500])
    await db.save_message(message.from_user.id, "assistant", response[:1000])

    # Разбиваем длинные сообщения
    if len(response) > 4000:
        parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
        for part in parts:
            await message.answer(part, parse_mode="Markdown")
    else:
        await message.answer(response, parse_mode="Markdown")


async def do_agent_reply(chat_id: int, user_id: int, text: str, reply_func, image_b64: str = None):
    await bot.send_chat_action(chat_id, "typing")
    user = await db.get_user(user_id)
    name = (user or {}).get("first_name") or "искатель"
    history = await db.get_chat_history(user_id)

    response = await chat(
        user_id=user_id,
        message=text,
        history=history,
        user_name=name,
        image_base64=image_b64,
    )
    await db.save_message(user_id, "user", text[:500])
    await db.save_message(user_id, "assistant", response[:1000])

    if len(response) > 4000:
        parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
        for part in parts:
            await reply_func(part, parse_mode="Markdown")
    else:
        await reply_func(response, parse_mode="Markdown")


def main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔮 Натальная карта", callback_data="natal"))
    builder.add(InlineKeyboardButton(text="💑 Совместимость", callback_data="compatibility"))
    builder.add(InlineKeyboardButton(text="🎴 Расклад Таро", callback_data="tarot"))
    builder.add(InlineKeyboardButton(text="🌙 Луна сейчас", callback_data="moon"))
    builder.add(InlineKeyboardButton(text="🪐 Транзиты планет", callback_data="transits"))
    builder.add(InlineKeyboardButton(text="📅 Годовой гороскоп", callback_data="year"))
    builder.add(InlineKeyboardButton(text="🌍 Лучшие места жизни", callback_data="astrocarto"))
    builder.add(InlineKeyboardButton(text="✋ Хиромантия", callback_data="palmistry"))
    builder.adjust(2)
    return builder.as_markup()


def tarot_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🃏 Карта дня", callback_data="tarot_one_card"))
    builder.add(InlineKeyboardButton(text="🔺 Три карты", callback_data="tarot_three_card"))
    builder.add(InlineKeyboardButton(text="💕 Любовный", callback_data="tarot_love"))
    builder.add(InlineKeyboardButton(text="💼 Карьера/деньги", callback_data="tarot_career"))
    builder.add(InlineKeyboardButton(text="✝️ Кельтский крест", callback_data="tarot_celtic_cross"))
    builder.add(InlineKeyboardButton(text="📅 Год вперёд", callback_data="tarot_year_ahead"))
    builder.adjust(2)
    return builder.as_markup()


# ─── Commands ───

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await db.ensure_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    user = await db.get_user(message.from_user.id)
    name = message.from_user.first_name or "искатель"

    if user and user.get("sun_sign"):
        await message.answer(
            f"🔮 Рада видеть тебя снова, *{name}*!\n\n"
            f"☉ Твой знак: *{user['sun_sign']}*\n"
            f"🌙 Луна: *{user.get('moon_sign', 'не определена')}*\n\n"
            "Что хочешь узнать сегодня?",
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )
    else:
        await message.answer(
            f"🔮 Приветствую тебя, *{name}*! Я — *Stella*, твой проводник в мире звёзд.\n\n"
            "Я владею:\n"
            "🌟 Западной, Ведической и Китайской астрологией\n"
            "🎴 Таро — 78 карт и 6 видов раскладов\n"
            "✋ Хиромантией — анализ линий руки по фото\n"
            "🌙 Лунным календарём и транзитами планет\n"
            "🌍 Астрокартографией — где лучше жить\n\n"
            "Чтобы составить твою натальную карту — скажи дату рождения 📅\n\n"
            "_Или выбери что интересует:_",
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )


@dp.message(Command("natal"))
async def cmd_natal(message: Message):
    await db.ensure_user(message.from_user.id)
    user = await db.get_user(message.from_user.id)

    if user and user.get("birth_date"):
        prompt = (
            f"Составь полную натальную карту для пользователя. "
            f"Его данные: дата рождения {user['birth_date']}, "
            f"время {user.get('birth_time', 'неизвестно')}, "
            f"город {user.get('birth_city', 'неизвестно')}. "
            "Сделай глубокий анализ по всем системам."
        )
        await agent_reply(message, prompt)
    else:
        await message.answer(
            "🔮 *Натальная карта*\n\n"
            "Для составления карты мне нужны:\n"
            "📅 Дата рождения (обязательно)\n"
            "🕐 Время рождения (желательно — нужно для Асцендента)\n"
            "📍 Город рождения (желательно)\n\n"
            "Напиши например:\n"
            "_«15 марта 1990, 14:30, Москва»_",
            parse_mode="Markdown",
        )


@dp.message(Command("moon"))
async def cmd_moon(message: Message):
    await db.ensure_user(message.from_user.id)
    from astro_calc import get_moon_phase
    moon = get_moon_phase()

    text = (
        f"🌙 *Луна сейчас*\n\n"
        f"{moon['phase']}\n"
        f"Знак: *{moon['moon_sign']}* {moon['moon_sign_symbol']}\n"
        f"Освещение: *{moon['illumination']}%*\n\n"
        f"💫 *{moon['description']}*\n\n"
        f"⚡ Энергия: {moon['energy']}\n\n"
        f"📅 Следующее новолуние: *{moon['next_new_moon']}*\n"
        f"🌕 Следующее полнолуние: *{moon['next_full_moon']}*"
    )
    await message.answer(text, parse_mode="Markdown")

    # Добавляем интерпретацию от агента
    prompt = (
        f"Луна сейчас {moon['phase']} в {moon['moon_sign']}. "
        "Дай краткую (3-4 предложения) практическую интерпретацию — "
        "что это значит для дел, эмоций и принятия решений сегодня."
    )
    await agent_reply(message, prompt)


@dp.message(Command("transits"))
async def cmd_transits(message: Message):
    await db.ensure_user(message.from_user.id)
    prompt = (
        "Получи позиции планет на сегодня и составь краткий обзор транзитов. "
        "Что сейчас активно в небе? Какие планеты в значимых позициях? "
        "Практические советы на основе транзитов."
    )
    await agent_reply(message, prompt)


@dp.message(Command("tarot"))
async def cmd_tarot(message: Message):
    await message.answer(
        "🎴 *Расклады Таро*\n\nВыбери расклад:",
        parse_mode="Markdown",
        reply_markup=tarot_keyboard(),
    )


@dp.message(Command("compatibility"))
async def cmd_compatibility(message: Message):
    await message.answer(
        "💑 *Совместимость знаков*\n\n"
        "Напиши знаки зодиака для анализа, например:\n"
        "_«Совместимость Льва и Скорпиона»_\n"
        "_«Я Рыбы, он Телец — как мы совместимы?»_\n\n"
        "Или укажи даты рождения для полного синастрического анализа! 🌟",
        parse_mode="Markdown",
    )


@dp.message(Command("palmistry"))
async def cmd_palmistry(message: Message):
    await message.answer(
        "✋ *Хиромантия*\n\n"
        "Пришли фото своей ладони — я прочитаю линии руки!\n\n"
        "📸 *Советы для хорошего фото:*\n"
        "• Хорошее освещение (дневной свет)\n"
        "• Ладонь расправлена, пальцы слегка раздвинуты\n"
        "• Доминирующая рука (правая для правшей)\n"
        "• Фото сверху, без теней\n\n"
        "_Пришли фото и я проанализирую линии жизни, судьбы, сердца и головы!_",
        parse_mode="Markdown",
    )


@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    await db.ensure_user(message.from_user.id)
    user = await db.get_user(message.from_user.id)
    if not user or not user.get("sun_sign"):
        await message.answer(
            "📋 Профиль не заполнен.\n\nСкажи дату рождения чтобы составить натальную карту!"
        )
        return

    lines = ["📋 *Твой астрологический профиль:*\n"]
    if user.get("birth_date"):
        lines.append(f"📅 Дата рождения: *{user['birth_date']}*")
    if user.get("birth_city"):
        lines.append(f"📍 Город: *{user['birth_city']}*")
    lines.append("")
    if user.get("sun_sign"):
        lines.append(f"☉ Солнце: *{user['sun_sign']}*")
    if user.get("moon_sign"):
        lines.append(f"🌙 Луна: *{user['moon_sign']}*")
    if user.get("rising_sign"):
        lines.append(f"⬆️ Асцендент: *{user['rising_sign']}*")
    if user.get("vedic_sign"):
        lines.append(f"🕉️ Раши (Ведическая): *{user['vedic_sign']}*")
    if user.get("chinese_sign"):
        lines.append(f"🏮 Китайский знак: *{user['chinese_sign']}*")
    if user.get("life_path"):
        lines.append(f"🔢 Число жизненного пути: *{user['life_path']}*")

    await message.answer("\n".join(lines), parse_mode="Markdown")


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "🔮 *Stella — твой астролог*\n\n"
        "📸 *Пришли фото руки* → хиромантия\n\n"
        "💬 *Примеры запросов:*\n"
        "• «15 марта 1990, 14:30, Москва» → натальная карта\n"
        "• «Совместимость Льва и Водолея»\n"
        "• «Что говорят транзиты на этой неделе?»\n"
        "• «Вытяни карту на день»\n"
        "• «Где мне лучше жить по астрокартографии?»\n"
        "• «Ретроградный ли сейчас Меркурий?»\n\n"
        "📋 *Команды:*\n"
        "/natal — натальная карта\n"
        "/tarot — расклады Таро\n"
        "/moon — луна сейчас\n"
        "/transits — транзиты планет\n"
        "/compatibility — совместимость\n"
        "/palmistry — хиромантия\n"
        "/profile — мой астропрофиль\n"
        "/menu — главное меню",
        parse_mode="Markdown",
    )


# ─── Callbacks ───

@dp.callback_query(F.data == "natal")
async def cb_natal(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "🔮 *Натальная карта*\n\n"
        "Напиши дату рождения, например:\n"
        "_«15 марта 1990»_ — базовая карта\n"
        "_«15.03.1990 14:30 Москва»_ — полная карта с Асцендентом",
        parse_mode="Markdown"
    )


@dp.callback_query(F.data == "compatibility")
async def cb_compatibility(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "💑 Напиши знаки или даты рождения:\n"
        "_«Лев и Скорпион»_\n"
        "_«Я 15.03.1990, он 20.07.1988»_",
        parse_mode="Markdown"
    )


@dp.callback_query(F.data == "moon")
async def cb_moon(callback: CallbackQuery):
    await callback.answer()
    from astro_calc import get_moon_phase
    moon = get_moon_phase()
    await callback.message.answer(
        f"🌙 *{moon['phase']}*\n"
        f"Знак: *{moon['moon_sign']}* | Освещение: *{moon['illumination']}%*\n\n"
        f"💫 {moon['description']}\n\n"
        f"📅 Новолуние: {moon['next_new_moon']} | Полнолуние: {moon['next_full_moon']}",
        parse_mode="Markdown"
    )


@dp.callback_query(F.data == "transits")
async def cb_transits(callback: CallbackQuery):
    await callback.answer()
    await do_agent_reply(
        callback.message.chat.id, callback.from_user.id,
        "Получи позиции планет сейчас и дай обзор ключевых транзитов дня.",
        callback.message.answer
    )


@dp.callback_query(F.data == "tarot")
async def cb_tarot(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("🎴 Выбери расклад:", reply_markup=tarot_keyboard())


@dp.callback_query(F.data.startswith("tarot_"))
async def cb_tarot_spread(callback: CallbackQuery):
    await callback.answer()
    spread_type = callback.data.replace("tarot_", "")
    spread_names = {
        "one_card": "карту дня", "three_card": "расклад три карты",
        "love": "любовный расклад", "career": "расклад на карьеру",
        "celtic_cross": "Кельтский крест", "year_ahead": "расклад на год"
    }
    name = spread_names.get(spread_type, spread_type)
    await do_agent_reply(
        callback.message.chat.id, callback.from_user.id,
        f"Вытяни {name} и дай глубокую интерпретацию карт.",
        callback.message.answer
    )


@dp.callback_query(F.data == "year")
async def cb_year(callback: CallbackQuery):
    await callback.answer()
    await do_agent_reply(
        callback.message.chat.id, callback.from_user.id,
        "Составь годовой гороскоп для пользователя на текущий год по его знаку.",
        callback.message.answer
    )


@dp.callback_query(F.data == "astrocarto")
async def cb_astrocarto(callback: CallbackQuery):
    await callback.answer()
    await do_agent_reply(
        callback.message.chat.id, callback.from_user.id,
        "Объясни астрокартографию и расскажи какие регионы мира благоприятны "
        "для знака пользователя — для любви, карьеры, творчества.",
        callback.message.answer
    )


@dp.callback_query(F.data == "palmistry")
async def cb_palmistry(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "✋ *Хиромантия*\n\nПришли фото своей ладони — прочитаю линии руки!\n\n"
        "_Правая рука для правшей, хорошее освещение, ладонь расправлена_ 📸",
        parse_mode="Markdown"
    )


# ─── Фото ───

@dp.message(F.photo)
async def handle_photo(message: Message, state: FSMContext):
    await state.clear()
    await db.ensure_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await bot.send_chat_action(message.chat.id, "typing")

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_bytes = await bot.download_file(file.file_path)
    image_b64 = base64.standard_b64encode(file_bytes.read()).decode("utf-8")

    caption = message.caption or ""
    text = (
        f"{caption} — проанализируй линии руки (хиромантия): "
        "форму руки, линию жизни, судьбы, головы и сердца."
        if not caption else caption
    )
    await agent_reply(message, text, image_b64=image_b64)


# ─── Текст ───

@dp.message(F.text)
async def handle_text(message: Message, state: FSMContext):
    await db.ensure_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await agent_reply(message, message.text)


# ─── Startup ───

async def set_bot_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="Начать"),
        BotCommand(command="natal", description="🔮 Натальная карта"),
        BotCommand(command="tarot", description="🎴 Расклады Таро"),
        BotCommand(command="moon", description="🌙 Луна сейчас"),
        BotCommand(command="transits", description="🪐 Транзиты планет"),
        BotCommand(command="compatibility", description="💑 Совместимость"),
        BotCommand(command="palmistry", description="✋ Хиромантия"),
        BotCommand(command="profile", description="📋 Мой астропрофиль"),
        BotCommand(command="help", description="Помощь"),
    ])


async def main():
    await db.init_db()
    await set_bot_commands()
    setup_scheduler(bot)
    logger.info("🔮 Stella Bot started!")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
