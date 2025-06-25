from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
import os
import requests

load_dotenv()

bot = Bot(token=os.getenv("TOKEN"))
dp = Dispatcher()

class Rezume(StatesGroup):
    FIO = State()
    age = State()
    direction = State()
    confirm = State()
    q1 = State()
    q2 = State()
    q3 = State()
    end = State()


def get_confirm_keyboard(prefix: str) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text="Да", callback_data=f"{prefix}_yes"),
        types.InlineKeyboardButton(text="Нет", callback_data=f"{prefix}_no")
    )
    return builder.as_markup()


def generate_question() -> str:
    prompt = {
        "modelUri": "gpt://b1gmeo6ccbir27d9ur13/yandexgpt-lite",
        "completionOptions": {"stream": False, "temperature": 0.6, "maxTokens": "2000"},
        "messages": [
            {
                "role": "user",
                "text": (
                    "Сгенерируй вопрос по программированию, на который будет ответ да или нет. "
                    "Вопрос должен содержать пример кода в блоке, чтобы пользователь видел контекст. "
                    "Используй синтаксис Markdown для выделения блока кода. "
                    "Например:\n```python\n"
                    "def foo():\n"
                    "    i = 0\n"
                    "    return i\n"
                    "```\n"
                )
            }
        ]
    }
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {os.getenv('YANDEX_API_KEY')}"
    }
    resp = requests.post(url, headers=headers, json=prompt)
    data = resp.json()
    try:
        return data['result']['alternatives'][0]['message']['text']
    except Exception:
        return "Не удалось получить вопрос. Попробуйте позже."


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.set_state(Rezume.FIO)
    await message.answer("Здравствуйте, Вы заполняете заявку на участие в отборе на учебу в МТС.")
    await message.answer("Напишите Ваше ФИО в именительном падеже.")


@dp.message(StateFilter(Rezume.FIO))
async def process_fio(message: types.Message, state: FSMContext):
    await state.update_data(FIO=message.text)
    await state.set_state(Rezume.age)
    await message.answer("Напишите Ваш возраст (только цифру)")


@dp.message(StateFilter(Rezume.age))
async def process_age(message: types.Message, state: FSMContext):
    await state.update_data(age=message.text)
    await state.set_state(Rezume.direction)
    await message.answer("Напишите Ваше направление.")


@dp.message(StateFilter(Rezume.direction))
async def process_direction(message: types.Message, state: FSMContext):
    await state.update_data(direction=message.text)
    await state.set_state(Rezume.confirm)
    data = await state.get_data()
    await message.answer(
        f"Ваше резюме \nФИО: {data['FIO']}\nВозраст: {data['age']} лет\nНаправление: {data['direction']}\nПодтвердить заявку?",
        reply_markup=get_confirm_keyboard("confirm")
    )


@dp.callback_query(StateFilter(Rezume.confirm))
async def process_confirm(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.data == "confirm_yes":
        data = await state.get_data()
        with open("resume.txt", "w") as f:
            f.write(f"{data['FIO']}, {data['age']}, {data['direction']}" )
        await callback.message.answer("✅ Ваша заявка успешно оформлена!\nНапишите \"/start2\"")
    else:
        await callback.message.answer("❌ Ваша заявка отклонена")
    await state.clear()


@dp.message(Command("start2"))
async def cmd_start2(message: types.Message, state: FSMContext):
    await state.set_state(Rezume.q1)
    await message.answer("Начать прохождение теста",
        reply_markup=get_confirm_keyboard("start2")
    )


@dp.callback_query(lambda c: c.data == "start2_yes", StateFilter(Rezume.q1))
async def question1(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    text = generate_question()
    await state.set_state(Rezume.q2)
    await callback.message.answer("Первый вопрос:")
    await callback.message.answer(text, parse_mode="Markdown", reply_markup=get_confirm_keyboard("q1"))


@dp.callback_query(lambda c: c.data in ["q1_yes", "q1_no"], StateFilter(Rezume.q2))
async def question2(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    text = generate_question()
    await state.set_state(Rezume.q3)
    await callback.message.answer("Второй вопрос:")
    await callback.message.answer(text, parse_mode="Markdown", reply_markup=get_confirm_keyboard("q2"))


@dp.callback_query(lambda c: c.data in ["q2_yes", "q2_no"], StateFilter(Rezume.q3))
async def question3(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    text = generate_question()
    await state.set_state(Rezume.end)
    await callback.message.answer("Третий вопрос:")
    await callback.message.answer(text, parse_mode="Markdown", reply_markup=get_confirm_keyboard("q3"))


@dp.callback_query(lambda c: c.data in ["q3_yes", "q3_no"], StateFilter(Rezume.end))
async def finish_test(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Тестовая часть пройдена")
    await state.clear()


dp.run_polling(bot)