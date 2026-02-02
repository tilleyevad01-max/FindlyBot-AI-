import os
import logging
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, executor
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from duckduckgo_search import DDGS  # Google API o'rniga bepul muqobil

# --- Render uchun Web Server ---
app = Flask('')
@app.route('/')
def home(): return "Findly AI is Live!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# --- Bot Sozlamalari ---
API_TOKEN = os.getenv('BOT_TOKEN') # Faqat Telegram Token kerak xolos
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class SearchSteps(StatesGroup):
    language = State()
    subject = State()
    category = State()
    topic = State()

MESSAGES = {
    'uz': {
        'welcome': "Fan nomini yozing:",
        'cat_select': "Material turini tanlang:",
        'topic_ask': "Mavzu nomini yozing:",
        'searching': "🔍 Qidirilmoqda (Bepul qidiruv tizimi)...",
        'not_found': "Ma'lumot topilmadi 😞",
        'buttons': ["Maqola", "Kitob", "Prezentatsiya", "Video"]
    }
}

# --- Qidiruv funksiyasi (API KEY-SIZ) ---
def free_search(query):
    try:
        results = []
        with DDGS() as ddgs:
            # Mavzu bo'yicha 5 ta eng yaxshi natijani olamiz
            ddgs_gen = ddgs.text(query, region='wt-wt', safesearch='off', timelimit='y')
            for i, r in enumerate(ddgs_gen):
                if i >= 5: break
                results.append(f"✅ {r['title']}\n🔗 {r['href']}")
        return results
    except Exception as e:
        logging.error(f"Search Error: {e}")
        return None

# --- Handlers ---
@dp.message_handler(commands=['start'], state='*')
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Tilni tanlang: /uz")
    await SearchSteps.language.set()

@dp.message_handler(commands=['uz'], state=SearchSteps.language)
async def set_lang(message: types.Message, state: FSMContext):
    await state.update_data(lang='uz')
    await message.answer(MESSAGES['uz']['welcome'])
    await SearchSteps.subject.set()

@dp.message_handler(state=SearchSteps.subject)
async def get_subject(message: types.Message, state: FSMContext):
    await state.update_data(subject=message.text)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(*MESSAGES['uz']['buttons'])
    await message.answer(MESSAGES['uz']['cat_select'], reply_markup=markup)
    await SearchSteps.category.set()

@dp.message_handler(state=SearchSteps.category)
async def get_category(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    await message.answer(MESSAGES['uz']['topic_ask'], reply_markup=types.ReplyKeyboardRemove())
    await SearchSteps.topic.set()

@dp.message_handler(state=SearchSteps.topic)
async def final_search(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await message.answer(MESSAGES['uz']['searching'])
    
    # Qidiruv so'rovini shakllantirish
    query = f"{data['subject']} {message.text} {data['category']}"
    if "Kitob" in data['category']: query += " filetype:pdf"
    
    res = free_search(query)
    
    if res:
        await message.answer("\n\n".join(res))
    else:
        await message.answer(MESSAGES['uz']['not_found'])
    await state.finish()

if __name__ == '__main__':
    keep_alive()
    executor.start_polling(dp, skip_updates=True)