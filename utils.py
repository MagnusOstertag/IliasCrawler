import os
import logging

from time import sleep
from platform import system

anti_dos_rate_limit = False

# logging{{{
enable_colors = True

# TODO verify if this works
if system() == 'Windows':
    import colorama
    colorama.init()

escape_codes = {
    logging.DEBUG: '\033[34m\033[49m',
    logging.INFO: '\033[32m\033[49m',
    logging.WARNING: '\033[33m\033[40m',
    logging.ERROR: '\033[31m\033[49m',
    logging.FATAL: '\033[30m\033[41m'
}

console_logger = logging.getLogger('IliasDownloader-console')
console_logger.setLevel(logging.DEBUG)
file_logger = logging.getLogger('IliasDownloader')
file_logger.setLevel(logging.DEBUG)

fh = logging.FileHandler('log.txt')
fh.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
# TODO make this variable
ch.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '{asctime} [{levelname:.4}] {message}',
    datefmt='%y-%m-%d %H:%M:%S',
    style='{')
fh.setFormatter(formatter)
ch.setFormatter(formatter)

file_logger.addHandler(fh)
console_logger.addHandler(ch)
# end logging}}}


def log(level, message, indents=0):
    '''Log a message. If indents is set to some number `n` other than 0, the
    message will be prepended with `n` times a `>` sign for better readability.
    :param level: Loglevel as specified in the logging module
    :param message: The message to be logged
    :param indents: If not 0, level of intentation
    '''
    message = f'{">"*indents}{" " if indents else ""}{message}'
    file_logger.log(level, message)
    if enable_colors:
        message = f'{escape_codes[level]}{message}\033[0m'
    console_logger.log(level, message)


def mkdir(path):
    '''A simple wrapper around os.mkdir that also logs if the directory was
    created.
    :param path: path to create
    '''
    try:
        os.mkdir(path)
        log(logging.DEBUG, f'Created dir {path}')
    except FileExistsError:
        pass


def rate_limit_sleep():
    '''Sleep for a while to avoid rate limiting'''
    # TODO make this configurable
    if anti_dos_rate_limit:
        sleep(1)


def clean_text(text):
    '''Cleans and returns a text for storing it to disk, i.e., removing illegal
    characters from filepaths
    :param text: the text to clean
    :returns: cleaned string
    '''
    return (
        text.strip()
        .replace('/', '-')
        .replace('!', '')
        .replace('?', ''))


def breadcrumb_matches(current_crumb, breadcrumbs):
    '''Ilias cuts off text of the breadcrumb if the strings are too long'''
    for breadcrumb in breadcrumbs:
        if not breadcrumb:
            continue
        # log(logging.DEBUG, f'breadcrumb is {breadcrumb}')
        if breadcrumb[-1] == '…':
            if current_crumb.startswith(breadcrumb[:-1]):
                return True
        elif breadcrumb == current_crumb:
            return True
    return False
