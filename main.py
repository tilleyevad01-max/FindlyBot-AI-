import os
import logging
from threading import Thread
from flask import Flask  # Flask qo'shamiz
from aiogram import Bot, Dispatcher, types, executor
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from googlesearch import search

# --- Render uchun Web Server (Keep Alive) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    t = Thread(target=run_web)
    t.start()
# --------------------------------------------

API_TOKEN = os.getenv('BOT_TOKEN')
logging.basicConfig(level=logging.INFO)

if not API_TOKEN:
    exit("XATO: BOT_TOKEN topilmadi!")

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# [Qolgan bot mantiqi yuqoridagi kod bilan bir xil...]
# (Sizga bergan oldingi kodimni shu yerga qo'yasiz)

if __name__ == '__main__':
    keep_alive()  # Web serverni ishga tushirish
    executor.start_polling(dp, skip_updates=True)