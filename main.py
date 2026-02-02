import os
import logging
import requests
import urllib.parse
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
    return "Findly AI is live and diagnosing!"

def run_web():
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

MESSAGES = {
    'uz': {
        'welcome': "Assalomu aleykum! Qaysi fan uchun materiallar izlamoqdasiz?",
        'cat_select': "Material turini tanlang:",
        'topic_ask': "Mavzu nomini yozing:",
        'searching': "🔍 Findly qidirmoqda va diagnostika qilmoqda...",
        'not_found': "Uzur, ma'lumot topilmadi 😞",
        'buttons': ["Maqola/Dissertatsiya", "Kitob", "Prezentatsiya", "Video rolik"]
    },
    'ru': {
        'welcome': "Здравствуйте! По какому предмету нужны материалы?",
        'cat_select': "Выберите тип:",
        'topic_ask': "Введите тему:",
        'searching': "🔍 Findly ищет и диагностирует...",
        'not_found': "Ничего не найдено 😞",
        'buttons': ["Статья/Диссертация", "Книга", "Презентация", "Видео ролик"]
    },
    'eng': {
        'welcome': "Welcome! Which subject are you looking for?",
        'cat_select': "Select type:",
        'topic_ask': "Enter topic:",
        'searching': "🔍 Findly is searching and diagnosing...",
        'not_found': "No results found 😞",
        'buttons': ["Article/Dissertation", "Book", "Presentation", "Video clip"]
    }
}

# --- Google Search Diagnostika bilan ---
def google_search(query):
    safe_query = urllib.parse.quote_plus(query)
    url = f"https://www.googleapis.com/customsearch/v1?key={G_API_KEY}&cx={G_CX}&q={safe_query}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        logging.info(f"DEBUG: Qidiruv so'rovi: {query}")

        # PRO VISION DIAGNOSTIKA
        if 'error' in data:
            return [f"❌ Google API xatosi: {data['error']['message']}"]
        
        if 'searchInformation' in data:
            total = data['searchInformation'].get('totalResults', '0')
            if total == '0':
                return [f"⚠️ Google topdi, lekin natija 0 ta.\n\nEhtimoliy sabab: CX sozlamasida 'Search the entire web' ochiq emas yoki siz kiritgan saytlar ichida bu mavzu yo'q."]

        results = []
        if 'items' in data:
            for item in data['items'][:5]:
                results.append(f"✅ {item['title']}\n🔗 {item['link']}")
        return results
    except Exception as e:
        logging.error(f"Tizim xatosi: {e}")
        return [f"❌ Tizim xatosi: {str(e)}"]

# --- Handlers ---
@dp.message_handler(commands=['start'], state='*')
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Tilni tanlang:\n/uz - O'zbekcha\n/ru - Русский\n/eng - English")
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
    
    query = f"{data['subject']} {message.text}"
    res = google_search(query)
    
    if res:
        await message.answer("\n\n".join(res))
    else:
        await message.answer(MESSAGES[lang]['not_found'])
    await state.finish()

if __name__ == '__main__':
    keep_alive()
    # skip_updates=True eski xabarlarni tozalaydi
    executor.start_polling(dp, skip_updates=True)