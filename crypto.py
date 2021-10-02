# from secrets import token_urlsafe
# from cryptography.fernet import Fernet


# f = Fernet(Fernet.generate_key())

from uuid import uuid4


# binary key -> mandatory field for registration to validate for genuinity of volunteers and organizations
def generate_key():
    return str(uuid4().hex + uuid4().hex[:12]).encode()
    # return f.generate_key()


# slug -> link to profile or whatever
def generate_slug():
    return uuid4().hex[:22]
    # return token_urlsafe(16)


if __name__ == '__main__':
    for _ in range(10):
        print('Key:', generate_key())
        print('Slug:', generate_slug())
