import os
import logging
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, executor
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from googlesearch import search

# --- Render uchun Web Server (Keep Alive) ---
app = Flask('')

@app.route('/')
def home():
    return "Findly Bot is running!"

def run_web():
    # Render avtomatik PORT beradi, agar bermasa 8080 ishlatiladi
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# --- Bot Sozlamalari ---
API_TOKEN = os.getenv('BOT_TOKEN')
logging.basicConfig(level=logging.INFO)

if not API_TOKEN:
    print("XATO: BOT_TOKEN topilmadi! Render muhitini tekshiring.")
    exit()

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# --- FSM (Holatlar) ---
class SearchSteps(StatesGroup):
    language = State()
    subject = State()
    category = State()
    topic = State()

# --- Matnlar lug'ati ---
MESSAGES = {
    'uz': {
        'welcome': "Assalomu aleykum, botga xush kelibsiz. Qaysi fan uchun materiallar izlamoqdasiz? Iltimos fan nomini hech qanday qistartirishlarsiz va imloviy xatolarsiz yozing, shunda o'zingizga kerakli material topishingiz ancha osonlashadi!!!",
        'cat_select': "Sizga kerakli material turini tanlang:",
        'topic_ask': "Sizga kerakli mavzu?",
        'not_found': "Uzur ma'lumot topilmadi😞",
        'buttons': ["Maqola/Dissertatsiya", "Kitob", "Prezentatsiya", "Video rolik"]
    },
    'ru': {
        'welcome': "Здравствуйте, добро пожаловать в бот. По какому предметu вы ищете материалы? Пожалуйста, пишите название предмета без сокращений и ошибок!",
        'cat_select': "Выберите нужный тип материала:",
        'topic_ask': "Какая тема вам нужна?",
        'not_found': "Извините, информация не найдена😞",
        'buttons': ["Статья/Диссертация", "Книга", "Презентация", "Видео ролик"]
    },
    'eng': {
        'welcome': "Hello, welcome to the bot. Which subject are you looking for materials for? Please write the subject name without abbreviations or spelling errors!",
        'cat_select': "Select the type of material you need:",
        'topic_ask': "Which topic do you need?",
        'not_found': "Sorry, no information found😞",
        'buttons': ["Article/Dissertation", "Book", "Presentation", "Video clip"]
    }
}

# --- Handlers (Buyruqlar) ---
@dp.message_handler(commands=['start'], state='*')
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("O'zingizga kerakli tilni tanlang:\n/uz - O'zbekcha\n/ru - Русский\n/eng - English")
    await SearchSteps.language.set()

@dp.message_handler(commands=['uz', 'ru', 'eng'], state=SearchSteps.language)
async def set_lang(message: types.Message, state: FSMContext):
    lang = message.text[1:]
    await state.update_data(lang=lang)
    await message.answer(MESSAGES[lang]['welcome'])
    await SearchSteps.subject.set()

@dp.message_handler(state=SearchSteps.subject)
async def get_subject(message: types.Message, state: FSMContext):
    await state.update_data(subject=message.text)
    data = await state.get_data()
    lang = data['lang']
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for btn in MESSAGES[lang]['buttons']:
        markup.add(btn)
        
    await message.answer(MESSAGES[lang]['cat_select'], reply_markup=markup)
    await SearchSteps.category.set()

@dp.message_handler(state=SearchSteps.category)
async def get_category(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    data = await state.get_data()
    await message.answer(MESSAGES[data['lang']]['topic_ask'], reply_markup=types.ReplyKeyboardRemove())
    await SearchSteps.topic.set()

@dp.message_handler(state=SearchSteps.topic)
async def search_engine(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data['lang']
    subject = data['subject']
    category = data['category']
    topic = message.text
    
    query = f"{subject} {topic} {category}"
    
    # Qidiruvni boyitish
    if "Prezentatsiya" in category or "Presentation" in category:
        query += " filetype:pptx OR filetype:pdf"
    elif "Video" in category:
        query = f"site:youtube.com {subject} {topic}"

    await message.answer("🔍 Findly qidirmoqda...")
    
    try:
        # googlesearch-python orqali qidiruv
        search_results = list(search(query, num_results=5, lang=lang))
        
        if search_results:
            text = "✅ Topilgan materiallar:\n\n"
            for i, link in enumerate(search_results, 1):
                text += f"{i}. {link}\n"
            await message.answer(text)
        else:
            await message.answer(MESSAGES[lang]['not_found'])
    except Exception as e:
        logging.error(f"Error: {e}")
        await message.answer(MESSAGES[lang]['not_found'])
    
    await state.finish()

if __name__ == '__main__':
    keep_alive()
    executor.start_polling(dp, skip_updates=True)