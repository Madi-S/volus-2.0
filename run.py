from app import app
from logger import logger


def start_ngrok():
    logger.debug('Starting with ngrok')
    from pyngrok import ngrok

    url = ngrok.connect(5000)
    logger.debug('Tunnel ngrok URL %s', url)


if __name__ == '__main__':
    logger.debug('Starting Volus')

    if app.config['START_NGROK']:
        start_ngrok()

    logger.debug('Web app is running')
    app.run()

    # logger.debug('Volus Web Application was started')

    # ngrok http 5000
