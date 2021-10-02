import logging


logger = logging.getLogger('volus')
logger.setLevel(logging.DEBUG)

s = logging.StreamHandler()
sf = logging.Formatter('%(levelname)s: %(message)s')
s.setLevel(logging.DEBUG)
s.setFormatter(sf)

w = logging.FileHandler('volus.log', mode='a', encoding='utf-8')
wf = logging.Formatter(
    '%(levelname)s - %(asctime)s - %(filename)s - Line #%(lineno)d: %(message)s')
w.setLevel(logging.DEBUG)
w.setFormatter(wf)

logger.addHandler(s)
logger.addHandler(w)
