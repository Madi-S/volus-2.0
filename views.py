from flask import render_template, request, url_for, redirect, session, flash, send_from_directory
from flask_admin.contrib.sqla import ModelView
from flask_wtf.csrf import CSRFError
from flask_mail import Message

from app import app, ip_ban, recaptcha, mail, db
from models import AdminUser, Organization, Needy

from functools import wraps
from logger import logger
from time import time

import os


bad_user_agents = ('requests', 'scrap', 'crawl', 'spider')


# --- VALIDATION AND SECURITY VIEWS ---

def log_view(f):
    @wraps(f)
    def inner(*args, **kwargs):
        logger.debug('In %s', f.__name__)

        try:
            return f(*args, **kwargs)
        except:
            logger.exception('Error in %s', f.__name__)
            flash('Ошибка сервера повторите запрос позже')
            return redirect(url_for('home'))

    return inner


@app.teardown_request
def teardown_request(error=None):
    if error:
        # Log the error
        logger.critical(
            'Error occured %s. Sending email with traceback info', error)
        try:
            subject = 'VOLUS CRITICAL'
            sender = 'volus.kokshe@gmail.com'
            recipients = ['khovansky99@gmail.com', ]
            body = f'[VOLUS APP] Error occured:\n\n{error}'

            msg = Message(subject=subject, recipients=recipients,
                          body=body, sender=sender)
            mail.send(msg)
        except:
            return redirect(url_for('home'))


'''
@app.after_request
def after_request_func(response):

    # TODO: Add some cleanup, db connection closing and other stuff

    username = g.username
    foo = session.get("foo")
    print("after_request is running!", username, foo)
    return response


def check_form_time(f):
    @wraps(f)
    def inner(*args, **kwargs):
        finish = time()
        start = session.get('start', 0)
        
        if finish - start <= 7:
            return Response(
                'Слишком быстро! Если вы человек, просто обновите страницу',
                status=400,
            )
        
        return f(*args, **kwargs)

    return inner
'''


@app.before_request
def check_user_agent():
    user_agent = request.headers.get('User-Agent', '')
    logger.debug('User-Agent: %s', user_agent)

    if user_agent in bad_user_agents:
        logger.warning('Banning user for suspicious user-agent')
        ip_ban.add()
        return '<h1>Привет, ботяра!</h1><h2>Если Вы видете данное сообщение, включите поддержку JavaScript и удалите куки</h2>'


# --- ADMIN VIEWS

class AdminModelView(ModelView):
    def is_accessible(self):
        logger.warning('Someone is trying to reach Admin Page')
        return 'admin_madi' in session

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('home'))


@app.route('/admin-logout')
@log_view
def admin_logout():
    session.pop('admin_madi')
    logger.debug('Successful logout from Admin Page')
    return redirect(url_for('home'))


@app.route('/admin-login', methods=['POST', 'GET'])
@log_view
def admin_login():
    # some form here then redirect to admin page
    logger.warning('Someone has access to admin-login page')
    if request.method == 'POST':
        if recaptcha.verify():
            username = request.form.get('username')
            password = request.form.get('password')

            validated = AdminUser.validate_creds(username, password)

            if validated:
                session['admin_madi'] = True
                logger.warning(
                    'Admin Page accessed, if it was not you, enhance security for Admin Page')
                return redirect('/admin-volus-for-madi')

    return render_template('home/admin_login.html')


# --- BASIC VIEWS ---

@app.route('/session')
@log_view
def session_items():
    return {'session': session.items().__repr__()}


@app.route('/favicon.ico')
@log_view
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'images/favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/donate', methods=['GET', 'POST'])
@log_view
def donate():
    # TODO: do not load all organizations, find out way to paginate them
    # orgs = Organization.query.all()
    # return render_template('home/donations.html', orgs=orgs)
    flash('Данная страница в процессе разработке')
    return redirect(url_for('home'))


@app.route('/terms')
@log_view
def terms():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'docs/Мади ДЗ.pdf')


@app.route('/home')
@app.route('/main')
@app.route('/')
@log_view
def home():
    iin = session.get('iin')
    if iin and Needy.query.filter_by(iin=iin).first():
        return redirect(url_for('help.home'))
    
    return render_template('home/index.html')


# --- ERROR HANDLING VIEWS ---

@app.errorhandler(403)
@log_view
def forbidden(e):
    return render_template('errors/forbidden.html', error=e), 403


@app.errorhandler(404)
@log_view
def page_not_found(e):
    return render_template('errors/not_found.html', error=e), 404


@app.errorhandler(500)
@log_view
def internal_server_error(e):
    db.session.rollback()
    return render_template('errors/server_error.html', error=e), 500


@app.errorhandler(CSRFError)
@log_view
def handle_csrf_error(e):
    db.session.rollback()
    return render_template('errors/csrf_error.html', reason=e.description), 400
