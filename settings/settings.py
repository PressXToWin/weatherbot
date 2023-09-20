import os

from dotenv import load_dotenv

load_dotenv()

GEO_KEY = os.getenv('GEO_KEY')
WEATHER_KEY = {'X-Yandex-API-Key': os.getenv('WEATHER_KEY', 'sqlite:////app/bot.db')}

DATABASE_URL = os.getenv('DATABASE_URL')

BOT_TOKEN = os.getenv('BOT_TOKEN')
TG_BOT_ADMIN = os.getenv('TG_BOT_ADMIN').split()
