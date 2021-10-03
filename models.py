from logger import logger
from app import db, bcrypt
from datetime import datetime
from crypto import generate_key, generate_slug


class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(200), unique=True)
    password = db.Column(db.LargeBinary)

    def __repr__(self):
        return f'<AdminUser id: {self.id}, username: {self.username}>'

    @staticmethod
    def validate_creds(username, password):
        logger.warning('Validating Admin user %s:%s', username, password)
        admin = AdminUser.query.filter_by(username=username).first()

        if admin:
            try:
                password_match = bcrypt.check_password_hash(
                    admin.password, str(password))

                if password_match:
                    logger.warning('Successful Admin user validation')
                    return True
            except:
                logger.exception(
                    'Error in Admin user validation with %s:%s', username, password)

        logger.warning('Credenitals validation failed for Admin user')

    @staticmethod
    def create_admin(username, password):
        logger.warning('Got %s:%s in Admin user creation', username, password)
        if not AdminUser.query.filter_by(username=username).first():
            try:
                pwd_hash = bcrypt.generate_password_hash(str(password))
                admin = AdminUser(
                    username=str(username),
                    password=pwd_hash
                )

                db.session.add(admin)
                db.session.commit()
                logger.warning('Admin user created')
                return True
            except:
                logger.exception()


volunteer_org = db.Table(
    'volunteer_org',
    db.Column('volunteer_id', db.Integer, db.ForeignKey('volunteer.id')),
    db.Column('organization_id', db.Integer, db.ForeignKey('organization.id'))
)


class UpdateUserMixin(object):
    @classmethod
    def update_data_for(cls, user_id, form, to_overwrite={}):
        '''Updates data fields for object with given id from request.form

        Args:
            user_id (int): Volunteer.id, Organization.id or Needy.id
            form (dict): request.form object
            to_overwrite (dict, optional): Additional key-value fields to overwrite (useful for Needy's help_type)
        '''
        logger.debug('Updating data for %s #%s with to_overwrite:%s; form: %s',
                     cls.__name__, user_id, to_overwrite, form)
        try:
            user = cls.query.get(user_id)
            if user:
                try:
                    for attr, value in form.items():
                        if isinstance(value, list):
                            value = ', '.join(value)
                        if value and hasattr(cls, attr):
                            setattr(user, attr, value)

                    for attr, value in to_overwrite.items():
                        setattr(user, attr, value)
                except:
                    logger.exception(
                        'Error when updating data, probably unique constraint failed')
                    return False

                db.session.commit()
                logger.debug('Successful data update')
                return True
        except:
            logger.exception('Error in update_data_for')


class SecretUserMixin(object):
    '''
    Handles registration and login processes for Volunteer and Organization, which do use login and password unlike Needy
    '''

    @staticmethod
    def _get_session_data(user):
        logger.debug('Compiling session data for %s', user)

        if hasattr(user, 'orgs'):
            return {
                'id': user.id,
                'key': user.key,
                'email': user.email,
                'username': user.username,
                'first_name': user.first_name,
                'phone_number': user.phone_number,
            }

        return {
            'id': user.id,
            'key': user.key,
            'org_name': user.org_name,
            'username': user.username,
            'owner_name': user.owner_name,
            'owner_phone': user.owner_phone,
            'owner_email': user.owner_email,
            'contact_email': user.contact_email,
            'contact_phone': user.contact_phone,
        }

    @classmethod
    def create(cls, pwd: str, key: str, **kwargs):
        '''Create an object of Voluneer or Organization

        Args:
            pwd (string): Pass pure password from the form
            key (string): Pass pure key from the form
            **kwargs (string): Pass values for specific columns varying from models

        Returns:
            obj: Returns created object of given class or None if nothing was created
            dict: Returns session_data or None if nothing was created
        '''

        if hasattr(cls, 'orgs'):
            # Steps to register Volunteer:
            # 1) Check if given key exists in table VolunteerRegistrationKey
            # 2) Check if given key's used_status is False
            # 3) Set key's status to False
            # 4) Register volunteer
            # 5) Automatically connect volunteer to an organization

            logger.debug(
                'Creating Volunteer with password %s, key %s and data %s', pwd, key, kwargs)

            try:
                vol_key = VolunteerRegistrationKey.query.filter_by(
                    key=key.encode()).first()
                if vol_key and vol_key.used_status == False:
                    pwd_hash = bcrypt.generate_password_hash(pwd)

                    vol = cls(password=pwd_hash, **kwargs)
                    vol.orgs.append(vol_key.organization)
                    logger.debug('Volunteer now pertains to organization')

                    vol_key.used_status = True
                    logger.debug('Volunteer reigstration key is invalidated')

                    db.session.add(vol)
                    db.session.commit()

                    session_data = cls._get_session_data(vol)
                    logger.debug('Successful Volunteer creation')
                    return vol, session_data
            except:
                logger.exception('Error when registrating Volunteer')

        else:
            # Steps to regester Organization:
            # 1) + Check if given key exists in table OrganizationRegistrationKey
            # 2) + Check if given key's used_status is False
            # 3) + Register organization
            # 4) + Set key's status to False

            logger.debug(
                'Creating Organization with password %s, key %s and data %s', pwd, key, kwargs)

            try:
                org_key = OrganizationRegistrationKey.query.filter_by(
                    key=key.encode('utf-8')).first()
                if org_key and org_key.used_status == False:
                    pwd_hash = bcrypt.generate_password_hash(pwd)

                    org = cls(password=pwd_hash, **kwargs)

                    org_key.used_status = True
                    logger.debug('Organization reigstration key invalidated')

                    db.session.add(org)
                    db.session.commit()

                    session_data = cls._get_session_data(org)
                    logger.debug('Successful Organization creation')
                    return org, session_data
            except:
                logger.exception('Errror when registrating Organization')

        logger.debug(
            'Registration failed, probably registration key is already used or unique constraint failed')
        return None, None

    @classmethod
    def validate_creds(cls, username, password):
        '''Validates credentials of an object of Voluneer or Organization

        Args:
            username (string): Pass username from the form
            password (string): Pass pure not hashed password from the form

        Returns:
            obj: Returns object of given class or None if credentials validation failed
            dict: Returns session_data or None if credentials validation failed
            str: Returns message if credentials validation failed or an emtpy string
        '''
        logger.debug('Valdiating credentials for %s %s:%s',
                     cls.__name__, username, password)

        try:
            user = cls.query.filter_by(username=username).first()
            if user and password:
                pwd_hash = user.password.decode()
                pwd_correct = bcrypt.check_password_hash(pwd_hash, password)
                logger.debug('Do passwords match for %s: %s',
                             username, pwd_correct)

                if pwd_correct:

                    if hasattr(cls, 'orgs'):
                        session_data = cls._get_session_data(user)

                    else:
                        session_data = cls._get_session_data(user)

                    logger.debug('Successful login')
                    return user, session_data, None

                return None, None, 'Вы ввели неверный пароль'
        except:
            logger.exception('Error when validating credentials')
            return None, None, 'Упс! У нас произошла ошибка, повторите Ваш запрос позже'

        logger.debug(
            'Attempt to registrate user with existing username %s', username)
        return None, None, f'Пользователь с логином {username} не существует'


class CreateBaseMixin(object):
    @classmethod
    def create(cls, **kwargs):
        logger.debug('Creating in BaseMixin for %s with data %s',
                     cls.__name__, kwargs)
        try:
            obj = cls(**kwargs)

            db.session.add(obj)
            db.session.commit()
            logger.debug('Successful BaseMixin creation')
            return obj
        except:
            logger.exception('Creation in BaseMixin failed')


class Volunteer(SecretUserMixin, UpdateUserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    about = db.Column(db.Text)
    last_name = db.Column(db.String(100), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100), nullable=False)

    date_of_birth = db.Column(db.Date, nullable=False)

    email = db.Column(db.String(200), nullable=False)
    phone_number = db.Column(db.String(11), nullable=False)

    password = db.Column(db.LargeBinary(), nullable=False)
    username = db.Column(db.String(31), nullable=False, unique=True)

    registered = db.Column(db.DateTime, default=datetime.now)
    slug = db.Column(db.String(200), default=generate_slug, unique=True)
    key = db.Column(db.LargeBinary(), default=generate_key, unique=True)

    bookmarks = db.relationship(
        'Bookmark', backref='volunteer', lazy='dynamic')
    orgs = db.relationship('Organization', secondary=volunteer_org,
                           backref=db.backref('volunteers', lazy='dynamic'))
    # completed_help_queries = db.relationship('HelpQuery', backref='completed_by_volunteer', lazy='dynamic')

    def __repr__(self):
        return f'<Volunteer id: {self.id}, name: {self.last_name}, email: {self.email}, username: {self.username}>'

    @staticmethod
    def get_completed_help_queries(id):
        logger.debug('Fetching completed help queries for volunteer #%s', id)
        if Volunteer.query.get(id):
            return QueryCompletion.query.filter_by(vol_id=id).order_by(QueryCompletion.start_date.desc()).all()

    def get_completed_help_queries_count(self):
        if Volunteer.query.filter_by(id=self.id).first():
            return QueryCompletion.query.filter_by(vol_id=self.id).filter_by(accepted=True).count()


class Organization(SecretUserMixin, UpdateUserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    about = db.Column(db.Text)
    addr = db.Column(db.String(200))
    contact_phone = db.Column(db.String(11), unique=True)
    contact_email = db.Column(db.String(200), unique=True)
    org_name = db.Column(db.String(200), nullable=False, unique=True)

    owner_name = db.Column(db.String(200), nullable=False)
    owner_phone = db.Column(db.String(11), nullable=False, unique=True)
    owner_email = db.Column(db.String(200), nullable=False, unique=True)

    password = db.Column(db.LargeBinary(), nullable=False)
    username = db.Column(db.String(31), nullable=False, unique=True)

    registered = db.Column(db.DateTime, default=datetime.now)
    slug = db.Column(db.String(200), default=generate_slug, unique=True)
    key = db.Column(db.LargeBinary(), default=generate_key, unique=True)

    bookmarks = db.relationship(
        'Bookmark', backref='organization', lazy='dynamic')
    registration_keys = db.relationship(
        'VolunteerRegistrationKey', backref='organization', lazy='dynamic')

    def __repr__(self):
        return f'<Organization id: {self.id}, name: {self.org_name}, email: {self.contact_email}, owner: {self.owner_name}>'

    @staticmethod
    def generate_vol_registration_keys(org_key=None, n=1):
        '''Generates string of registration keys for volunteers

        Args:
            org_key (bytes): Unique organization key  
            n (int, optional): Number of keys to generate. Defaults to 1.

        Returns:
            str: Returns well-formated string of registration keys for volunteers
        '''
        logger.debug(
            'Generating %s volunteer registration keys for %s', n, org_key)

        if org_key:
            org = Organization.query.filter_by(key=org_key).first()
        else:
            org = Organization.query.first()
        try:
            if org:
                vol_keys = []
                for _ in range(n):
                    vol_keys.append(
                        VolunteerRegistrationKey(
                            key=generate_key(),
                            organization_id=org.id,
                        )
                    )

                db.session.add_all(vol_keys)
                db.session.commit()
                logger.debug('Successfully fetched vol registration keys')
                return '\n'.join([vol_key.key.decode() for vol_key in vol_keys])
        except:
            logger.exception('Couldn\'t generate volunteer registration keys')


class VolunteerRegistrationKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    key = db.Column(db.LargeBinary, unique=True)
    used_status = db.Column(db.Boolean, default=False)
    organization_id = db.Column(db.Integer, db.ForeignKey(
        'organization.id'), nullable=False)

    def __repr__(self):
        return f'<Volunteer Registration Key: {self.key}, used: {self.used_status}, for organization №{self.organization.id}>'


class OrganizationRegistrationKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    key = db.Column(db.LargeBinary, unique=True)
    used_status = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Organization Registration Key: {self.key}, used: {self.used_status}>'

    @staticmethod
    def generate_org_registration_keys(n=5):
        '''Generates a list registration keys for organizations

        Args:
            n (int, optional): Number of keys to generate. Defaults to 5.

        Returns:
            list: List of keys of string type
        '''
        logger.debug('Generating %s organization registration keys ', n)

        objs = []
        try:
            for _ in range(n):
                objs.append(
                    OrganizationRegistrationKey(key=generate_key())
                )
            db.session.add_all(objs)
            db.session.commit()
            logger.debug('Successfully fetched org registration keys')
            return '\n'.join([obj.key.decode() for obj in objs])
        except:
            logger.exception(
                'Couldn\'t generate organization registration keys')


class Needy(CreateBaseMixin, UpdateUserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    addr = db.Column(db.String(200))
    gender = db.Column(db.String(6))
    name = db.Column(db.String(200), nullable=False)
    iin = db.Column(db.String(12), nullable=False, unique=True)

    about = db.Column(db.Text)
    help_type = db.Column(db.String(200))

    home_number = db.Column(db.String(6))
    mobile_number = db.Column(db.String(12))
    relative_number = db.Column(db.String(12))

    registered = db.Column(db.DateTime, default=datetime.now)
    slug = db.Column(db.String(200), default=generate_slug, unique=True)
    key = db.Column(db.LargeBinary(), default=generate_key, unique=True)

    help_queries = db.relationship(
        'HelpQuery', backref='needy', lazy='dynamic')
    notifications = db.relationship(
        'Notification', backref='needy', lazy='dynamic')

    def __repr__(self):
        return f'<Needy id: {self.id}, name: {self.name}, iin: {self.iin}>'

    @staticmethod
    def get_help_queries(needy_id, page: int, per_page=5):
        '''Get paginated list of help queries that were created by given needy

        Args:
            needy_id (int): Needy id
            page (int): Current page number
            per_page (int, optional): Displayed help queries per page. Defaults to 5.

        Returns:
            list: Pagniated list of help queries
        '''
        logger.debug(
            'Fetching help queries for needy #%s on page %s', needy_id, page)

        try:
            return Needy.query.get(needy_id).help_queries.filter_by(deleted=False).order_by(HelpQuery.date.desc()).paginate(page=page, per_page=per_page)
        except:
            logger.exception(
                'Couldn\'t fetch help queries for needy #%s', needy_id)


class HelpQuery(CreateBaseMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    about = db.Column(db.Text)
    duration = db.Column(db.Interval())
    help_type = db.Column(db.String(200))

    deleted = db.Column(db.Boolean, default=False)

    from_needy = db.Column(
        db.Integer, db.ForeignKey('needy.id'), nullable=False)

    completion_date = db.Column(db.DateTime)
    completion_status = db.Column(db.Boolean, default=False)
    completed_by = db.Column(db.Integer, db.ForeignKey('volunteer.id'))

    date = db.Column(db.DateTime, default=datetime.now)
    slug = db.Column(db.String(200), default=generate_slug, unique=True)

    def __repr__(self):
        return f'<HelpQuery id: {self.id}, from: {self.from_needy}, completion status: {self.completion_status}>'

    @staticmethod
    def complete(notification_id):
        '''Marks HelpQuery as completed, volunteer top ups his completed help queries history, notification is deleted but added to history

        Args:
            notification_id (int): Notification object's id
        Returns:
            bool: Returns True if HelpQuery was successfully marked as completed, otherwise returns False
        '''
        logger.debug(
            'Marking HelpQuery as completed from notifcation #%s', notification_id)

        try:
            notification = Notification.query.filter_by(
                deleted=False).filter_by(id=notification_id).first()

            if notification and notification.accepted:
                hq_id = notification.help_query_id
                hq = HelpQuery.query.get(hq_id)
                if hq:
                    if notification.from_volunteer:
                        vol_id = notification.from_volunteer
                    elif notification.to_volunteer:
                        vol_id = notification.to_volunteer
                    else:
                        return False
                    hq.completed_by = vol_id
                    # TODO: idk about if needies will renew help query each time their help query is completed (can be done by volunteers though!)
                    # hq.completion_date = datetime.now()
                    # completion_status = True

                    notification.deleted = True

                    db.session.commit()
                    logger.debug('Successful help query completion')
                    return True
        except:
            logger.exception('Error when marking HelpQuery as completed')

    @staticmethod
    def delete(id):
        '''Marks help query as deleted

        Args:
            id (int): Help query id

        Returns:
            bool: True if successfully deleted, otherwise False
        '''
        logger.debug('Marking help query #%s as deleted', id)

        try:
            hq = HelpQuery.query.get(id)
            if hq:
                hq.deleted = True

                db.session.commit()
                logger.debug('Successful help query deletion')
                return True
        except:
            logger.exception('Cannot mark help query #%s as deleted', id)

    @staticmethod
    def get_pages(page: int, per_page=5):
        '''Get paginated list of help queries for displaying to volunteers and organizations 

        Args:
            page (int): Current page number
            per_page (int, optional): Number of help queries per page. Defaults to 5.

        Returns:
            list: Paginated list of help queries
        '''
        logger.debug(
            'Fetching paginated help queries for volunteers on page %s', page)
        try:
            return HelpQuery.query.filter_by(deleted=False).filter_by(completion_status=False).order_by(HelpQuery.date.desc()).paginate(page=page, per_page=per_page)
        except:
            logger.exception('Cannot fetch help queries for volunteers')

    @staticmethod
    def change_status(id):
        '''Changes help queries status to the opposite

        Args:
            id (int): Help query id

        Returns:
            bool: True if status was changed successfully, otherwise False
            bool: To what status was changed, otherwise False
        '''
        logger.debug('Changing status of help query #%s', id)

        try:
            help_query = HelpQuery.query.get(id)
            if help_query:

                # If help query is changed from completed to active
                if help_query.completion_status:
                    if HelpQuery.query.filter_by(from_needy=help_query.from_needy).filter_by(completion_status=False).count() >= 10:
                        logger.debug(
                            'Cannot change help query status due to overload of help queries')
                        return False, None

                    help_query.completion_status = False

                # Help query changes status from active to completed
                else:
                    help_query.completion_status = True
                    help_query.completion_date = datetime.now()

                db.session.commit()
                logger.debug('Successfully changed help query status')
                return True, help_query.completion_status

            logger.debug('No help query found to change status')
            return False, False

        except:
            logger.exception('Error when changing help query id')
            return False, None


class QueryCompletion(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    needy_id = db.Column(db.Integer, db.ForeignKey('needy.id'), nullable=False)
    vol_id = db.Column(db.Integer, db.ForeignKey(
        'volunteer.id'), nullable=False)
    org_id = db.Column(db.Integer, db.ForeignKey(
        'organization.id'), nullable=False)
    help_query_id = db.Column(db.Integer, db.ForeignKey(
        'help_query.id'), nullable=False)
    notification_id = db.Column(db.Integer, db.ForeignKey(
        'notification.id'), nullable=False, unique=True)

    about = db.Column(db.Text, nullable=False)
    minutes = db.Column(db.Integer, nullable=False)
    accepted = db.Column(db.Boolean, default=False)
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    completion_date = db.Column(db.DateTime)

    def __repr__(self):
        return f'<QueryCompletion id: {self.id}, vol_id: {self.vol_id}, org_id: {self.org_id}, not_id: {self.notification_id}, minutes: {self.minutes}, accepted: {self.accepted}>'

    def get_needy_name(self):
        if needy := Needy.query.get(self.needy_id):
            return needy.name

    def get_help_query_info(self):
        if hq := HelpQuery.query.get(self.help_query_id):
            return hq.help_type + '\n\n' + hq.about

    def get_org_name(self):
        if org := Organization.query.get(self.org_id):
            return org.org_name

    def accept(self):
        self.accepted = True
        self.completion_date = datetime.now()
        db.session.commit()
        return True

    def update(self, minutes: int, about: str):
        self.about = about
        self.minutes = minutes
        db.session.commit()
        return True

    @staticmethod
    def create_or_update(notification_id, **kwargs):
        if qc := QueryCompletion.query.filter_by(notification_id=notification_id).first():
            for key, value in kwargs.items():
                if hasattr(QueryCompletion, key):
                    setattr(qc, key, value)

        else:
            qc = QueryCompletion(notification_id=notification_id, **kwargs)
            db.session.add(qc)

        db.session.commit()
        return qc


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    read = db.Column(db.Boolean, default=False)
    deleted = db.Column(db.Boolean, default=False)
    accepted = db.Column(db.Boolean, default=False)

    needy_id = db.Column(db.Integer, db.ForeignKey('needy.id'), nullable=False)
    help_query_id = db.Column(db.Integer, db.ForeignKey(
        'help_query.id'), nullable=False)
    help_query_slug = db.Column(db.String(200), nullable=False)

    to_volunteer = db.Column(db.Integer, db.ForeignKey('volunteer.id'))
    from_organization = db.Column(db.Integer, db.ForeignKey('organization.id'))

    to_organization = db.Column(db.Integer, db.ForeignKey('organization.id'))
    from_volunteer = db.Column(db.Integer, db.ForeignKey('volunteer.id'))

    date = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f'<Notification id: {self.id}, date: {self.date}, on help query: {self.help_query_id}>'

    @staticmethod
    def accept(id, by_org=False):
        '''Accept notification -> partake in help query as volunteer or allow volunteer to help, and display them additional data fields

        Args:
            id (int): User id (volunteer.id or organization.id)
            by_org (bool, optional): Accept notification from volunteer -> allow volunteer to help. Defaults to False.

        Returns:
            bool: True if everything went successfully
        '''
        logger.debug('Acceptiong notification #%s, by org?: %s', id, by_org)

        try:
            n = Notification.query.filter_by(
                deleted=False).filter_by(id=id).first()

            if n:
                n.accepted = True

                # If was submitted by Organization (org clicke button) -> create notifcation for volunteer, where info will be displayed
                if by_org:
                    vol_id = n.from_volunteer
                    org_id = n.to_organization

                    n.to_volunteer = vol_id
                    n.from_organization = org_id

                db.session.commit()
                logger.debug('Successfully accepted notification')
                return True
        except:
            logger.exception('Error in accept notification')

    @staticmethod
    def get_sender(id):
        '''Get information about volunteer or organization like whom notification came from

        Args:
            id (int): User id

        Returns:
            dict: Dictionary containing information about sender
        '''
        logger.debug('Fetching get sender data for notification #%s', id)

        try:
            n = Notification.query.filter_by(
                deleted=False).filter_by(id=id).first()
            if n:
                info = {}

                if n.from_volunteer:
                    vol = Volunteer.query.get(n.from_volunteer)
                    info['from'] = vol.first_name + ' ' + vol.last_name

                else:
                    org = Organization.query.get(n.from_organization)
                    info['from'] = org.org_name
                    info['owner'] = org.owner_name

                return info
        except:
            logger.exception(
                'Oops, cannot get sender for notification #%s', id)

    @staticmethod
    def get_notifications(user_id: int, to_volunteer: bool = True):
        '''Returns notifications list that are not marked as read, hence should pop up in the notifications bar

        Args:
            user_id (int): Volunteer id or Organization id
            to_volunteer (bool, optional): Specify False, when passing organization_id into user_id to get notifications for organization. Defaults to True.

        Returns:
            list: List of notifications objects
        '''
        logger.debug(
            'Fetching notifications for user #%s, volunteer?: %s', user_id, to_volunteer)

        try:
            if to_volunteer:
                return Notification.query.filter_by(deleted=False).filter_by(to_volunteer=user_id).filter_by(read=False).order_by(Notification.date.desc()).all()
            return Notification.query.filter_by(deleted=False).filter((Notification.to_organization == user_id) | (Notification.from_organization == user_id)).filter_by(read=False).order_by(Notification.date.desc()).all()
        except:
            logger.exception(
                'Oops, cannot get notifications for user #%s', user_id)

    @staticmethod
    def mark_as_read(slug: str):
        '''Marks notification as read by given slug so it will not show up in the notifications bar anymore

        Args:
            notification_slug (str): Notification slug

        Returns:
            bool: True if notification was sucessfully marked as read
        '''
        logger.debug('Marking as "read" notification with slug %s', slug)

        try:
            n = Notification.query.filter_by(
                deleted=False).filter_by(slug=slug).first()
            n.read = True

            db.session.commit()
            return True
        except:
            logger.exception(
                'Oops, cannot mark as "read" notification #%s', id)

    @staticmethod
    def create(from_id: int, to_id: int, help_query, as_volunteer: bool = True):
        '''Creates a notification for needies that their help query was looked through. Also notifies volunteer that he/she is responsible for this help query or notifies organization that volunteer is willing to work on this help query

        Args:
            from_id (int): Notification creator's id: can be organization's or volunteer's id
            to_id (int): Notification receiver's id: can be volunteer's or organization's id
            help_query (obj): Help query object
            as_volunteer (bool, optional): Specify False, when creating notification for volunteer from organization

        Returns:
            obj: Returns created Notification object
        '''
        logger.debug('Creating notification (as volunteer?: %s) from #%s to #%s for help query %s',
                     as_volunteer, from_id, to_id, help_query)

        try:
            help_query_id = help_query.id
            help_query_slug = help_query.slug
            needy_id = help_query.needy.id

            if as_volunteer:
                # If volunteer had already asked permission from given organization on this help query
                if Notification.query.filter_by(deleted=False).filter_by(help_query_id=help_query_id).filter_by(from_volunteer=from_id).filter_by(to_organization=to_id).first():
                    return None
                # If some organization had already chosen this volunteer for this help query
                if Notification.query.filter_by(deleted=False).filter_by(help_query_id=help_query_id).filter_by(to_volunteer=from_id).first():
                    return None

                n = Notification(
                    needy_id=needy_id,
                    to_organization=to_id,
                    from_volunteer=from_id,
                    help_query_id=help_query_id,
                    help_query_slug=help_query_slug,
                )
                logger.debug('Notification from volunteer compiled')

            else:
                # If organization organization had already chosen this volunteer for this help action
                if Notification.query.filter_by(deleted=False).filter_by(help_query_id=help_query_id).filter_by(from_organization=from_id).filter_by(to_volunteer=to_id).first():
                    return None
                # If volunteer had already submitted help query to given organization and waiting for permission
                if Notification.query.filter_by(deleted=False).filter_by(help_query_id=help_query_id).filter_by(to_organization=from_id).filter_by(from_volunteer=to_id).first():
                    return None

                n = Notification(
                    needy_id=needy_id,
                    to_volunteer=to_id,
                    from_organization=from_id,
                    help_query_id=help_query_id,
                    help_query_slug=help_query_slug,
                )
                logger.debug('Notification from organization compiled')

            db.session.add(n)
            db.session.commit()
            logger.debug('Notification has been created successfully')
            return n

        except:
            logger.exception('Cannot create notification!!!')


class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    help_query_slug = db.Column(
        db.String(200), db.ForeignKey('help_query.slug'))

    volunteer_id = db.Column(db.Integer, db.ForeignKey('volunteer.id'))
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'))

    date = db.Column(db.DateTime, default=datetime.now)
    slug = db.Column(db.String(200), default=generate_slug, unique=True)

    def __repr__(self):
        by = self.volunteer_id if self.volunteer_id else self.organization_id
        return f'<Bookmark id: {self.id}, for help query: {self.help_query_slug}, created by: {by}>'

    @staticmethod
    def add_or_remove(help_query_slug: str, volunteer_id=None, organization_id=None):
        '''Add or remove (if already in bookmarks) help query to bookmarks

        Args:
            help_query_slug (str): Help query slug
            volunteer_id (int, optional): Volunteer id, specify without organization_id. Defaults to None.
            organization_id (int, optional): Organization id, specify without volunteer_id. Defaults to None.

        Returns:
            obj: Returns created Bookmark object. If Bookmark was removed returns False
        '''
        logger.debug('Adding or removing bookamrk for vol #%s or org %s for help query with slug %s',
                     volunteer_id, organization_id, help_query_slug)

        try:
            if volunteer_id:
                existing_bookmark = Bookmark.query.filter_by(
                    help_query_slug=help_query_slug, volunteer_id=volunteer_id).first()

                if existing_bookmark:
                    db.session.delete(existing_bookmark)
                    db.session.commit()
                    return False

                b = Bookmark(
                    help_query_slug=help_query_slug,
                    volunteer_id=volunteer_id,
                )

            elif organization_id:
                existing_bookmark = Bookmark.query.filter_by(
                    help_query_slug=help_query_slug, organization_id=organization_id).first()

                if existing_bookmark:
                    db.session.delete(existing_bookmark)
                    db.session.commit()
                    return False

                b = Bookmark(
                    help_query_slug=help_query_slug,
                    organization_id=organization_id,
                )

            db.session.add(b)
            db.session.commit()
            logger.debug('Successfully added/removed bookmark')
            return b

        except:
            logger.exception('Cannot add/remove bookmark')
