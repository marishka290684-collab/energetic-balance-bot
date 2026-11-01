import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

# Set BOT_TOKEN as an environment variable before running.
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

# In-memory sessions for simple testing. Answers are lost when the bot process stops.
SESSIONS = {}

QUESTIONS = [
    {
        "title": "Блок 1 из 3 · Ресурсное состояние",
        "question": "1/6. Какое ощущение в теле чаще возникает при мысли о будущем или текущих делах?",
        "multi": True,
        "options": [
            ("A", "🔴 Сжатие в груди, тяжело дышать, «ком» в горле"),
            ("Б", "🔵 Напряжение в челюсти, плечах и шее"),
            ("В", "🟡 Слабость в ногах, мало сил, ощущение отсутствия опоры"),
            ("Г", "🟢 Лёгкость, тепло в теле, свободное дыхание"),
        ],
    },
    {
        "title": "Блок 1 из 3 · Ресурсное состояние",
        "question": "2/6. Как ваше тело реагирует на усталость?",
        "multi": True,
        "options": [
            ("A", "🔴 Слёзливость, хочется свернуться калачиком, пустота в животе"),
            ("Б", "🔵 Не замечаю усталости, пока не становится совсем плохо"),
            ("В", "🟡 Ватность в теле, трудно двигаться, апатия"),
            ("Г", "🟢 Вовремя замечаю усталость и даю себе отдых"),
        ],
    },
    {
        "title": "Блок 2 из 3 · Контакт с телом и эмоциями",
        "question": "3/6. Что вы ощущаете в области таза и нижней части живота?",
        "multi": True,
        "options": [
            ("A", "❌ Холод, жёсткость, зажимы или частые боли"),
            ("Б", "⚠️ Пустоту или слабую связь с этой областью"),
            ("В", "✨ Тепло, мягкость, расслабление"),
        ],
    },
    {
        "title": "Блок 2 из 3 · Контакт с телом и эмоциями",
        "question": "4/6. Как вы проявляете эмоции на физическом уровне?",
        "multi": True,
        "options": [
            ("A", "❌ Сдерживаю слёзы или смех, держу переживания внутри"),
            ("Б", "⚠️ Часто тревожусь, эмоции захлёстывают"),
            ("В", "✨ Могу выражать эмоции и постепенно возвращаюсь к равновесию"),
        ],
    },
    {
        "title": "Блок 3 из 3 · Границы и внутренняя опора",
        "question": "5/6. Как вы ощущаете спину и осанку?",
        "multi": True,
        "options": [
            ("A", "❌ Сильное напряжение спины или частая боль"),
            ("Б", "⚠️ Сутулость, вялость, ощущение бессилия"),
            ("В", "✨ Устойчивая, но гибкая осанка; ощущение опоры"),
        ],
    },
    {
        "title": "Блок 3 из 3 · Границы и внутренняя опора",
        "question": "6/6. Как вы обычно защищаете личные границы?",
        "multi": True,
        "options": [
            ("A", "❌ Резко напрягаюсь, перехожу в оборону или повышаю голос"),
            ("Б", "⚠️ Сжимаюсь, избегаю контакта, мне трудно отказать"),
            ("В", "✨ Стараюсь говорить спокойно и уверенно"),
        ],
    },
]

# Option codes are local to each question. "A", "Б", "В", "Г" match the supplied test.
CONCERN_CODES = {
    0: {"A", "Б", "В"}, 1: {"A", "Б", "В"},
    2: {"A", "Б"}, 3: {"A", "Б"}, 4: {"A", "Б"}, 5: {"A", "Б"},
}
POSITIVE_CODES = {
    0: {"Г"}, 1: {"Г"},
    2: {"В"}, 3: {"В"}, 4: {"В"}, 5: {"В"},
}

INTRO = (
    "🌿 <b>Энергетический баланс и телесные маркеры</b>\n\n"
    "Это короткий тест для самонаблюдения за ощущениями за последние 1–2 месяца. "
    "В каждом вопросе можно выбрать один или несколько вариантов.\n\n"
    "Важно: тест не является медицинской или психологической диагностикой. "
    "Телесные ощущения сами по себе не позволяют достоверно определить психологическое состояние "
    "или «энергетические блоки». Если симптомы новые, сильные, сохраняются или беспокоят вас, "
    "обратитесь к квалифицированному специалисту.\n\n"
    "Нажмите «Начать тест», когда будете готовы."
)

def get_session(user_id: int):
    if user_id not in SESSIONS:
        SESSIONS[user_id] = {"index": 0, "answers": [set() for _ in QUESTIONS]}
    return SESSIONS[user_id]

def question_keyboard(index: int, selected: set[str]):
    q = QUESTIONS[index]
    kb = InlineKeyboardBuilder()
    for code, label in q["options"]:
        mark = "☑️ " if code in selected else "▫️ "
        kb.button(text=mark + label, callback_data=f"t:{index}:{code}")
    kb.adjust(1)
    kb.button(text="🧹 Снять выбор", callback_data=f"clear:{index}")
    nav = []
    if index > 0:
        nav.append(("⬅️ Назад", f"back:{index}"))
    if index < len(QUESTIONS) - 1:
        nav.append(("Далее ➡️", f"next:{index}"))
    else:
        nav.append(("🌿 Посмотреть результат", f"finish:{index}"))
    for text, data in nav:
        kb.button(text=text, callback_data=data)
    kb.adjust(1)
    return kb.as_markup()

def render_question(index: int, answers: list[set[str]]) -> str:
    q = QUESTIONS[index]
    chosen = answers[index]
    selected_text = ""
    if chosen:
        selected_text = "\n\n<i>Выбрано: " + ", ".join(chosen) + "</i>"
    else:
        selected_text = "\n\n<i>Пока ничего не выбрано. Можно отметить несколько вариантов.</i>"
    return f"🌿 <b>{q['title']}</b>\n\n{q['question']}{selected_text}"

def assess_block(question_indices, answers):
    concern = 0
    positive = 0
    for i in question_indices:
        concern += len(answers[i] & CONCERN_CODES[i])
        positive += len(answers[i] & POSITIVE_CODES[i])
    if concern == 0 and positive > 0:
        state = "🟢 Больше поддерживающих маркеров"
        desc = "В выбранных ответах больше признаков контакта с потребностями и ресурсами. Полезно сохранять то, что уже помогает вам."
        tips = [
            "Продолжайте замечать ранние признаки усталости и делать паузы.",
            "Поддерживайте регулярный сон, питание, движение и отдых.",
        ]
    elif concern > positive:
        state = "🟡 Больше сигналов напряжения или неудовлетворённых потребностей"
        desc = "Вы отметили больше вариантов, которые могут отражать напряжение, усталость или трудности с самоподдержкой. Это повод мягко присмотреться к своему состоянию, а не доказательство какого-либо нарушения."
        tips = [
            "Выберите один небольшой шаг на ближайшие дни: короткая прогулка, спокойное дыхание без усилия или пауза без экрана.",
            "Попробуйте замечать, в каких ситуациях ощущения усиливаются и что помогает им ослабнуть.",
            "Если симптомы частые, сильные или мешают повседневной жизни, обсудите их с врачом или психологом.",
        ]
    elif concern == positive:
        state = "🟡 Смешанная картина"
        desc = "В ответах одновременно присутствуют поддерживающие маркеры и признаки напряжения. Самочувствие может меняться в зависимости от обстоятельств."
        tips = [
            "Отметьте, какие условия помогают вам чувствовать себя спокойнее и устойчивее.",
            "Не требуйте от себя постоянного равновесия: отдых и поддержка нужны всем.",
        ]
    else:
        state = "🌱 Есть и опора, и зоны внимания"
        desc = "В выбранных ответах есть поддерживающие признаки, но также отмечены некоторые сигналы напряжения. Можно опираться на то, что работает, и уделить внимание оставшимся потребностям."
        tips = [
            "Сохраните полезные привычки и добавьте одну небольшую практику восстановления.",
            "Если дискомфорт сохраняется или усиливается, обратитесь за профессиональной консультацией.",
        ]
    return state, desc, tips, concern, positive

def make_result(answers):
    blocks = [
        ("Ресурсное состояние", [0, 1]),
        ("Контакт с телом и эмоциями", [2, 3]),
        ("Границы и внутренняя опора", [4, 5]),
    ]
    parts = ["🌿 <b>Ваш результат</b>\n", "Это ориентир для самонаблюдения, а не диагноз. Результат отражает только выбранные ответы и не устанавливает причину ощущений.\n"]
    for title, indices in blocks:
        state, desc, tips, concern, positive = assess_block(indices, answers)
        parts.append(f"\n<b>{title}</b>\n{state}\n{desc}")
        parts.append("\n<b>Что можно попробовать:</b>\n" + "\n".join(f"• {tip}" for tip in tips))
    parts.append(
        "\n\n<b>Мягкое завершение</b>\n"
        "Спросите себя: «Что мне сейчас нужнее всего — отдых, поддержка, движение, ясность или личное пространство?» "
        "Выберите один посильный шаг, без давления на себя.\n\n"
        "Если вы отмечали боль, затруднённое дыхание или другие физические симптомы, не объясняйте их только стрессом или «энергией»: при выраженных или новых симптомах обратитесь за медицинской помощью."
    )
    return "\n".join(parts)

def result_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Пройти ещё раз", callback_data="restart")
    kb.button(text="ℹ️ О тесте", callback_data="about")
    kb.adjust(1)
    return kb.as_markup()

@dp.message(CommandStart())
async def start(message: Message):
    SESSIONS.pop(message.from_user.id, None)
    kb = InlineKeyboardBuilder()
    kb.button(text="🌿 Начать тест", callback_data="begin")
    kb.adjust(1)
    await message.answer(INTRO, reply_markup=kb.as_markup(), parse_mode="HTML")

@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "🌿 <b>Команды бота</b>\n/start — начать заново\n/help — помощь\n\n"
        "Отвечайте на вопросы кнопками. Можно выбрать несколько ответов; повторное нажатие снимает выбор.",
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "begin")
async def begin(callback: CallbackQuery):
    session = get_session(callback.from_user.id)
    session["index"] = 0
    session["answers"] = [set() for _ in QUESTIONS]
    await callback.message.edit_text(
        render_question(0, session["answers"]),
        reply_markup=question_keyboard(0, session["answers"][0]),
        parse_mode="HTML",
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("t:"))
async def toggle_answer(callback: CallbackQuery):
    _, idx_str, code = callback.data.split(":")
    idx = int(idx_str)
    session = get_session(callback.from_user.id)
    if idx != session["index"]:
        await callback.answer("Сначала перейдите к текущему вопросу.", show_alert=False)
        return
    selected = session["answers"][idx]
    if code in selected:
        selected.remove(code)
    else:
        selected.add(code)
    await callback.message.edit_text(
        render_question(idx, session["answers"]),
        reply_markup=question_keyboard(idx, selected),
        parse_mode="HTML",
    )
    await callback.answer("Выбор обновлён")

@dp.callback_query(F.data.startswith("clear:"))
async def clear_answers(callback: CallbackQuery):
    _, idx_str = callback.data.split(":")
    idx = int(idx_str)
    session = get_session(callback.from_user.id)
    session["answers"][idx].clear()
    await callback.message.edit_text(
        render_question(idx, session["answers"]),
        reply_markup=question_keyboard(idx, session["answers"][idx]),
        parse_mode="HTML",
    )
    await callback.answer("Выбор снят")

@dp.callback_query(F.data.startswith("next:"))
async def next_question(callback: CallbackQuery):
    _, idx_str = callback.data.split(":")
    idx = int(idx_str)
    session = get_session(callback.from_user.id)
    if not session["answers"][idx]:
        await callback.answer("Сначала выберите хотя бы один ответ.", show_alert=True)
        return
    session["index"] = min(idx + 1, len(QUESTIONS) - 1)
    new_idx = session["index"]
    await callback.message.edit_text(
        render_question(new_idx, session["answers"]),
        reply_markup=question_keyboard(new_idx, session["answers"][new_idx]),
        parse_mode="HTML",
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("back:"))
async def previous_question(callback: CallbackQuery):
    _, idx_str = callback.data.split(":")
    idx = int(idx_str)
    session = get_session(callback.from_user.id)
    session["index"] = max(idx - 1, 0)
    new_idx = session["index"]
    await callback.message.edit_text(
        render_question(new_idx, session["answers"]),
        reply_markup=question_keyboard(new_idx, session["answers"][new_idx]),
        parse_mode="HTML",
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("finish:"))
async def finish_test(callback: CallbackQuery):
    _, idx_str = callback.data.split(":")
    idx = int(idx_str)
    session = get_session(callback.from_user.id)
    if not session["answers"][idx]:
        await callback.answer("Выберите хотя бы один ответ.", show_alert=True)
        return
    unanswered = [str(i + 1) for i, a in enumerate(session["answers"]) if not a]
    if unanswered:
        await callback.answer("Ответьте на все вопросы. Остались: " + ", ".join(unanswered), show_alert=True)
        return
    result = make_result(session["answers"])
    # Telegram message limit is 4096 characters; this report is kept comfortably below it.
    await callback.message.edit_text(result, reply_markup=result_keyboard(), parse_mode="HTML")
    await callback.answer("Тест завершён")

@dp.callback_query(F.data == "restart")
async def restart(callback: CallbackQuery):
    session = get_session(callback.from_user.id)
    session["index"] = 0
    session["answers"] = [set() for _ in QUESTIONS]
    await callback.message.edit_text(
        render_question(0, session["answers"]),
        reply_markup=question_keyboard(0, session["answers"][0]),
        parse_mode="HTML",
    )
    await callback.answer("Начинаем заново")

@dp.callback_query(F.data == "about")
async def about(callback: CallbackQuery):
    await callback.answer(
        "Тест предназначен для самонаблюдения и не заменяет медицинскую или психологическую консультацию.",
        show_alert=True
    )

# Render deployment: Telegram sends updates to this public HTTPS webhook.
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
import secrets

WEBHOOK_PATH = "/telegram/webhook"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET") or secrets.token_urlsafe(32)


async def health(request: web.Request) -> web.Response:
    return web.Response(text="Telegram bot is running.")


def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "Не найден BOT_TOKEN. Добавьте BOT_TOKEN в Environment Variables на Render."
        )

    base_url = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
    if not base_url:
        raise RuntimeError(
            "Не найдена RENDER_EXTERNAL_URL. Этот вариант запуска предназначен для Render Web Service."
        )

    bot = Bot(token=BOT_TOKEN)
    app = web.Application()
    app.router.add_get("/", health)

    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET,
    )
    webhook_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    async def on_startup(_app: web.Application):
        webhook_url = f"{base_url}{WEBHOOK_PATH}"
        await bot.set_webhook(
            url=webhook_url,
            secret_token=WEBHOOK_SECRET,
            drop_pending_updates=True,
        )
        logging.info("Telegram webhook configured: %s", webhook_url)

    async def on_cleanup(_app: web.Application):
        await bot.session.close()

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    port = int(os.getenv("PORT", "10000"))
    web.run_app(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
