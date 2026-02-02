import os
import logging
import requests
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, executor
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# --- Render uchun Web Server (Keep Alive) ---
app = Flask('')

@app.route('/')
def home():
    return "Findly AI is live!"

def run_web():
    # Render uchun standart port 10000 qilib belgilandi
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# --- Sozlamalar ---
API_TOKEN = os.getenv('BOT_TOKEN')
G_API_KEY = os.getenv('GOOGLE_API_KEY')
G_CX = os.getenv('GOOGLE_CX')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class SearchSteps(StatesGroup):
    language = State()
    subject = State()
    category = State()
    topic = State()

# --- Lug'at ---
MESSAGES = {
    'uz': {
        'welcome': "Assalomu aleykum, botga xush kelibsiz. Qaysi fan uchun materiallar izlamoqdasiz?",
        'cat_select': "Sizga kerakli material turini tanlang:",
        'topic_ask': "Sizga kerakli mavzu nomi?",
        'searching': "🔍 Findly qidirmoqda...",
        'not_found': "Uzur, ma'lumot topilmadi 😞",
        'buttons': ["Maqola/Dissertatsiya", "Kitob", "Prezentatsiya", "Video rolik"]
    },
    'ru': {
        'welcome': "Здравствуйте! По какому предметu вы ищете материалы?",
        'cat_select': "Выберите тип материала:",
        'topic_ask': "Какая тема вам нужна?",
        'searching': "🔍 Findly ищет...",
        'not_found': "Извините, ничего не найдено 😞",
        'buttons': ["Статья/Диссертация", "Книга", "Презентация", "Видео ролик"]
    },
    'eng': {
        'welcome': "Welcome! Which subject are you looking for?",
        'cat_select': "Select the material type:",
        'topic_ask': "Which topic do you need?",
        'searching': "🔍 Findly is searching...",
        'not_found': "Sorry, no results found 😞",
        'buttons': ["Article/Dissertation", "Book", "Presentation", "Video clip"]
    }
}

# --- Google Search funksiyasi ---
def google_search(query):
    url = f"https://www.googleapis.com/customsearch/v1?key={G_API_KEY}&cx={G_CX}&q={query}"
    try:
        response = requests.get(url).json()
        results = []
        if 'items' in response:
            for item in response['items'][:5]:
                results.append(f"✅ {item['title']}\n🔗 {item['link']}")
        return results
    except Exception as e:
        logging.error(f"Google API Error: {e}")
        return None

# --- Handlers ---
@dp.message_handler(commands=['start'], state='*')
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Tilni tanlang / Choose language:\n/uz - O'zbekcha\n/ru - Русский\n/eng - English")
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
    markup.add(*MESSAGES[lang]['buttons'])
    await message.answer(MESSAGES[lang]['cat_select'], reply_markup=markup)
    await SearchSteps.category.set()

@dp.message_handler(state=SearchSteps.category)
async def get_category(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    data = await state.get_data()
    await message.answer(MESSAGES[data['lang']]['topic_ask'], reply_markup=types.ReplyKeyboardRemove())
    await SearchSteps.topic.set()

@dp.message_handler(state=SearchSteps.topic)
async def final_search(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data['lang']
    await message.answer(MESSAGES[lang]['searching'])
    
    subject = data['subject']
    topic = message.text
    category = data['category']
    
    # Aqlli qidiruv so'rovi (Smart Query)
    query = f"{subject} {topic}"
    
    if any(x in category for x in ["Maqola", "Dissertatsiya", "Article", "Статья"]):
        query += " filetype:pdf"
    elif any(x in category for x in ["Kitob", "Book", "Книга"]):
        query += " darslik filetype:pdf"
    elif any(x in category for x in ["Prezentatsiya", "Presentation", "Презентация"]):
        query += " filetype:pptx"
    elif "Video" in category:
        query = f"site:youtube.com {subject} {topic}"

    res = google_search(query)
    
    # Agar natija chiqmasa, oddiyroq qidirib ko'rish (Fallback)
    if not res:
        res = google_search(f"{subject} {topic}")

    if res:
        await message.answer("\n\n".join(res))
    else:
        await message.answer(MESSAGES[lang]['not_found'])
    await state.finish()

if __name__ == '__main__':
    # Render'da bot o'chib qolmasligi uchun Flask ishga tushadi
    keep_alive()
    # Konfliktlarni oldini olish uchun skip_updates=True
    executor.start_polling(dp, skip_updates=True)