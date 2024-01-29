import os
from sys import platform
from datetime import timedelta


DB_ABS_PATH = os.path.join(os.path.abspath(os.getcwd()), 'sqlite', 'volus.db')


class Config(object):
    DEBUG = True

    # FLASK_ENV = 'development'

    # --- DATABASE ---
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DB_ABS_PATH}' if platform.startswith('w')\
                            else 'mysql+mysqlconnector://root:1234@localhost/volus'

    # --- SESSION ---
    SESSION_TYPE = 'redis'
    SECRET_KEY = 'Your app secret key'
    PERMANENT_SESSION_LIFETIME = timedelta(days=3650)

    # --- RECAPTCHA ---
    RECAPTCHA_SITE_KEY = 'Recaptcha site key'
    RECAPTCHA_SECRET_KEY = 'Reacaptcha secret key'
    # RECAPTCHA_THEME = 'dark'
    # RECAPTCHA_TYPE = 'audio'
    # RECAPTCHA_SIZE = 'compact'

    # --- EMAIL SENDING ---
    MAIL_PORT = 465
    MAIL_DEBUG = False
    MAIL_USE_SSL = True
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_USERNAME = 'volus.kokshe@gmail.com'
    MAIL_PASSWORD = 'volus=zaebis123Q#*@#'

    # --- ADMIN ---
    FLASK_ADMIN_SWATCH = 'superhero'

    # --- CACHE ---
    CACHE_TYPE = 'SimpleCache'  # On production use RedisCache or MemcachedCache
    CACHE_DEFAULT_TIMEOUT = 100

    # --- NGROK ---
    START_NGROK = False

    # --- TESTING ---
    APP_BASE_URL = 'http://127.0.0.1:5000/'
