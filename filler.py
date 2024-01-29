import sys
import argparse
from faker import Faker
from datetime import timedelta
from random import choice, randint

from crypto import generate_key
from models import db, Volunteer, Organization, Needy, HelpQuery, VolunteerRegistrationKey, OrganizationRegistrationKey


parser = argparse.ArgumentParser(
    'Script to fill tables with random data', 'python filler.py [options]')
parser.add_argument('-a', '--all', action='store_true',
                    default=True, help='Fill all tables, by default True')
parser.add_argument('-n', '--needy', action='store_true', default=False,
                    help='Fill database with needy data, by default False')
parser.add_argument('-o', '--org', action='store_true', default=False,
                    help='Fill database with organizations data, by default False')
parser.add_argument('-d', '--drop', action='store_true', default=False,
                    help='Drop all tables before filling process, by default False')
parser.add_argument('-x', '--x', type=int, default=10,
                    help='Default number for x - based on this number elements will be created. By default x = 10, specify number between 1 and 100')

f = Faker()


def fillOrganizationRegistrationKey():
    global org_keys

    org_keys = []
    for i in range(x):
        org_keys.append(
            OrganizationRegistrationKey(
                key=generate_key()
            ))
        print(f'Processing OrganizationRegistrationKey #{i}')

    db.session.add_all(org_keys)
    db.session.commit()
    print('Done with OrganizationRegistrationKey')


def fillOrganization():
    global orgs

    orgs = []
    for i in range(x):
        key = org_keys[i].key.decode()

        orgs.append(
            Organization.create(
                'madiBEST99',
                key,
                about=f.text(),
                addr=f.unique.address(),
                owner_name=f.unique.name(),
                org_name=f.unique.company(),
                owner_email=f.unique.email(),
                username=f.unique.user_name(),
                contact_email=f.unique.email(),
                owner_phone=f.unique.msisdn()[:11],
                contact_phone=f.unique.msisdn()[:11],
            )[0])
        print(f'Processing Organization #{i}')
    print('Done with Organization')


def fillVolunteerRegistrationKey():
    global vol_keys

    vol_keys = []
    for i in range(x*10):
        org_id = org_keys[i % 10].id

        vol_keys.append(
            VolunteerRegistrationKey(
                key=generate_key(),
                organization_id=org_id,
            )
        )
        print(f'Processing VolunteerRegistrationKey #{i}')

    db.session.add_all(vol_keys)
    db.session.commit()
    print('Done with VolunteerRegistrationKey')


def fillVolunteer():
    for i in range(x*10):
        key = vol_keys[i].key.decode()

        Volunteer.create(
            'madiBEST99',
            key,
            email=f.unique.email(),
            last_name=f.last_name(),
            middle_name=f.last_name(),
            first_name=f.first_name(),
            about=f.unique.text().strip(),
            username=f.unique.user_name(),
            date_of_birth=f.date_object(),
            phone_number=f.unique.msisdn()[:11]
        )

        print(f'Processing Volunteer #{i}')

    print('Done with Volunteer')


def fillNeedy():
    global ns

    ns = []
    for i in range(x*10):
        ns.append(
            Needy.create(
                about=f.text(),
                name=f.unique.name(),
                addr=f.unique.address(),
                gender=choice(('male', 'female')),
                home_number=randint(100000, 999999),
                mobile_number=f.unique.msisdn()[:11],
                iin=randint(100000000000, 999999999999),
                relative_number=choice(
                    (f.unique.msisdn()[:11], randint(100000, 999999))),
                help_type=choice(
                    ('Инвалидность', 'Помощь по дому', 'Провизия', 'Общение')),
            ))
        print(f'Processing Needy #{i}')
    print('Done with Needy')


def fillHelpQuery():
    for i in range(x*100):
        from_needy = ns[i // 50].id

        HelpQuery.create(
            about=f.text(),
            from_needy=from_needy,
            duration=timedelta(hours=choice((72, 168, 744))),
            help_type=choice(
                ('Инвалидность', 'Помощь по дому', 'Провизия', 'Общение')),
        )
        print(f'Processing HelpQuery #{i}')
    print('Done with HelpQuery')


def fillAll(drop=True):
    # Strict order

    fillOrganizationRegistrationKey()
    fillOrganization()

    fillVolunteerRegistrationKey()
    fillVolunteer()

    fillNeedy()
    fillHelpQuery()


if __name__ == '__main__':
    args = parser.parse_args()

    x = args.x

    if x < 1 or x > 100 or not isinstance(x, int):
        raise('X should be an integer between 1 and 100 ')

    if args.drop:
        db.drop_all()

    db.create_all()

    if args.needy:
        fillNeedy()
        fillHelpQuery()
    elif args.org:
        fillOrganizationRegistrationKey()
        fillOrganization()
    elif args.all:
        fillAll()

    sys.exit()
