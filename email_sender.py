import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from os import environ


PASSWORD = environ['SMTP_PASSWORD']
FROM_EMAIL = environ['SMTP_EMAIL']
MAILHOST = 'smtp.gmail.com'
MAILPORT = 465


def send_email(subject, to_email, body=None, html=None):
    assert (body or html)

    with smtplib.SMTP_SSL(MAILHOST, MAILPORT) as smtp:
        smtp.login(FROM_EMAIL, PASSWORD)

        msg = f'Subject: {subject}\n\n{body}'.encode('utf-8')

        smtp.sendmail(FROM_EMAIL, to_email, msg)
