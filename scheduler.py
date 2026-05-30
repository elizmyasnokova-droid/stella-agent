"""
Scheduler — ежедневный гороскоп и лунные уведомления.
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from config import TIMEZONE
import database as db

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone=TIMEZONE)


async def send_daily_horoscope(bot):
    """Утренний астро-дайджест всем пользователям."""
    from astro_calc import get_moon_phase, get_planet_positions, get_mercury_retrograde
    from datetime import datetime
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic()
    user_ids = await db.get_all_users()
    if not user_ids:
        return

    # Получаем астрологические данные
    moon = get_moon_phase()
    mercury = get_mercury_retrograde()
    planets = get_planet_positions()

    planets_str = ", ".join(
        f"{p} в {info['sign']}" for p, info in list(planets.items())[:5]
    )

    logger.info(f"Daily horoscope: {len(user_ids)} users")

    for user_id in user_ids[:50]:  # Лимит 50 в день
        user = await db.get_user(user_id)
        if not user:
            continue

        sun_sign = user.get("sun_sign", "")
        name = user.get("first_name", "")
        if not sun_sign:
            continue

        try:
            prompt = (
                f"Составь краткий астро-дайджест на сегодня для {name}, знак {sun_sign}. "
                f"Луна: {moon['phase']} в {moon['moon_sign']}. "
                f"Планеты: {planets_str}. "
                f"Меркурий: {'ретроградный' if mercury['is_retrograde'] else 'прямой'}. "
                "Формат: 3-4 предложения с практическими советами на день. "
                "Стиль: вдохновляющий но конкретный. Используй эмодзи."
            )
            response = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.content[0].text
            await bot.send_message(
                user_id,
                f"🌟 *Астро-дайджест на сегодня*\n\n{text}",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Daily horoscope failed for {user_id}: {e}")


async def send_moon_alert(bot, phase_name: str):
    """Уведомление о смене фазы Луны."""
    from astro_calc import get_moon_phase
    moon = get_moon_phase()
    user_ids = await db.get_all_users()

    message = (
        f"🌙 *{moon['phase']}*\n\n"
        f"Луна в {moon['moon_sign']} — {moon['description']}\n\n"
        f"💫 Энергия: *{moon['energy']}*"
    )

    for user_id in user_ids:
        try:
            await bot.send_message(user_id, message, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"Moon alert failed for {user_id}: {e}")


def setup_scheduler(bot):
    # Ежедневный гороскоп в 8:00
    scheduler.add_job(
        send_daily_horoscope,
        CronTrigger(hour=8, minute=0),
        args=[bot],
        id="daily_horoscope",
        replace_existing=True,
    )
    # Уведомление о новолунии и полнолунии
    scheduler.add_job(
        send_moon_alert,
        CronTrigger(hour=10, minute=0),
        args=[bot, "check"],
        id="moon_alert",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler started ({TIMEZONE})")
    return scheduler
