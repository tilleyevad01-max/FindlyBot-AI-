import os
import logging
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, executor
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from duckduckgo_search import DDGS

# --- Web Server ---
app = Flask('')
@app.route('/')
def home(): return "Findly AI is Active!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# --- Bot Sozlamalari ---
API_TOKEN = os.getenv('BOT_TOKEN')
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
        'welcome': "Qaysi fan bo'yicha material izlaymiz?",
        'cat_select': "Turini tanlang:",
        'topic_ask': "Mavzu nomini kiriting:",
        'searching': "🔍 Qidirilmoqda...",
        'not_found': "Ma'lumot topilmadi. Boshqacharoq yozib ko'ring.",
        'buttons': ["Maqola", "Kitob", "Prezentatsiya", "Video"]
    },
    'ru': {
        'welcome': "По какому предмету ищем материал?",
        'cat_select': "Выберите тип:",
        'topic_ask': "Введите название темы:",
        'searching': "🔍 Поиск...",
        'not_found': "Информация не найдена. Попробуйте другой запрос.",
        'buttons': ["Статья", "Книга", "Презентация", "Видео"]
    },
    'eng': {
        'welcome': "What subject are we searching for?",
        'cat_select': "Select type:",
        'topic_ask': "Enter the topic name:",
        'searching': "🔍 Searching...",
        'not_found': "Information not found. Try a different query.",
        'buttons': ["Article", "Book", "Presentation", "Video"]
    }
}

def free_search(query):
    try:
        results = []
        with DDGS() as ddgs:
            # Qidiruvni kengaytiramiz
            ddgs_gen = ddgs.text(query, region='wt-wt', safesearch='off')
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
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("O'zbekcha 🇺🇿", "Русский 🇷🇺", "English 🇺🇸")
    await message.answer("Tilni tanlang / Выберите язык / Select language:", reply_markup=markup)
    await SearchSteps.language.set()

@dp.message_handler(state=SearchSteps.language)
async def set_lang(message: types.Message, state: FSMContext):
    text = message.text
    lang = 'uz' if "O'zbekcha" in text else 'ru' if "Русский" in text else 'eng'
    await state.update_data(lang=lang)
    await message.answer(MESSAGES[lang]['welcome'], reply_markup=types.ReplyKeyboardRemove())
    await SearchSteps.subject.set()

@dp.message_handler(state=SearchSteps.subject)
async def get_subject(message: types.Message, state: FSMContext):
    await state.update_data(subject=message.text)
    data = await state.get_data()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(*MESSAGES[data['lang']]['buttons'])
    await message.answer(MESSAGES[data['lang']]['cat_select'], reply_markup=markup)
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
    
    # Qidiruvni aqlliroq qilish: Fan + Mavzu + Tur
    query = f"{data['subject']} {message.text} {data['category']}"
    
    # Ma'lumot topish ehtimolini oshirish uchun qo'shimcha filtrlar
    if "Kitob" in data['category'] or "Книга" in data['category'] or "Book" in data['category']:
        query += " filetype:pdf OR filetype:epub"
    if "Prezentatsiya" in data['category'] or "Презентация" in data['category'] or "Presentation" in data['category']:
        query += " filetype:ppt OR filetype:pptx"

    res = free_search(query)
    
    if res:
        await message.answer("\n\n".join(res))
    else:
        # Agar topilmasa, soddaroq qidirib ko'ramiz
        res_simple = free_search(f"{data['subject']} {message.text}")
        if res_simple:
            await message.answer("\n\n".join(res_simple))
        else:
            await message.answer(MESSAGES[lang]['not_found'])
    await state.finish()

if __name__ == '__main__':
    keep_alive()
    executor.start_polling(dp, skip_updates=True)