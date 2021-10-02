from flask import Blueprint, request, url_for, redirect, render_template, session, flash

from models import Volunteer, Organization, HelpQuery, Notification, Bookmark, QueryCompletion, Needy
from validators import Validator

from views import log_view, wraps, logger, recaptcha
from datetime import date


validator = Validator()

volunteer = Blueprint('volunteer', __name__, static_folder='../static',
                      template_folder='../templates/volunteer')


# strftime('%d.%m.%y %H:%m:%S')


def login_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        vol = session.get('vol', {})
        org = session.get('org', {})

        logger.debug('In login_required Vol: %s and Org: %s', vol, org)

        if vol and org:
            session.debug('Both volunteer and organization session items are present. Redirecting to register page')
            return redirect(url_for('volunteer.register'))

        if (vol or org) and (Volunteer.query.filter_by(key=vol.get('key')).first() or Organization.query.filter_by(key=org.get('key')).first()):
            if org:
                session['unread_notifications'] = bool(
                    Notification.get_notifications(org.get('id'), to_volunteer=False))
            else:
                session['unread_notifications'] = bool(
                    Notification.get_notifications(vol.get('id')))

            logger.debug('Volunteer is logged in')
            return f(*args, **kwargs)

        logger.debug('Volunteer or Organization is not authenicated')
        session.pop('org', None)
        session.pop('vol', None)
        return redirect(url_for('volunteer.register'))

    return inner


@volunteer.route('/login', methods=['GET', 'POST'])
@log_view
def login():
    if request.method == 'POST':
        # if recaptcha.verify():
        username = request.form.get('username')
        password = request.form.get('password')

        volunteer, session_data, msg = Volunteer.validate_creds(
            username, password)

        if volunteer:
            session['vol'] = session_data
            return redirect(url_for('volunteer.index'))

        logger.debug('Gonna display error login message %s', msg)
        flash(msg)

        # else:
        #     flash('Подтвердите капчу!')

    return render_template('home/register.html', login=True)


@volunteer.route('/logout')
@login_required
@log_view
def logout():
    session.pop('vol', None)
    session.pop('org', None)

    logger.debug('User logged out -> session: %s', session.items())
    return redirect(url_for('home'))


@volunteer.route('/join-org')
@login_required
@log_view
def join_org():
    if 'org' in session:
        return redirect(url_for('volunteer.index'))

    return 'Here you can join some volunteer clubs if you have volunteer registration key(s)'


@volunteer.route('/profile')
@login_required
@log_view
def profile():
    if 'org' in session:
        id = session.get('org').get('id')
        user = Organization.query.get(id)
    else:
        id = session.get('vol').get('id')
        user = Volunteer.query.get(id)

    return render_template('v_profile.html', user=user, edit=False)


@volunteer.route('/profile-edit', methods=['GET', 'POST'])
@login_required
@log_view
def edit_profile():
    if 'org' in session:
        id = session.get('org').get('id')
        user_model = Organization
    else:
        id = session.get('vol').get('id')
        user_model = Volunteer

    if request.method == 'GET':
        user = user_model.query.get(id)
        return render_template('v_profile.html', user=user, edit=True)

    form = request.form
    logger.debug('Form in edit_pofile: %s', form)

    success = user_model.update_data_for(id, form)

    if success:
        flash('Данные успешно обновлены')
    else:
        flash('Произошла ошибка при обновлении данных, указанные телефон и/или электронная почта уже заняты, введите другие данные')

    return redirect(url_for('volunteer.profile'))


@volunteer.route('/news')
@login_required
@log_view
def news():
    return render_template('v_news.html')


@volunteer.route('/colleagues')
@login_required
@log_view
def colleagues():
    if 'org' in session:
        org_id = session.get('org').get('id')
        colleagues = Organization.query.get(org_id).volunteers.all()
        as_vol = False
    else:
        vol_id = session.get('vol').get('id')
        colleagues = Volunteer.query.get(vol_id).orgs
        as_vol = True

    return render_template('v_colleagues.html', as_vol=as_vol, colleagues=colleagues)


@volunteer.route('/accept/<int:notification_id>')
@login_required
@log_view
def accept_notifcation(notification_id):
    # GET method then redirect
    status = Notification.accept(notification_id, by_org='org' in session)
    logger.debug('Notification is e accepted')

    if status:
        flash('Успешно принята заявка. Если Вы волонтер, то вы получите дополнительную информацию о нуждающемся. Если же Вы волонтерская организация, то волонтер получит дополнительную информацию о нуждающимся')
    else:
        flash('Произошла ошибка. Данное уведомление не существует')

    return redirect(url_for('volunteer.notifications'))


@volunteer.route('/complete/<int:notification_id>', methods=['POST', 'GET'])
@login_required
def complete(notification_id):
    if notification := Notification.query.filter_by(deleted=False).filter_by(id=notification_id).first():
        if 'org' in session:
            org_id = session.get('org').get('id')
            if not (org_id == notification.to_organization or org_id == notification.from_organization):
                flash(
                    'Руководитель волонтерского центра, Вы не имеете прав на посещение данной страницы')
                return redirect(url_for('volunteer.index'))

        else:
            vol_id = session.get('vol').get('id')
            if not (vol_id == notification.to_volunteer or vol_id == notification.from_volunteer):
                flash('Волонтер, Вы не имеете прав на посещение данной страницы')
                return redirect(url_for('volunteer.index'))

        if request.method == 'GET':
            vol_id = notification.from_volunteer or notification.to_volunteer
            vol = Volunteer.query.get(vol_id)
            hq = HelpQuery.query.get(notification.help_query_id)
            
            data = {}

            data['notification_id'] = notification_id
            
            data['vol_id'] = vol.id
            data['vol_name'] = vol.last_name + ' ' + vol.first_name

            data['hq_id'] = hq.id
            data['hq_about'] = hq.about
            data['help_type'] = hq.help_type

            data['needy_id'] = notification.needy_id
            data['needy_name'] = hq.needy.name

            if 'org' in session:
                if qc := QueryCompletion.query.filter_by(accepted=False).filter_by(notification_id=notification_id).first():
                    data.update({
                        'about': qc.about,
                        'minutes': qc.minutes,
                    })

            return render_template('v_complete.html', data=data)

        form = request.form
        if 'org' in session:
            if qc := QueryCompletion.query.filter_by(accepted=False).filter_by(notification_id=notification_id).first():
                qc.update(
                    about=form.get('about'),
                    minutes=form.get('minutes'),
                )

            else:
                qc = QueryCompletion.create_or_update(
                    notification_id,
                    about=form.get('about'),
                    minutes=form.get('minutes'),
                    needy_id=notification.needy_id,
                    help_query_id=notification.help_query_id,
                    vol_id=notification.to_volunteer or notification.from_organization,
                    org_id=notification.to_organization or notification.from_organization,
                )

            if HelpQuery.complete(notification_id):
                flash('Вы подтвердили выполнение запроса на помощь')
                qc.accept()
            else:
                flash('Произошла ошибка, повторите позже')
                
        else:
            QueryCompletion.create_or_update(
                notification_id,
                about=form.get('about'),
                minutes=form.get('minutes'),
                needy_id=notification.needy_id,
                help_query_id=notification.help_query_id,
                vol_id=notification.to_volunteer or notification.from_organization,
                org_id=notification.to_organization or notification.from_organization,
            )
            flash(
                'Ожидайте подтверждения выполнения запроса на помощь от руководителя волонтерского центра')

    else:
        flash('Данного уведомления не существует')

    return redirect(url_for('volunteer.index'))


@volunteer.route('/bookmarks')
@login_required
@log_view
def bookmarks():
    org_id = session.get('org', {}).get('id')
    if org := Organization.query.get(org_id):
        bookmarks = org.bookmarks.all()
    else:
        vol_id = session.get('vol').get('id')
        bookmarks = Volunteer.query.get(vol_id).bookmarks.all()
    print('!!!', bookmarks)

    return render_template('v_bookmarks.html', bookmarks=bookmarks)


@volunteer.route('/bookmarks-add-remove/<query_slug>')
@login_required
@log_view
def bookmarks_add_remove(query_slug):
    if 'org' in session:
        org_id = session.get('org').get('id')
        b = Bookmark.add_or_remove(query_slug, organization_id=org_id)
    else:
        vol_id = session.get('vol').get('id')
        b = Bookmark.add_or_remove(query_slug, volunteer_id=vol_id)

    if b:
        flash('Данная заявка на помощь добавлена в ваши закладки')
    else:
        flash('Данная заявка на помощь удалена из ваших закладок')

    return redirect(url_for('volunteer.query', query_slug=query_slug))


@volunteer.route('/main')
@volunteer.route('/')
@login_required
@log_view
def index():
    page = request.args.get('page', 1)
    if isinstance(page, int) or page.isdigit():
        page = int(page)
        pages = HelpQuery.get_pages(page)

        return render_template('v_index.html', pages=pages)

    flash('Произошла ошибка при формировании запроса. Попытайтесь использовать навигационные кнопки, а не вручную вводить адрес')
    return redirect(url_for('volunteer.index'))


@volunteer.route('/history')
@login_required
@log_view
def history():
    if 'org' in session:
        # flash('У вас ничего не будет отображаться в истории, так как руководитель волонтерского центра не может отвечать на запросы на помощь')
        return redirect(url_for('volunteer.index'))

    vol_id = session.get('vol').get('id')
    vol = Volunteer.query.get(vol_id)
    vol_name = vol.last_name + ' ' + vol.first_name

    completed_help_queries = Volunteer.get_completed_help_queries(vol_id)

    logger.debug('History for volunteer: %s', completed_help_queries)
    return render_template('v_history.html', vol_name=vol_name, queries=completed_help_queries)


@volunteer.route('/notifications')
@login_required
@log_view
def notifications():
    if 'org' in session:
        org_id = session.get('org').get('id')
        notifications = Notification.get_notifications(
            org_id, to_volunteer=False)
    else:
        vol_id = session.get('vol').get('id')
        notifications = Notification.get_notifications(vol_id)

    info = []
    for notification in notifications:
        info.append(Notification.get_sender(notification.id))

    return render_template('v_notifications.html', notifications=notifications, info=info)


@volunteer.route('/query/<query_slug>')
@login_required
@log_view
def query(query_slug):
    help_query = HelpQuery.query.filter_by(slug=query_slug).first()
    if not help_query:
        return redirect(url_for(('volunteer.index')))

    volunteers = ()
    orgs = ()

    if 'org' in session:
        org_id = session.get('org').get('id')
        volunteers = Organization.query.get(org_id).volunteers.all()
    else:
        vol_id = session.get('vol').get('id')
        orgs = Volunteer.query.get(vol_id).orgs

    return render_template('v_query.html', query=help_query, volunteers=volunteers, orgs=orgs)


@volunteer.route('/submit/<query_slug>', methods=['POST'])
@login_required
@log_view
def submit_help(query_slug):
    # if recaptcha.verify():

    help_query = HelpQuery.query.filter_by(slug=query_slug).first()

    if 'org' in session:
        # Send notification to volunteer that he will be responsible for this doing, show him addr, phone number about problem information etc
        # Make help query as "in process"

        vol_id = request.form.get('chosen_vol_id')
        org_id = session.get('org').get('id')

        n = Notification.create(
            to_id=vol_id,
            from_id=org_id,
            as_volunteer=False,
            help_query=help_query,
        )

        if n:
            flash(
                'Указанный волонтер будет уведомлен, что он назначен на оказание помощи.')
        else:
            flash('Данный волонтер уже был уведомлен о назначени на оказание помощи либо данный волонтер уже ждет разрешение на оказание помощи от вас')

    elif 'vol' in session:
        # Send notification to head volunteer or receive data about it and add it to history as "active" help query submission
        # Then wait for head volunteer to receive the acceptance in messages

        org_id = request.form.get('chosen_org_id')
        vol_id = session.get('vol').get('id')

        n = Notification.create(
            to_id=org_id,
            from_id=vol_id,
            help_query=help_query,
        )

        if n:
            flash(
                'Спасибо! Ваша волонтерская организация будет уведомлена о вашем запросе на оказание помощи')
        else:
            flash('Вы уже раннее откликнулись на помощь либо волонтерская организация уже дала разрешение на оказание помощи')

    # TODO: Also then send notifiction to needy that their help query was looked through

    # else:
    #     flash('Подтвердите капчу')

    # return redirect(url_for('volunteer.index'))
    return redirect(url_for('volunteer.query', query_slug=query_slug))


@volunteer.route('/register', methods=['GET', 'POST'])
@log_view
def register():
    if request.method == 'POST':
        # if recaptcha.verify():
        form = request.form

        phone_number, email, username = form.get(
            'phone_number'), form.get('email'), form.get('username')

        if Volunteer.query.filter_by(phone_number=phone_number).first():
            flash(
                f'Пользователь с данным номером телефона {phone_number} уже зарегистрирован')
        elif Volunteer.query.filter_by(email=email).first():
            flash(
                f'Пользователь с данным электронным адресом {email} уже зарегистрирован')
        elif Volunteer.query.filter_by(username=username).first():
            flash(
                f'Пользователь с данным логином {username} уже зарегистрирован')
        elif not all((validator.v_email(email), validator.v_phone(phone_number))):
            flash(f'Телефон, электронная почта или псевдоним указаны в неверном формате')
        else:
            volunteer, session_data = Volunteer.create(
                form.get('password'),
                form.get('key'),
                email=email,
                username=username,
                about=form.get('about'),
                phone_number=phone_number,
                last_name=form.get('last_name'),
                first_name=form.get('first_name'),
                middle_name=form.get('middle_name'),
                date_of_birth=date(
                    *list(map(lambda a: int(a), form.get('date_of_birth').split('-')))),
            )
            if volunteer:
                session['vol'] = session_data

                flash('Успешная регистрация!')
                return redirect(url_for('volunteer.index'))

            flash('Введенный ключ не действителен или уже использован. Попросите руководителя волонтерского ценра сгенерировать для Вас ключ')

        # if validation above failed
        return redirect(url_for('volunteer.register'))

        # else:
        #     flash('Ага, робот! Подвердите каптчу еще раз')
        #     return redirect(url_for('volunteer.register'))

    else:
        vol = session.get('vol', {})
        org = session.get('org', {})

        if (vol or org) and (Volunteer.query.filter_by(key=vol.get('key')).first() or Organization.query.filter_by(key=org.get('key')).first()):
            return redirect(url_for('volunteer.index'))

        return render_template('home/register.html')
