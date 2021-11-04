from flask import Blueprint, request, url_for, redirect, render_template, session, flash
from datetime import timedelta

from views import wraps, log_view, logger
from models import Needy, HelpQuery
from validators import Validator


validator = Validator()

help = Blueprint('help', __name__, static_folder='../static',
                 template_folder='../templates/help')


def login_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        logger.debug('In login_required for needy iin: %s ',
                     session.get('iin'))

        if 'iin' in session and Needy.query.filter_by(iin=session.get('iin', '')).first():
            logger.debug('Needy is logged in')
            return f(*args, **kwargs)

        logger.debug('Needy is not authenicated')
        return redirect(url_for('help.edit_profile'))

    return inner


@help.route('/logout')
@login_required
@log_view
def logout():
    session.pop('iin', None)

    return redirect(url_for('home'))


@help.route('/login')
@log_view
def login():
    iin = request.args.get('iin')
    if not iin:
        return redirect(url_for('help.edit_profile'))

    n = Needy.query.filter_by(iin=iin).first()
    if not n:
        return redirect(url_for('help.edit_profile'))

    session['name'] = n.name
    session['addr'] = n.addr
    session['about'] = n.about
    session['needy_id'] = n.id
    session['gender'] = n.gender
    session['home_number'] = n.home_number
    session['rel_number'] = n.relative_number
    session['mobile_number'] = n.mobile_number
    session['help_type'] = n.help_type.strip().split(', ')

    # Must be last
    session['iin'] = iin

    return redirect(url_for('help.profile'))


@help.route('/profile')
@login_required
@log_view
def profile():
    return render_template('profile.html')


@help.route('/profile/edit', methods=['POST', 'GET'])
@log_view
def edit_profile():
    form = request.form
    args = request.args

    logger.debug('Method: %s', request.method)
    logger.debug('Form: %s', form)
    logger.debug('Args: %s', args)
    logger.debug('Session: %s', session.items())

    if request.method == 'POST':
        iin = form.get('iin')
        name = form.get('name')
        addr = form.get('addr')
        gender = form.get('avatar')
        rel_number = form.get('rel_number')
        about = form.get('about', '').strip()
        home_number = form.get('home_number')
        mobile_number = form.get('mobile_number')
        help_type = form.getlist('help_type')

        if not validator.v_iin(iin):
            flash('ИИН указан в неверном формате')
        elif not validator.v_phone(home_number) and home_number:
            flash('Домашний номер указан в неверном формате')
        elif not validator.v_phone(mobile_number) and mobile_number:
            flash('Мобильный номер указан в неверном формате')
        elif not validator.v_phone(rel_number) and rel_number:
            flash('Телефонный номер родственников указан в неверном формате')
        else:
            needy = Needy.query.filter_by(iin=iin).first()

            # Update data for existing needy
            if needy:
                Needy.update_data_for(needy.id, form, to_overwrite={
                                      'help_type': ', '.join(help_type)})

            # Register new needy
            else:
                needy = Needy.create(
                    iin=iin,
                    addr=addr,
                    name=name,
                    about=about,
                    gender=gender,
                    home_number=home_number,
                    relative_number=rel_number,
                    mobile_number=mobile_number,
                    help_type=', '.join(help_type),
                )

            session['name'] = name
            session['addr'] = addr
            session['about'] = about
            session['gender'] = gender
            session['needy_id'] = needy.id
            session['help_type'] = help_type
            session['rel_number'] = rel_number
            session['home_number'] = home_number
            session['mobile_number'] = mobile_number
            session['heading'] = 'Здесь можно изменить.Личные данные'

            # Must be last
            session['iin'] = iin

            return redirect(url_for('help.profile'))

        # if validation above failed
        return render_template('edit_profile.html')

    # Render request from home index page (first form)
    elif 'name' in args and 'about' in args and 'home_number' in args:
        session['name'] = args.get('name')
        session['about'] = args.get('about', '').strip()
        session['home_number'] = args.get('home_number')

    return render_template('edit_profile.html')


@help.route('/get', methods=['POST', 'GET'])
@login_required
@log_view
def get_help():
    if request.method == 'POST':
        from_needy = session.get('needy_id')

        queries_count = HelpQuery.query.filter_by(from_needy=from_needy).filter_by(
            deleted=False).filter_by(completion_status=False).count()

        if queries_count < 10:
            form = request.form
            logger.debug('Form in get_help: %s', form)

            about = form.get('problem')
            hours = form.get('duration')
            help_type = form.getlist('help_type')

            if hours == 'None':
                help_query = HelpQuery.create(
                    about=about,
                    from_needy=from_needy,
                    help_type=', '.join(help_type),
                )
            else:
                help_query = HelpQuery.create(
                    about=about,
                    from_needy=from_needy,
                    help_type=', '.join(help_type),
                    duration=timedelta(hours=int(hours)),
                )

            flash(
                f'Заявка #{help_query.id} на получение помощи успешно отправлена')
            return redirect(url_for('help.history'))

        else:
            flash(f'Невозможно отправить заявку на помощь, так как ревышен лимит активных заявок (10). Удалите их, чтобы отправить новую заявку на помощь')

    return render_template('get_help.html')


@help.route('/query/delete/<help_query_id>')
@login_required
@log_view
def delete_help(help_query_id):
    deleted = HelpQuery.delete(help_query_id)
    if deleted:
        flash(f'Успешна удалена заявка на помощь #{help_query_id}')
    else:
        flash(
            f'Не получается удалить заявку на помощь #{help_query_id}. Возможно она уже удалена или не существует')

    return redirect(url_for('help.history'))


@help.route('/query/change/<help_query_id>')
@login_required
@log_view
def change_status(help_query_id):
    changed, status = HelpQuery.change_status(help_query_id)
    logger.debug(
        'Help query status is changed?: %s, completion status: %s', changed, status)
    if changed:
        if status:
            flash(
                f'Статус заявки на помощь #{help_query_id} поменялся на "Неактивная"')
        else:
            flash(
                f'Статус заявки на помощь #{help_query_id} поменялся на "Активная"')

    else:
        flash(
            f'Невозможно изменить статус заявки на помощь #{help_query_id}. Возможно данная заявка не существует или превышен лимит на активные заявки на помощь')

    return redirect(url_for('help.history'))


@help.route('/query/<query_slug>')
@login_required
@log_view
def query(query_slug):
    help_query = HelpQuery.query.filter_by(slug=query_slug).first()
    return render_template('help_query.html', query=help_query)


@help.route('/history')
@login_required
@log_view
def history():
    page = request.args.get('page', 1)
    logger.debug('History page received: %s', page)
    if isinstance(page, int) or page.isdigit():
        pages = Needy.get_help_queries(session.get('needy_id'), int(page))
        return render_template('history.html', pages=pages)

    flash('Произошла ошибка при формировании запроса. Попытайтесь использовать навигационные кнопки, а не вручную вводить адрес')
    return redirect(url_for('help.home'))


@help.route('/notifications')
@login_required
@log_view
def notifications():
    needy_id = session.get('needy_id')
    notifications = Needy.query.get(needy_id).notifications.all()

    return render_template('notifications.html', notifications=notifications)


@help.route('/')
@login_required
@log_view
def home():
    return render_template('index.html')


@help.route('/user/<user_slug>')
@log_view
def user_profile(user_slug):
    return '<h1>Чей-то профиль</h1>'


@help.route('/organization/<org_slug>')
@log_view
def company_profile(org_slug):
    return '<h1>Профиль какой-либо волонтерской организации</h1>'
