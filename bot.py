import asyncio
import logging
import os
import secrets

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

# Set BOT_TOKEN as an environment variable before running.
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

# In-memory sessions: answers are lost when the bot process stops.
SESSIONS = {}
SECOND_SESSIONS = {}

# ---------------------------------------------------------------------
# TEST 1: Энергетический баланс и телесные маркеры (original test)
# ---------------------------------------------------------------------

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
        kb.button(text=mark + code, callback_data=f"t:{index}:{code}")
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
    options_text = "\n\n" + "\n".join(
        f"<b>{code})</b> {label}" for code, label in q["options"]
    )
    if chosen:
        selected_text = "\n\n<i>Выбрано: " + ", ".join(sorted(chosen)) + "</i>"
    else:
        selected_text = "\n\n<i>Отметьте один или несколько вариантов кнопками ниже.</i>"
    return f"🌿 <b>{q['title']}</b>\n\n{q['question']}{options_text}{selected_text}"


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
    parts = [
        "🌿 <b>Ваш результат</b>\n",
        "Это ориентир для самонаблюдения, а не диагноз. Результат отражает только выбранные ответы и не устанавливает причину ощущений.\n",
    ]
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
    kb.button(text="🏠 Главное меню", callback_data="menu")
    kb.button(text="ℹ️ О тесте", callback_data="about")
    kb.adjust(1)
    return kb.as_markup()


# ---------------------------------------------------------------------
# TEST 2: Раскрытие Женского Полюса (new test)
# ---------------------------------------------------------------------

SECOND_INTRO = (
    "✨ <b>Тест «Раскрытие Женского Полюса»</b>\n\n"
    "Честно ответьте на 9 вопросов. Выбирайте вариант (А, Б или В), "
    "который лучше всего отражает ваше поведение за последний месяц.\n\n"
    "В каждом вопросе выберите один вариант ответа. "
    "Тест предназначен для саморефлексии и не является медицинской или психологической диагностикой.\n\n"
    "Нажмите «Начать второй тест», когда будете готовы."
)

SECOND_QUESTIONS = [
    {
        "title": "Блок 1: Сигналы тела (Физический план)",
        "question": "1. Как вы понимаете, что пора отдохнуть?",
        "options": [
            ("А", "По графику или когда чувствую легкую приятную расслабленность, переключаюсь на хобби."),
            ("Б", "Когда начинает болеть голова, падает концентрация или раздражают мелочи."),
            ("В", "Когда буквально с ног валюсь, заболеваю или не могу поднять себя с кровати."),
        ],
    },
    {
        "title": "Блок 1: Сигналы тела (Физический план)",
        "question": "2. Каковы ваши отношения с качественным сном и телесными удовольствиями (массаж, ванна, уход)?",
        "options": [
            ("А", "Это регулярный приоритет. Мое тело — мой храм, я балую его без повода."),
            ("Б", "Включаю в расписание, только если сильно устала или «заслужила» тяжелой неделей."),
            ("В", "На это вечно нет времени/денег, это кажется непозволительной роскошью."),
        ],
    },
    {
        "title": "Блок 1: Сигналы тела (Физический план)",
        "question": "3. Что происходит с вашим телом, когда вы просто садитесь на диван посреди дня без телефона и дел?",
        "options": [
            ("А", "Наслаждаюсь моментом, расслабляюсь, чувствую текучесть и покой."),
            ("Б", "Начинаю прокручивать в голове список задач, испытываю легкий дискомфорт."),
            ("В", "Внутри всё сжимается, подскакиваю от чувства вины («я сижу без дела!»)."),
        ],
    },
    {
        "title": "Блок 2: Психологические границы (Ментальный план)",
        "question": "4. Умеете ли вы говорить «нет» без последующего чувства вины?",
        "options": [
            ("А", "Да, если это нарушает мой баланс и забирает ресурс."),
            ("Б", "Говорю «нет», но потом долго прокручиваю в голове, правильно ли я поступила."),
            ("В", "Соглашаюсь через силу, тащу всё на себе, а потом тихо злюсь на тех, кто попросил."),
        ],
    },
    {
        "title": "Блок 2: Психологические границы (Ментальный план)",
        "question": "5. Какая установка откликается вам сильнее всего при мысли об отдыхе?",
        "options": [
            ("А", "«Отдых — это наполнение ресурсом, чтобы жить в удовольствие»."),
            ("Б", "«Сначала дело — потом безделье. Нужно сначала всё доделать»."),
            ("В", "«Если я расслаблюсь, всё рухнет/я стану ленивой неудачницей»."),
        ],
    },
    {
        "title": "Блок 2: Психологические границы (Ментальный план)",
        "question": "6. Как вы реагируете, когда близкие или коллеги просят о помощи в ваш выходной?",
        "options": [
            ("А", "Мягко обозначаю, что сейчас мое время, и предлагаю перенести на рабочие часы."),
            ("Б", "Помогаю, жертвуя своим сном или планами, но с внутренним вздохом."),
            ("В", "Бросаю всё и бегу спасать, даже если внутри меня всё кричит от усталости."),
        ],
    },
    {
        "title": "Блок 3: Раскрытие Женского Полюса (Энергетический план)",
        "question": "7. Из какого состояния вы чаще всего действуете в течение дня?",
        "options": [
            ("А", "Из «Хочу» и «Мне в радость» (состояние потока, принятия, созидания)."),
            ("Б", "Балансирую между «Надо» и «Хочу», но «Надо» часто перевешивает."),
            ("В", "Только из «Надо», «Должна», «Кто, если не я» (жесткий контроль, достигаторство)."),
        ],
    },
    {
        "title": "Блок 3: Раскрытие Женского Полюса (Энергетический план)",
        "question": "8. Насколько легко вы принимаете подарки, комплименты и помощь от мужчин/окружающих?",
        "options": [
            ("А", "С благодарностью и удовольствием, чувствую себя достойной этого по праву рождения."),
            ("Б", "Принимаю, но сразу чувствую себя «должной» ответить взаимностью."),
            ("В", "Отказываюсь, смущаюсь или говорю: «Да ладно, я сама справлюсь»."),
        ],
    },
    {
        "title": "Блок 3: Раскрытие Женского Полюса (Энергетический план)",
        "question": "9. Когда вы в последний раз занимались творчеством, флиртовали или просто дурачились без практической цели?",
        "options": [
            ("А", "На этой неделе / регулярно. Это естественная часть моей жизни."),
            ("Б", "Иногда бывает, но редко, обычно под хорошее настроение в отпуске."),
            ("В", "Уже не помню, когда такое было, жизнь — слишком серьезная штука."),
        ],
    },
]

SECOND_RESULTS = {
    "А": (
        "✨ <b>Уровень «Потоковая Богиня»</b>\n"
        "<b>Высокий уровень раскрытия женского полюса</b>\n\n"
        "Вы глубоко соединены со своей женской природой. Для вас отдых — это не награда за каторжный труд, а естественное состояние бытия. Вы умеете наполняться изнутри, чувствуете микросигналы тела и останавливаетесь до наступления истощения. Ваш женский полюс раскрыт: вы притягиваете блага не через пахоту, а через расслабление и магнетизм.\n\n"
        "<b>Ваш вызов:</b> Удерживать этот баланс во время внешних кризисов и не скатываться в спасательство."
    ),
    "Б": (
        "⚖️ <b>Уровень «Балансирующая Амазонка»</b>\n"
        "<b>Переходный этап</b>\n\n"
        "Вы уже понимаете ценность женской энергии, но старые социальные программы («успешный успех», контроль, заслуживание любви через труд) еще сильны. Вы даете себе отпуск, только когда лампочка ресурса начинает мигать красным. Вы отдыхаете, но часто с привкусом фоновой тревоги или вины.\n\n"
        "<b>Ваш вызов:</b> Учиться переходить от концепции «отдых нужно заслужить» к концепции «я ценна сама по себе». Начните планировать отдых первым в своем календаре, а работу — встраивать вокруг него."
    ),
    "В": (
        "🚨 <b>Уровень «Железная Леди на грани»</b>\n"
        "<b>Глубокий дефицит и мужской полюс</b>\n\n"
        "Вы находитесь в тотальном мужском полюсе (гиперконтроль, выживание, достигаторство). Ваше тело работает на износ и способно лечь отдохнуть только через болезнь или полный эмоциональный коллапс. Вы запрещаете себе уязвимость, слабость и принятие помощи. Женский полюс заблокирован страхом потерять контроль.\n\n"
        "<b>Ваш вызов:</b> Это зона SOS. Вам жизненно необходимо передавать ответственность, просить о помощи и учиться самым базовым телесным практикам расслабления (дыхание, ванны) хотя бы по 10 минут в день."
    ),
}


def get_second_session(user_id: int):
    if user_id not in SECOND_SESSIONS:
        SECOND_SESSIONS[user_id] = {
            "index": 0,
            "answers": [None for _ in SECOND_QUESTIONS],
        }
    return SECOND_SESSIONS[user_id]


def second_question_keyboard(index: int, selected: str | None):
    q = SECOND_QUESTIONS[index]
    kb = InlineKeyboardBuilder()
    for code, label in q["options"]:
        mark = "☑️ " if code == selected else "▫️ "
        kb.button(text=f"{mark}{code}", callback_data=f"q2:{index}:{code}")
    kb.adjust(1)

    if index > 0:
        kb.button(text="⬅️ Назад", callback_data=f"b2:{index}")
    if index < len(SECOND_QUESTIONS) - 1:
        kb.button(text="Далее ➡️", callback_data=f"n2:{index}")
    else:
        kb.button(text="✨ Получить результат", callback_data=f"f2:{index}")
    kb.button(text="🏠 Главное меню", callback_data="menu")
    kb.adjust(1)
    return kb.as_markup()


def render_second_question(index: int, answers: list):
    q = SECOND_QUESTIONS[index]
    selected = answers[index]
    selected_text = (
        f"\n\n<i>Ваш ответ: {selected}</i>"
        if selected
        else "\n\n<i>Выберите один вариант ответа.</i>"
    )
    return f"✨ <b>{q['title']}</b>\n\n<b>{q['question']}</b>\n\n" + "\n".join(
        f"<b>{code})</b> {label}" for code, label in q["options"]
    ) + selected_text


def make_second_result(answers):
    counts = {letter: answers.count(letter) for letter in ("А", "Б", "В")}
    highest = max(counts.values())
    winners = [letter for letter, count in counts.items() if count == highest]

    if len(winners) == 1:
        result = SECOND_RESULTS[winners[0]]
    else:
        tied_names = {
            "А": "«Потоковая Богиня»",
            "Б": "«Балансирующая Амазонка»",
            "В": "«Железная Леди на грани»",
        }
        names = ", ".join(tied_names[letter] for letter in winners)
        result = (
            "⚖️ <b>Смешанный результат — несколько ведущих тенденций</b>\n\n"
            f"У вас одинаковое количество ответов у нескольких вариантов: {names}.\n"
            "Это значит, что по этому тесту нельзя выделить один преобладающий уровень. "
            "Ваши ответы отражают сочетание разных способов реагирования в разных ситуациях.\n\n"
            "<b>Ваш ориентир:</b> перечитайте описания совпавших уровней и отметьте, "
            "какие фрагменты больше всего откликаются именно сейчас. Отнеситесь к результату "
            "как к подсказке для самонаблюдения, а не как к оценке или диагнозу."
        )

    count_line = (
        f"\n\n<b>Ваши ответы:</b> А — {counts['А']}, Б — {counts['Б']}, В — {counts['В']}."
    )
    disclaimer = (
        "\n\n<i>Результат этого авторского теста предназначен для саморефлексии "
        "и не является медицинской или психологической диагностикой.</i>"
    )
    return "✨ <b>Результаты теста «Раскрытие Женского Полюса»</b>\n\n" + result + count_line + disclaimer


def second_result_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Пройти второй тест ещё раз", callback_data="restart2")
    kb.button(text="🏠 Главное меню", callback_data="menu")
    kb.adjust(1)
    return kb.as_markup()


# ---------------------------------------------------------------------
# Main menu and handlers
# ---------------------------------------------------------------------

def main_menu_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🌿 Первый тест — Энергетический баланс", callback_data="choose:first")
    kb.button(text="✨ Второй тест — Раскрытие Женского Полюса", callback_data="choose:second")
    kb.adjust(1)
    return kb.as_markup()


@dp.message(CommandStart())
async def start(message: Message):
    SESSIONS.pop(message.from_user.id, None)
    SECOND_SESSIONS.pop(message.from_user.id, None)
    await message.answer(
        "Добро пожаловать! 🌷\n\nВыберите тест, который хотите пройти:",
        reply_markup=main_menu_keyboard(),
    )


@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "🌿 <b>Команды бота</b>\n/start — главное меню и начало заново\n/help — помощь\n\n"
        "Выберите нужный тест в главном меню и отвечайте на вопросы кнопками.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


@dp.callback_query(F.data == "menu")
async def show_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🌷 <b>Главное меню</b>\n\nВыберите тест:",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data == "choose:first")
async def choose_first_test(callback: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="🌿 Начать первый тест", callback_data="begin")
    kb.button(text="🏠 Главное меню", callback_data="menu")
    kb.adjust(1)
    await callback.message.edit_text(INTRO, reply_markup=kb.as_markup(), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "choose:second")
async def choose_second_test(callback: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="✨ Начать второй тест", callback_data="begin2")
    kb.button(text="🏠 Главное меню", callback_data="menu")
    kb.adjust(1)
    await callback.message.edit_text(SECOND_INTRO, reply_markup=kb.as_markup(), parse_mode="HTML")
    await callback.answer()


# First test handlers (original flow)
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
        show_alert=True,
    )


# Second test handlers
@dp.callback_query(F.data == "begin2")
async def begin_second_test(callback: CallbackQuery):
    session = get_second_session(callback.from_user.id)
    session["index"] = 0
    session["answers"] = [None for _ in SECOND_QUESTIONS]
    await callback.message.edit_text(
        render_second_question(0, session["answers"]),
        reply_markup=second_question_keyboard(0, None),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("q2:"))
async def choose_second_answer(callback: CallbackQuery):
    _, idx_str, code = callback.data.split(":")
    idx = int(idx_str)
    session = get_second_session(callback.from_user.id)
    if idx != session["index"]:
        await callback.answer("Сначала перейдите к текущему вопросу.", show_alert=False)
        return
    if code not in {"А", "Б", "В"}:
        await callback.answer("Неизвестный вариант ответа.", show_alert=True)
        return
    session["answers"][idx] = code
    await callback.message.edit_text(
        render_second_question(idx, session["answers"]),
        reply_markup=second_question_keyboard(idx, code),
        parse_mode="HTML",
    )
    await callback.answer("Ответ сохранён")


@dp.callback_query(F.data.startswith("n2:"))
async def next_second_question(callback: CallbackQuery):
    _, idx_str = callback.data.split(":")
    idx = int(idx_str)
    session = get_second_session(callback.from_user.id)
    if not session["answers"][idx]:
        await callback.answer("Сначала выберите один вариант ответа.", show_alert=True)
        return
    session["index"] = min(idx + 1, len(SECOND_QUESTIONS) - 1)
    new_idx = session["index"]
    await callback.message.edit_text(
        render_second_question(new_idx, session["answers"]),
        reply_markup=second_question_keyboard(new_idx, session["answers"][new_idx]),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("b2:"))
async def previous_second_question(callback: CallbackQuery):
    _, idx_str = callback.data.split(":")
    idx = int(idx_str)
    session = get_second_session(callback.from_user.id)
    session["index"] = max(idx - 1, 0)
    new_idx = session["index"]
    await callback.message.edit_text(
        render_second_question(new_idx, session["answers"]),
        reply_markup=second_question_keyboard(new_idx, session["answers"][new_idx]),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("f2:"))
async def finish_second_test(callback: CallbackQuery):
    _, idx_str = callback.data.split(":")
    idx = int(idx_str)
    session = get_second_session(callback.from_user.id)
    if not session["answers"][idx]:
        await callback.answer("Выберите один вариант ответа.", show_alert=True)
        return
    unanswered = [str(i + 1) for i, answer in enumerate(session["answers"]) if not answer]
    if unanswered:
        await callback.answer(
            "Ответьте на все вопросы. Остались: " + ", ".join(unanswered),
            show_alert=True,
        )
        return
    result = make_second_result(session["answers"])
    await callback.message.edit_text(
        result,
        reply_markup=second_result_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer("Второй тест завершён")


@dp.callback_query(F.data == "restart2")
async def restart_second_test(callback: CallbackQuery):
    session = get_second_session(callback.from_user.id)
    session["index"] = 0
    session["answers"] = [None for _ in SECOND_QUESTIONS]
    await callback.message.edit_text(
        render_second_question(0, session["answers"]),
        reply_markup=second_question_keyboard(0, None),
        parse_mode="HTML",
    )
    await callback.answer("Начинаем второй тест заново")


# ---------------------------------------------------------------------
# Render deployment: Telegram sends updates to this public HTTPS webhook.
# ---------------------------------------------------------------------

from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

WEBHOOK_PATH = "/telegram/webhook"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET") or secrets.token_urlsafe(32)


async def health(request: web.Request) -> web.Response:
    return web.Response(text="Telegram bot is running.")


@web.middleware
async def log_webhook_requests(request: web.Request, handler):
    """Log webhook arrival and response without recording message contents or secrets."""
    if request.path == WEBHOOK_PATH:
        request_id = request.headers.get("CF-Ray", "not-provided")
        logging.info(
            "Incoming Telegram webhook: method=%s path=%s cf_ray=%s",
            request.method, request.path, request_id,
        )
        try:
            response = await handler(request)
        except Exception:
            logging.exception("Telegram webhook handler failed: cf_ray=%s", request_id)
            raise
        logging.info(
            "Telegram webhook response: status=%s cf_ray=%s",
            response.status, request_id,
        )
        return response
    return await handler(request)


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
    app = web.Application(middlewares=[log_webhook_requests])
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
            drop_pending_updates=False,
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
