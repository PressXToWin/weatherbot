# WeatherBot

Telegram бот для получения данных о погоде. Используется API Яндекс.Погоды.

### Функционал:
- возможность сохранения своего города
- возможность получения данных о погоде в различных городах
- возможность просмотра истории запросов
- реализована админ панель для получения инфорации о юзерах

### Стек: 
- Aiogram
- SQLAlchemy (гарантированно поддерживаются SQLite и PostgreSQL)
- Docker

## Как запустить проект локально:
Клонировать репозиторий и перейти в него в командной строке:
```
git clone git@github.com:PressXToWin/weatherbot.git
```

```
cd weatherbot/
```

Cоздать и активировать виртуальное окружение:

```
python3 -m venv venv
```

```
source venv/bin/activate
```
```
python3 -m pip install --upgrade pip
```

Установить зависимости из файла requirements.txt:

```
pip install -r requirements.txt
```

Создаем .env файл с токенами согласно образцу .env.example:

```
GEO_KEY=<API-ключ Яндекс.Геокодера>
WEATHER_KEY=<API-ключ Яндекс.Погоды>

DATABASE_URL=<URL к базе в формате SQLAlchemy>

BOT_TOKEN=<Токен Telegram-бота>
TG_BOT_ADMIN=<ID админов, разделённые пробелом>
```

Запускаем бота:

```
python bot.py
```

## Как запустить проект через Docker:

```
docker build -t weatherbot . 
```

```shell
docker run -d \
  --name weatherbot \
  -v /path/to/db/bot.db:/app/bot.db \
  -e GEO_KEY=<API-ключ Яндекс.Геокодера> \
  -e WEATHER_KEY=<API-ключ Яндекс.Погоды> \
  -e DATABASE_URL=<URL к базе в формате SQLAlchemy> \
  -e BOT_TOKEN=<Токен Telegram-бота> \
  -e TG_BOT_ADMIN=<ID админов, разделённые пробелом> \
  weatherbot
```