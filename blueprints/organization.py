from flask import Blueprint, Response, request, url_for, redirect, render_template, session, flash

from app import Message, mail, recaptcha, app
from views import log_view, wraps, logger
from validators import Validator
from models import Organization

from threading import Thread


validator = Validator()

organization = Blueprint('organization', __name__,
                         static_folder='../static', template_folder='../templates')


def login_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        key = session.get('org', {}).get('key')
        logger.debug('In login_required for org key: %s', key)

        if Organization.query.filter_by(key=key).first():
            logger.debug('Org is logged in')
            return f(*args, **kwargs)

        session.pop('vol', None)
        session.pop('org', None)
        logger.debug('Org is not authenicated')
        return redirect(url_for('organization.register'))

    return inner


@organization.route('/login', methods=['GET', 'POST'])
@log_view
def login():
    if request.method == 'POST':
        # if recaptcha.verify():
        username = request.form.get('username')
        password = request.form.get('password')

        org, session_data, msg = Organization.validate_creds(
            username, password)
        if org:
            session['org'] = session_data
            return redirect(url_for('volunteer.index'))

        flash(msg)

        # else:
        #     flash('Подтвердите капчу!')

    return render_template('home/register.html', org=True, login=True)


@organization.route('/register', methods=['GET', 'POST'])
@log_view
def register():
    if request.method == 'POST':
        # if recaptcha.verify():
        form = request.form
        logger.debug('Org registration form: %s', form)

        username = form.get('username')
        owner_email = form.get('owner_email')
        owner_phone = form.get('owner_phone')
        contact_email = form.get('contact_email')
        contact_phone = form.get('contact_phone')

        if contact_phone and Organization.query.filter_by(contact_phone=contact_phone).first():
            flash(
                f'Волонтерская организация с данным контактным номером телефона {contact_phone} уже зарегистрирована')
        elif contact_email and Organization.query.filter_by(contact_email=contact_email).first():
            flash(
                f'Волонтерская организация с данным контактным электронным адресом {contact_email} уже зарегистрирована')
        elif Organization.query.filter_by(username=username).first():
            flash(
                f'Волонтерская организация с данным логином {username} уже зарегистрирована')
        elif Organization.query.filter_by(owner_email=owner_email).first():
            flash(
                f'Волонтерская организация с данным электронным адресом руковдителя {owner_email} уже зарегистрирована')
        elif Organization.query.filter_by(owner_phone=owner_phone).first():
            flash(
                f'Волонтерская организация с данным номером телефона руководителя {owner_phone} уже зарегистрирована')
        elif not all((validator.v_email(contact_email), validator.v_phone(contact_phone), validator.v_email(owner_email), validator.v_phone(owner_phone))):
            flash(f'Телефон, электронная почта или псевдоним указаны в неверном формате')
        else:
            org, session_data = Organization.create(
                form.get('password'),
                form.get('key'),
                username=username,
                addr=form.get('addr'),
                about=form.get('about'),
                owner_phone=owner_phone,
                owner_email=owner_email,
                contact_email=contact_email,
                contact_phone=contact_phone,
                org_name=form.get('org_name'),
                owner_name=form.get('owner_name'),
            )
            if org:
                session['org'] = session_data
                logger.debug(
                    'Session data after registration: %s', session_data)

                flash('Успешная регистрация!')
                return redirect(url_for('volunteer.index'))

            flash('Введенный ключ не действителен или уже использован. Попросите создателя сгенерировать для Вас новый ключ')

        # if validation above failed
        return redirect(url_for('organization.register'))

        # else:
        #     flash('Ага, робот! Подвердите каптчу еще раз')
        #     return redirect(url_for('organization.register'))

    else:
        key = session.get('org', {}).get('key')
        if Organization.query.filter_by(key=key).first():
            return redirect(url_for('volunteer.index'))

        return render_template('home/register.html', org=True)


@organization.route('/generate', methods=['POST', 'GET'])
@login_required
@log_view
def generate_keys():

    def send_email(to_email: list):

        def send_async_email(app, msg):
            with app.app_context():
                mail.send(msg)

        recipients = to_email
        sender = 'volus.kokshe@gmail.com'
        subject = 'Volus Ключи Регистрации'
        body = f'Ключи в размере {keys_amount} штук. Передайте данные ключи исключительно волонтерам:\n\n{keys}'

        msg = Message(subject=subject, recipients=recipients,
                      body=body, sender=sender)

        Thread(target=send_async_email, args=(app, msg)).start()

    if request.method == 'POST':
        # if recaptcha.verify():
        keys_amount = request.form.get('keys_amount')

        org_key = session.get('org').get('key')
        to_email = session.get('org').get('owner_email')

        if to_email and keys_amount and org_key and keys_amount.isdigit():
            keys = Organization.generate_vol_registration_keys(
                org_key, int(keys_amount))

            if keys:
                send_email([to_email, ])

                flash('Ключи были отправлены на почту')
                logger.debug('Email with vol registraion keys was sent')
            else:
                flash(
                    'Произошла ошибка, данная волонтерская организация не зарегистрирована')

        else:
            flash('Произошла ошибка при генерации, повторите запрос позже')
        # else:
        #     print('Captcha failed')
        #     flash('Пройдите капчу еще раз')

    return render_template('volunteer/v_generate_keys.html')
