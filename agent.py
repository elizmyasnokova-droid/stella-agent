"""
Stella Agent — Claude как мастер-астролог, таролог и хиромант.
"""
import json
import logging
from datetime import datetime
from anthropic import AsyncAnthropic
import database as db

logger = logging.getLogger(__name__)
client = AsyncAnthropic()

SYSTEM_PROMPT = """Ты — Stella, мастер-астролог с 20-летним опытом. Ты владеешь:
• Западной астрологией (знаки зодиака, дома, аспекты, транзиты)
• Ведической астрологией (Джйотиш, Раши, Накшатры, Даши)
• Китайской астрологией (Ба Цзы, Цзы Вэй Доу Шу, 5 элементов)
• Таро (78 карт, классические и авторские расклады)
• Нумерологией (числа жизненного пути, судьбы, имени)
• Хиромантией (линии руки, бугры, пальцы)
• Астрокартографией (благоприятные места для жизни)
• Синастрией (совместимость, компаратная карта)

════════════════════════════════════════
🌟 СТИЛЬ РАБОТЫ
════════════════════════════════════════

• Глубокий, серьёзный анализ — не банальные формулировки
• Используешь реальные астрологические термины (квадратура, трин, секстиль, оппозиция)
• Объясняешь символизм и архетипы планет и знаков
• Честна в интерпретациях — не только то что хочет слышать
• Всегда добавляешь практические рекомендации
• Говоришь на языке пользователя

════════════════════════════════════════
🔮 НАТАЛЬНАЯ КАРТА
════════════════════════════════════════

При составлении натальной карты анализируй:
1. **Солнечный знак** — основная суть личности, путь самовыражения
2. **Знак Луны** — эмоциональная природа, потребности, реакции
3. **Асцендент** — маска, первое впечатление, тело
4. **Позиции планет** — Меркурий (мышление), Венера (любовь/деньги),
   Марс (действие/сексуальность), Юпитер (удача/рост),
   Сатурн (уроки/ограничения), Уран (революция), Нептун (мечты), Плутон (трансформация)
5. **Доминирующий элемент** и **доминирующий крест** (кардинальный/фиксированный/мутабельный)
6. **Ведический аналог** — Раши, Накшатра рождения
7. **Китайский аналог** — животное и элемент года
8. **Число жизненного пути**

Формат ответа по натальной карте:
🌟 [ИМЯ], твоя натальная карта:

☉ **Солнце в [знаке]** — [глубокое описание]
🌙 **Луна в [знаке]** — [эмоциональный портрет]
⬆️ **Асцендент [знак]** — [внешность и первое впечатление]
[Планеты...]

🕉️ **Ведическая астрология**: [анализ]
🏮 **Китайская астрология**: [анализ]
🔢 **Нумерология**: Число жизненного пути [X] — [описание]

════════════════════════════════════════
💑 СОВМЕСТИМОСТЬ
════════════════════════════════════════

Анализируй на трёх уровнях:
1. Западная синастрия — аспекты между картами
2. Совместимость элементов
3. Китайская совместимость животных

Будь честна — плохая совместимость тоже бывает!

════════════════════════════════════════
🎴 ТАРО
════════════════════════════════════════

При раскладе:
• Называй карту и её астрологическое соответствие
• Интерпретируй в контексте вопроса и позиции
• Прямая/перевёрнутая — разные нюансы
• Финальный синтез — общий смысл расклада
• Практический совет

════════════════════════════════════════
✋ ХИРОМАНТИЯ
════════════════════════════════════════

При анализе фото руки:
1. Форма руки (огненная/земная/воздушная/водная)
2. Линия Жизни — энергия, здоровье
3. Линия Головы — мышление, интеллект
4. Линия Сердца — эмоции, любовь
5. Линия Судьбы — карьера, жизненный путь
6. Дополнительные линии и знаки
7. Бугры планет на ладони

ВАЖНО: указывай качество фото и оговаривай приблизительность анализа.

════════════════════════════════════════
🌍 АСТРОКАРТОГРАФИЯ
════════════════════════════════════════

Объясняй как планетарные линии влияют на разные регионы:
• Солнечная линия — реализация, успех
• Лунная линия — дом, семья, комфорт
• Венерная линия — любовь, творчество
• Марсовая линия — энергия, конфликты
• Юпитерная линия — удача, возможности
• Сатурная линия — труд, испытания

════════════════════════════════════════
⚠️ ЭТИКА
════════════════════════════════════════

• Никогда не предсказывай смерть, болезни или катастрофы напрямую
• Формулируй вызовы как возможности для роста
• Напоминай что астрология — инструмент самопознания, не рок
• Свобода воли всегда выше звёзд"""

TOOLS = [
    {
        "name": "get_user_profile",
        "description": "Получить натальные данные пользователя",
        "input_schema": {
            "type": "object",
            "properties": {"user_id": {"type": "integer"}},
            "required": ["user_id"],
        },
    },
    {
        "name": "save_natal_data",
        "description": "Сохранить натальные данные после составления карты",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "integer"},
                "birth_date": {"type": "string", "description": "YYYY-MM-DD"},
                "birth_time": {"type": "string", "description": "HH:MM (опционально)"},
                "birth_city": {"type": "string"},
                "sun_sign": {"type": "string"},
                "moon_sign": {"type": "string"},
                "rising_sign": {"type": "string"},
                "chinese_sign": {"type": "string"},
                "vedic_sign": {"type": "string"},
                "life_path": {"type": "integer"},
            },
            "required": ["user_id"],
        },
    },
    {
        "name": "get_planet_positions",
        "description": "Получить актуальные позиции планет на сегодня",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "YYYY-MM-DD (пусто = сегодня)"},
            },
        },
    },
    {
        "name": "get_moon_phase",
        "description": "Получить текущую фазу Луны и её знак",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "draw_tarot",
        "description": "Вытянуть карты таро для расклада",
        "input_schema": {
            "type": "object",
            "properties": {
                "spread_type": {
                    "type": "string",
                    "enum": ["one_card", "three_card", "love", "career", "celtic_cross", "year_ahead"],
                    "description": "Тип расклада",
                },
                "question": {"type": "string", "description": "Вопрос для расклада"},
            },
            "required": ["spread_type"],
        },
    },
    {
        "name": "calculate_compatibility",
        "description": "Рассчитать базовую астрологическую совместимость двух знаков",
        "input_schema": {
            "type": "object",
            "properties": {
                "sign1": {"type": "string"},
                "sign2": {"type": "string"},
                "name1": {"type": "string"},
                "name2": {"type": "string"},
            },
            "required": ["sign1", "sign2"],
        },
    },
    {
        "name": "save_reading",
        "description": "Сохранить результат чтения в историю",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "integer"},
                "reading_type": {"type": "string"},
                "result": {"type": "string"},
                "question": {"type": "string"},
            },
            "required": ["user_id", "reading_type", "result"],
        },
    },
    {
        "name": "get_mercury_retrograde",
        "description": "Проверить ретроградность Меркурия сейчас",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "calculate_numerology",
        "description": "Рассчитать числа нумерологии по дате рождения",
        "input_schema": {
            "type": "object",
            "properties": {
                "birth_date": {"type": "string", "description": "YYYY-MM-DD"},
            },
            "required": ["birth_date"],
        },
    },
]


async def execute_tool(name: str, input_data: dict) -> str:
    try:
        if name == "get_user_profile":
            user = await db.get_user(input_data["user_id"])
            if not user:
                return "Профиль не найден"
            return json.dumps(user, ensure_ascii=False, default=str)

        elif name == "save_natal_data":
            user_id = input_data.pop("user_id")
            await db.save_natal_data(user_id, **input_data)
            return json.dumps({"success": True})

        elif name == "get_planet_positions":
            from astro_calc import get_planet_positions
            date_str = input_data.get("date")
            if date_str:
                from datetime import datetime
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            else:
                dt = None
            positions = get_planet_positions(dt)
            return json.dumps(positions, ensure_ascii=False)

        elif name == "get_moon_phase":
            from astro_calc import get_moon_phase
            phase = get_moon_phase()
            return json.dumps(phase, ensure_ascii=False)

        elif name == "draw_tarot":
            from tarot_data import draw_cards, SPREADS
            spread_type = input_data.get("spread_type", "one_card")
            spread = SPREADS.get(spread_type, SPREADS["one_card"])
            cards = draw_cards(len(spread["positions"]), spread["positions"])
            result = {
                "spread_name": spread["name"],
                "question": input_data.get("question", ""),
                "cards": cards,
            }
            return json.dumps(result, ensure_ascii=False)

        elif name == "calculate_compatibility":
            from astro_calc import ZODIAC_SIGNS
            sign1 = input_data["sign1"]
            sign2 = input_data["sign2"]

            # Найти элементы
            elem1 = elem2 = "неизвестно"
            for s in ZODIAC_SIGNS:
                if s["name"] == sign1:
                    elem1 = s["element"]
                if s["name"] == sign2:
                    elem2 = s["element"]

            compat = {
                ("Огонь", "Огонь"): (85, "Страстный союз, много энергии и драмы"),
                ("Огонь", "Воздух"): (90, "Отличная совместимость — воздух раздувает огонь"),
                ("Огонь", "Земля"): (55, "Сложный союз — огонь хочет свободы, земля — стабильности"),
                ("Огонь", "Вода"): (60, "Притяжение противоположностей, но нужна работа"),
                ("Земля", "Земля"): (80, "Надёжный союз, стабильность и взаимопонимание"),
                ("Земля", "Вода"): (88, "Прекрасная совместимость — вода питает землю"),
                ("Земля", "Воздух"): (55, "Разные ценности — земля хочет стабильности, воздух — свободы"),
                ("Воздух", "Воздух"): (75, "Интеллектуальный союз, много общения"),
                ("Воздух", "Вода"): (65, "Интересное сочетание, нужно понимание"),
                ("Вода", "Вода"): (82, "Глубокая эмоциональная связь"),
            }
            key = tuple(sorted([elem1, elem2]))
            score, desc = compat.get(key, (70, "Нейтральная совместимость"))

            return json.dumps({
                "sign1": sign1, "sign2": sign2,
                "element1": elem1, "element2": elem2,
                "compatibility_score": score,
                "description": desc,
                "name1": input_data.get("name1", sign1),
                "name2": input_data.get("name2", sign2),
            }, ensure_ascii=False)

        elif name == "save_reading":
            await db.save_reading(
                input_data["user_id"],
                input_data["reading_type"],
                input_data["result"],
                input_data.get("question"),
            )
            return json.dumps({"success": True})

        elif name == "get_mercury_retrograde":
            from astro_calc import get_mercury_retrograde
            result = get_mercury_retrograde()
            return json.dumps(result, ensure_ascii=False)

        elif name == "calculate_numerology":
            from astro_calc import calculate_life_path
            from datetime import datetime
            bd = datetime.strptime(input_data["birth_date"], "%Y-%m-%d").date()
            result = calculate_life_path(bd)
            return json.dumps(result, ensure_ascii=False)

        return f"Инструмент '{name}' не найден"
    except Exception as e:
        logger.error(f"Tool '{name}' error: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


async def chat(
    user_id: int,
    message: str,
    history: list[dict],
    user_name: str = None,
    image_base64: str = None,
    image_media_type: str = "image/jpeg",
) -> str:
    name = user_name or "дорогой искатель"
    now = datetime.now()

    system = (
        SYSTEM_PROMPT
        + f"\n\n[КЛИЕНТ: имя={name}, user_id={user_id}]"
        f"\n[СЕЙЧАС: {now.strftime('%d.%m.%Y %H:%M')}, {_get_weekday(now)}]"
        "\nОбращайся по имени. Используй user_id во всех инструментах."
        "\nПомни историю разговора — это важно для контекста чтений."
    )

    if image_base64:
        user_content = [
            {"type": "image", "source": {"type": "base64", "media_type": image_media_type, "data": image_base64}},
            {"type": "text", "text": message or "Проанализируй пожалуйста"},
        ]
    else:
        user_content = message

    messages = history + [{"role": "user", "content": user_content}]

    for _ in range(6):
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            return "".join(b.text for b in response.content if hasattr(b, "text")).strip()

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    logger.info(f"Tool: {block.name}")
                    result = await execute_tool(block.name, block.input)
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return "Произошла ошибка. Попробуй ещё раз."


def _get_weekday(dt: datetime) -> str:
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    return days[dt.weekday()]
