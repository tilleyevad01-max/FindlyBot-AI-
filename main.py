import os
import logging
import wikipedia
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, executor
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# --- Render uchun Web Server ---
app = Flask('')
@app.route('/')
def home(): return "Wiki Bot is Running!"

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

class WikiState(StatesGroup):
    lang = State()
    query = State()

# --- Xabarlar matni ---
LANG_DATA = {
    'uz': {
        'ask_info': "Assalomu aleykum, sizga nima haqida ma'lumot kerak?",
        'next_query': "Yana nima haqida bilmoqchisiz?",
        'not_found': "Uzur, Wikipedia'da bunday ma'lumot topilmadi 😞",
        'searching': "🔍 Wikipedia'dan qidiryapman...",
        'wiki_lang': 'uz'
    },
    'ru': {
        'ask_info': "Здравствуйте! О чем вам нужна информация?",
        'next_query': "О чем еще вы хотите узнать?",
        'not_found': "Извините, такая информация в Википедии не найдена 😞",
        'searching': "🔍 Ищу в Википедии...",
        'wiki_lang': 'ru'
    },
    'en': {
        'ask_info': "Hello! What information do you need?",
        'next_query': "What else would you like to know about?",
        'not_found': "Sorry, no such information found on Wikipedia 😞",
        'searching': "🔍 Searching Wikipedia...",
        'wiki_lang': 'en'
    }
}

# --- Handlers ---
@dp.message_handler(commands=['start'], state='*')
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("O'zbekcha 🇺🇿", "Русский 🇷🇺", "English 🇺🇸")
    
    welcome_text = (
        "Iltimos, kerakli tilni tanlang\n"
        "Пожалуйста, выберите нужный язык\n"
        "Please select the required language"
    )
    await message.answer(welcome_text, reply_markup=markup)
    await WikiState.lang.set()

@dp.message_handler(state=WikiState.lang)
async def set_language(message: types.Message, state: FSMContext):
    if "O'zbekcha" in message.text:
        user_lang = 'uz'
    elif "Русский" in message.text:
        user_lang = 'ru'
    else:
        user_lang = 'en'
        
    await state.update_data(chosen_lang=user_lang)
    await message.answer(
        LANG_DATA[user_lang]['ask_info'], 
        reply_markup=types.ReplyKeyboardRemove()
    )
    await WikiState.query.set()

@dp.message_handler(state=WikiState.query)
async def get_wiki_info(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang_code = data.get('chosen_lang')
    
    # Foydalanuvchi /start yozsa, til tanlashga qaytadi
    if message.text == "/start":
        await cmd_start(message, state)
        return

    await message.answer(LANG_DATA[lang_code]['searching'])
    wikipedia.set_lang(LANG_DATA[lang_code]['wiki_lang'])
    
    try:
        # Wikipedia'dan qisqa ma'lumot olish
        summary = wikipedia.summary(message.text, sentences=5)
        page = wikipedia.page(message.text)
        
        response = f"📖 **{page.title}**\n\n{summary}\n\n🔗 [To'liq maqola]({page.url})"
        await message.answer(response, parse_mode="Markdown", disable_web_page_preview=False)
        
        # Ma'lumot topilgandan keyin yana so'rash
        await message.answer(f"✅ {LANG_DATA[lang_code]['next_query']}")
        
    except (wikipedia.exceptions.PageError, wikipedia.exceptions.DisambiguationError):
        # Ma'lumot topilmasa yoki juda ko'p variant bo'lsa
        await message.answer(LANG_DATA[lang_code]['not_found'])
        await message.answer(LANG_DATA[lang_code]['next_query'])
        
    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await message.answer(LANG_DATA[lang_code]['not_found'])

# Botni ishga tushirish
if __name__ == '__main__':
    keep_alive()
    executor.start_polling(dp, skip_updates=True)