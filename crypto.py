from secrets import token_urlsafe
from cryptography.fernet import Fernet


f = Fernet(Fernet.generate_key())


# binary key -> mandatory field for registration to validate for genuinity of volunteers and organizations
def generate_key():
    return f.generate_key()


# slug -> link to profile or whatever
def generate_slug():
    return token_urlsafe(16)


if __name__ == '__main__':
    for _ in range(10):
        print('Key:', generate_key())
        print('Slug:', generate_slug())
