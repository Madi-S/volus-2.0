# from logging_config import logger
from views import *
from logger import logger
from app import app, db, admin
from blueprints.help import help
from blueprints.volunteer import volunteer
from blueprints.organization import organization
import models


def start_ngrok():
    logger.debug('Starting with ngrok')
    from pyngrok import ngrok

    url = ngrok.connect(5000)
    logger.debug('Tunnel ngrok URL %s', url)


if __name__ == '__main__':
    logger.debug('Starting Volus')
    app.register_blueprint(help, url_prefix='/help')
    app.register_blueprint(volunteer, url_prefix='/volunteer')
    app.register_blueprint(organization, url_prefix='/organization')

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

    if app.config['START_NGROK']:
        start_ngrok()

    logger.debug('Web app is running')
    app.run()

    # logger.debug('Volus Web Application was started')

    # ngrok http 5000
