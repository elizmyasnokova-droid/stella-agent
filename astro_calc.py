"""
Астрологические вычисления — планеты, луна, знаки.
Использует библиотеку ephem для точных астрономических данных.
"""
import math
from datetime import datetime, date
from typing import Optional

try:
    import ephem
    EPHEM_AVAILABLE = True
except ImportError:
    EPHEM_AVAILABLE = False

try:
    import pytz
except ImportError:
    pass


# ─── Знаки зодиака ───

ZODIAC_SIGNS = [
    {"name": "Овен", "symbol": "♈", "element": "Огонь", "quality": "Кардинальный",
     "ruler": "Марс", "start": (3, 21), "end": (4, 19)},
    {"name": "Телец", "symbol": "♉", "element": "Земля", "quality": "Фиксированный",
     "ruler": "Венера", "start": (4, 20), "end": (5, 20)},
    {"name": "Близнецы", "symbol": "♊", "element": "Воздух", "quality": "Мутабельный",
     "ruler": "Меркурий", "start": (5, 21), "end": (6, 20)},
    {"name": "Рак", "symbol": "♋", "element": "Вода", "quality": "Кардинальный",
     "ruler": "Луна", "start": (6, 21), "end": (7, 22)},
    {"name": "Лев", "symbol": "♌", "element": "Огонь", "quality": "Фиксированный",
     "ruler": "Солнце", "start": (7, 23), "end": (8, 22)},
    {"name": "Дева", "symbol": "♍", "element": "Земля", "quality": "Мутабельный",
     "ruler": "Меркурий", "start": (8, 23), "end": (9, 22)},
    {"name": "Весы", "symbol": "♎", "element": "Воздух", "quality": "Кардинальный",
     "ruler": "Венера", "start": (9, 23), "end": (10, 22)},
    {"name": "Скорпион", "symbol": "♏", "element": "Вода", "quality": "Фиксированный",
     "ruler": "Плутон/Марс", "start": (10, 23), "end": (11, 21)},
    {"name": "Стрелец", "symbol": "♐", "element": "Огонь", "quality": "Мутабельный",
     "ruler": "Юпитер", "start": (11, 22), "end": (12, 21)},
    {"name": "Козерог", "symbol": "♑", "element": "Земля", "quality": "Кардинальный",
     "ruler": "Сатурн", "start": (12, 22), "end": (1, 19)},
    {"name": "Водолей", "symbol": "♒", "element": "Воздух", "quality": "Фиксированный",
     "ruler": "Уран/Сатурн", "start": (1, 20), "end": (2, 18)},
    {"name": "Рыбы", "symbol": "♓", "element": "Вода", "quality": "Мутабельный",
     "ruler": "Нептун/Юпитер", "start": (2, 19), "end": (3, 20)},
]

SIGN_NAMES = [s["name"] for s in ZODIAC_SIGNS]


def get_sun_sign(birth_date: date) -> dict:
    """Определить знак Солнца по дате рождения."""
    month, day = birth_date.month, birth_date.day
    for sign in ZODIAC_SIGNS:
        sm, sd = sign["start"]
        em, ed = sign["end"]
        if sm <= em:
            if (month == sm and day >= sd) or (month == em and day <= ed) or (sm < month < em):
                return sign
        else:  # Козерог — переход через год
            if (month == sm and day >= sd) or (month == em and day <= ed) or month > sm or month < em:
                return sign
    return ZODIAC_SIGNS[0]


def get_moon_sign_from_ephem(birth_datetime: datetime) -> str:
    """Вычислить знак Луны через ephem."""
    try:
        moon = ephem.Moon()
        moon.compute(birth_datetime.strftime("%Y/%m/%d %H:%M:%S"))
        ecliptic_lon = math.degrees(moon.hlong)
        sign_index = int(ecliptic_lon / 30)
        return ZODIAC_SIGNS[sign_index % 12]["name"]
    except Exception:
        return "неизвестно"


def get_planet_positions(dt: datetime = None) -> dict:
    """Получить позиции планет на заданную дату."""
    if not EPHEM_AVAILABLE:
        return {"error": "ephem not available", "Солнце": {"sign": "неизвестно", "degree": 0}}

    if dt is None:
        dt = datetime.utcnow()

    date_str = dt.strftime("%Y/%m/%d %H:%M:%S")

    planets = {
        "Солнце": ephem.Sun(),
        "Луна": ephem.Moon(),
        "Меркурий": ephem.Mercury(),
        "Венера": ephem.Venus(),
        "Марс": ephem.Mars(),
        "Юпитер": ephem.Jupiter(),
        "Сатурн": ephem.Saturn(),
        "Уран": ephem.Uranus(),
        "Нептун": ephem.Neptune(),
        "Плутон": ephem.Pluto(),
    }

    result = {}
    for planet_name, planet in planets.items():
        try:
            planet.compute(date_str)
            lon = math.degrees(planet.hlong)
            sign_index = int(lon / 30) % 12
            degree = lon % 30
            sign = ZODIAC_SIGNS[sign_index]
            result[planet_name] = {
                "sign": sign["name"],
                "symbol": sign["symbol"],
                "degree": round(degree, 1),
                "longitude": round(lon, 2),
            }
        except Exception as e:
            result[planet_name] = {"sign": "неизвестно", "degree": 0, "longitude": 0}

    return result


def get_moon_phase(dt: datetime = None) -> dict:
    """Получить фазу Луны."""
    if not EPHEM_AVAILABLE:
        return {
            "phase": "🌙 Луна", "illumination": 50, "description": "данные недоступны",
            "energy": "неизвестно", "moon_sign": "неизвестно", "moon_sign_symbol": "🌙",
            "angle": 0, "next_new_moon": "скоро", "next_full_moon": "скоро"
        }

    if dt is None:
        dt = datetime.utcnow()

    date_str = dt.strftime("%Y/%m/%d %H:%M:%S")
    moon = ephem.Moon()
    moon.compute(date_str)
    phase = moon.phase  # 0-100 (% освещения)

    # Определяем фазу
    sun = ephem.Sun()
    sun.compute(date_str)

    moon_lon = math.degrees(moon.hlong) % 360
    sun_lon = math.degrees(sun.hlong) % 360
    angle = (moon_lon - sun_lon) % 360

    if angle < 45:
        phase_name = "🌑 Новолуние"
        phase_desc = "Время новых начинаний, посева намерений"
        energy = "обновление"
    elif angle < 90:
        phase_name = "🌒 Растущий серп"
        phase_desc = "Время для действий и роста"
        energy = "рост"
    elif angle < 135:
        phase_name = "🌓 Первая четверть"
        phase_desc = "Время преодоления препятствий"
        energy = "действие"
    elif angle < 180:
        phase_name = "🌔 Растущая луна"
        phase_desc = "Нарастание энергии, развитие"
        energy = "нарастание"
    elif angle < 225:
        phase_name = "🌕 Полнолуние"
        phase_desc = "Кульминация, реализация, эмоции на пике"
        energy = "кульминация"
    elif angle < 270:
        phase_name = "🌖 Убывающая луна"
        phase_desc = "Время отдачи, благодарности"
        energy = "убывание"
    elif angle < 315:
        phase_name = "🌗 Последняя четверть"
        phase_desc = "Время освобождения и завершения"
        energy = "завершение"
    else:
        phase_name = "🌘 Убывающий серп"
        phase_desc = "Время отдыха и переосмысления"
        energy = "отдых"

    # Знак луны сейчас
    moon_sign_index = int(moon_lon / 30) % 12
    moon_sign = ZODIAC_SIGNS[moon_sign_index]

    # Следующее новолуние и полнолуние
    try:
        next_new = ephem.next_new_moon(date_str)
        next_full = ephem.next_full_moon(date_str)
        next_new_dt = ephem.Date(next_new).datetime()
        next_full_dt = ephem.Date(next_full).datetime()
    except Exception:
        next_new_dt = next_full_dt = None

    return {
        "phase": phase_name,
        "illumination": round(phase, 1),
        "description": phase_desc,
        "energy": energy,
        "moon_sign": moon_sign["name"],
        "moon_sign_symbol": moon_sign["symbol"],
        "angle": round(angle, 1),
        "next_new_moon": next_new_dt.strftime("%d.%m.%Y") if next_new_dt else "скоро",
        "next_full_moon": next_full_dt.strftime("%d.%m.%Y") if next_full_dt else "скоро",
    }


def get_chinese_zodiac(birth_year: int) -> dict:
    """Китайский зодиак по году рождения."""
    animals = [
        {"name": "Крыса", "symbol": "🐀", "element_cycle": "Вода",
         "traits": "умная, адаптивная, предприимчивая"},
        {"name": "Бык", "symbol": "🐂", "element_cycle": "Земля",
         "traits": "трудолюбивый, надёжный, упорный"},
        {"name": "Тигр", "symbol": "🐅", "element_cycle": "Дерево",
         "traits": "смелый, харизматичный, непредсказуемый"},
        {"name": "Кролик", "symbol": "🐇", "element_cycle": "Дерево",
         "traits": "мягкий, дипломатичный, удачливый"},
        {"name": "Дракон", "symbol": "🐉", "element_cycle": "Земля",
         "traits": "мощный, успешный, притягивает удачу"},
        {"name": "Змея", "symbol": "🐍", "element_cycle": "Огонь",
         "traits": "мудрая, интуитивная, загадочная"},
        {"name": "Лошадь", "symbol": "🐴", "element_cycle": "Огонь",
         "traits": "свободолюбивая, энергичная, общительная"},
        {"name": "Коза", "symbol": "🐐", "element_cycle": "Земля",
         "traits": "творческая, чуткая, гармоничная"},
        {"name": "Обезьяна", "symbol": "🐒", "element_cycle": "Металл",
         "traits": "остроумная, изобретательная, игривая"},
        {"name": "Петух", "symbol": "🐓", "element_cycle": "Металл",
         "traits": "наблюдательный, прямолинейный, трудолюбивый"},
        {"name": "Собака", "symbol": "🐕", "element_cycle": "Земля",
         "traits": "верная, честная, защищающая"},
        {"name": "Свинья", "symbol": "🐷", "element_cycle": "Вода",
         "traits": "щедрая, искренняя, компанейская"},
    ]
    elements = ["Металл", "Металл", "Вода", "Вода", "Дерево",
                "Дерево", "Огонь", "Огонь", "Земля", "Земля"]

    index = (birth_year - 1900) % 12
    element_index = (birth_year - 1924) % 10
    animal = animals[index]
    element = elements[element_index % 10]

    return {
        "animal": animal["name"],
        "symbol": animal["symbol"],
        "element": element,
        "traits": animal["traits"],
    }


def get_vedic_sign(birth_date: date) -> str:
    """
    Ведический знак (примерно на 23 дня сдвинут от западного).
    Используем упрощённый расчёт.
    """
    # Ведические знаки сдвинуты ~23 дня назад (аянамса)
    # Упрощённо: вычитаем 23 дня
    from datetime import timedelta
    vedic_date = birth_date - timedelta(days=23)
    sign = get_sun_sign(vedic_date)
    return sign["name"]


def get_mercury_retrograde(dt: datetime = None) -> dict:
    """Проверить ретроградность Меркурия."""
    if dt is None:
        dt = datetime.utcnow()

    try:
        merc1 = ephem.Mercury()
        merc1.compute(dt.strftime("%Y/%m/%d"))
        lon1 = math.degrees(merc1.hlong)

        from datetime import timedelta
        dt2 = dt + timedelta(days=1)
        merc2 = ephem.Mercury()
        merc2.compute(dt2.strftime("%Y/%m/%d"))
        lon2 = math.degrees(merc2.hlong)

        # Если долгота убывает — ретроград
        diff = lon2 - lon1
        if diff > 180:
            diff -= 360
        elif diff < -180:
            diff += 360

        is_retrograde = diff < 0
        return {
            "is_retrograde": is_retrograde,
            "status": "🔄 Ретроградный Меркурий" if is_retrograde else "✅ Меркурий прямой",
            "advice": (
                "Избегай подписания контрактов, покупок техники, важных переговоров. "
                "Время для переосмысления и завершения дел." if is_retrograde
                else "Благоприятное время для общения, сделок и новых проектов."
            ),
        }
    except Exception:
        return {"is_retrograde": False, "status": "неизвестно", "advice": ""}


def calculate_life_path(birth_date: date) -> dict:
    """Число жизненного пути (нумерология)."""
    digits = [int(d) for d in birth_date.strftime("%d%m%Y") if d.isdigit()]
    total = sum(digits)
    while total > 9 and total not in (11, 22, 33):
        total = sum(int(d) for d in str(total))

    descriptions = {
        1: "Лидер и первопроходец. Независимость, инициатива, амбиции.",
        2: "Дипломат и миротворец. Сотрудничество, интуиция, чуткость.",
        3: "Творец и коммуникатор. Самовыражение, оптимизм, креативность.",
        4: "Строитель и организатор. Стабильность, труд, порядок.",
        5: "Искатель свободы. Перемены, авантюризм, адаптивность.",
        6: "Нуртурер и целитель. Ответственность, гармония, семья.",
        7: "Мистик и аналитик. Поиск истины, интроспекция, мудрость.",
        8: "Строитель судьбы. Власть, достижения, материальный успех.",
        9: "Гуманист и мудрец. Служение, сострадание, завершение циклов.",
        11: "Мастер-интуит. Вдохновение, духовность, просветление.",
        22: "Мастер-строитель. Грандиозные планы, реализация мечт.",
        33: "Мастер-учитель. Высшее служение, исцеление, мудрость.",
    }

    return {
        "number": total,
        "description": descriptions.get(total, "Уникальный путь."),
        "is_master": total in (11, 22, 33),
    }
