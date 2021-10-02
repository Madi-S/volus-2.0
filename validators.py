import re
import requests
from bs4 import BeautifulSoup
from string import digits, punctuation


user_agents_url = 'http://www.useragentstring.com/pages/useragentstring.php'


def get_bad_user_agents():
    # r = requests.get(user_agents_url)
    # if r.ok:
    #     soup = BeautifulSoup(r.text, 'html.parser')
    #     user_agents = [a.text for a in soup.find_all('a', class_='unterMenuName')]
    #     return user_agents

    return []


primitive_pwds = [
    'qwerty', 'Qwerty', 'password123', 'my_password', 'Admin123', 'admin'
]

phone_patterns = [r'^[\d]{11}$', r'^[\d]{6}$']

email_pattern = r'[A-Za-z0-9_.!#$%&-]{2,100}@.+'

not_in_name = digits + punctuation


class Validator:

    def __init__(self):
        pass

    def v_email(self, email):
        return re.match(email_pattern, email)

    def v_phone(self, phone):
        return re.match(phone_patterns[0], phone) or re.match(phone_patterns[1], phone)

    def v_pwd(self, pwd):
        for a in primitive_pwds:
            if a in pwd:
                return False
        return True

    def v_iin(self, iin):
        return iin.isdigit() and len(iin) == 12
