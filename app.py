from flask import Flask
from flask_mail import Mail
from flask_admin import Admin
from flask_ipban import IpBan
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_recaptcha import ReCaptcha
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy

from config import Config


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


def create_app():
    from views import AdminModelView
    import models

    admin.add_view(AdminModelView(models.Needy, db.session,
                                  'Нуждающиеся', endpoint='/admin-needies'))
    admin.add_view(AdminModelView(models.Bookmark, db.session,
                                  'Закладки', endpoint='/admin-bookmarks'))
    admin.add_view(AdminModelView(models.HelpQuery, db.session,
                                  'Запросы', endpoint='/admin-help-queries'))
    admin.add_view(AdminModelView(models.Volunteer, db.session,
                                  'Волонтеры', endpoint='/admin-volunteers'))
    admin.add_view(AdminModelView(models.Organization, db.session,
                                  'Организации', endpoint='/admin-organizations'))
    admin.add_view(AdminModelView(models.Notification, db.session,
                                  'Уведомления', endpoint='/admin-notifications'))
    admin.add_view(AdminModelView(models.VolunteerRegistrationKey, db.session,
                                  'Ключи Регистрации Волонтеров', endpoint='/admin-volunteer-registration-keys'))
    admin.add_view(AdminModelView(models.OrganizationRegistrationKey, db.session,
                                  'Ключи Регистрации Организаций', endpoint='/admin-organization-registration-keys'))

    from blueprints.help import help as help_blueprint
    from blueprints.volunteer import volunteer as volunteer_blueprint
    from blueprints.organization import organization as organization_blueprint

    app.register_blueprint(help_blueprint, url_prefix='/help')
    app.register_blueprint(volunteer_blueprint, url_prefix='/volunteer')
    app.register_blueprint(organization_blueprint, url_prefix='/organization')
