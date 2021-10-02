from flask import Flask, session

from flask_admin import Admin
from flask_ipban import IpBan
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_mail import Mail, Message
from flask_recaptcha import ReCaptcha
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy

from config import Config
from logger import logger


app = Flask('Volus')
app.config.from_object(Config)

db = SQLAlchemy(app)
mail = Mail(app)
bcrypt = Bcrypt(app)
csrf = CSRFProtect(app)
migrate = Migrate(app, db)
recaptcha = ReCaptcha(app=app)
ip_ban = IpBan(app, ban_seconds=60, ban_count=30)
# ip_ban.ip_whitelist_add('127.0.0.1')
admin = Admin(app, name='Volus Админка',
              template_mode='bootstrap3', url='/admin-volus-for-madi')
