from logging import INFO, DEBUG, WARNING, ERROR, FATAL
from json import loads
from json.decoder import JSONDecodeError
from sys import exit as exit_app

class Config:
    def __init__(self, log):
        self._config = {
            'skip_courses': [],
            'download_files': True,
            'download_mediacast': True,
            'download_opencast': True,
            'download_videos': True,
            'warn_on_lm': True,
            'opencast_merge_videos': False,
            'ILIAS_URL': 'https://ilias3.uni-stuttgart.de',
            'USER_HOME': (
                'ilias.php?baseClass=ilPersonalDesktopGUI&'
                'cmd=jumpToMemberships'),
            'LOGIN_URL': (
                'ilias.php?lang=de&client_id=Uni_Stuttgart&cmd=post'
                '&cmdClass=ilstartupgui&cmdNode=zq'
                '&baseClass=ilStartUpGUI&rtoken='),
            'METADATA_URL': (
                'Customizing/global/plugins/Services/Repository/'
                'RepositoryObject/Opencast/api.php/episode.json?id='),
            'save_path': 'ilias_files',
        }
        try:
            log(DEBUG, 'Reading config file')
            with open('.ilias_crawler_config') as config_file:
                # This will override values from the default config
                self._config.update(loads(config_file.read()))
        except FileNotFoundError:
            log(WARNING,
                'It seems like the config file is missing! '
                'Will use the defaults.')
        except PermissionError:
            log(FATAL,
                'Failed to read config file, check permissions! Aborting')
            exit_app(5)
        except JSONDecodeError:
            log(FATAL,
                'Failed to parse config file! Aborting')
            exit_app(4)

    @property
    def skip_courses(self):
        return self._config['skip_courses']

    @property
    def download_files(self):
        return self._config['download_files']

    @property
    def download_mediacast(self):
        return self._config['download_mediacast']

    @property
    def download_opencast(self):
        return self._config['download_opencast']

    @property
    def download_videos(self):
        return self._config['download_videos']

    @property
    def warn_on_lm(self):
        return self._config['warn_on_lm']

    @property
    def opencast_merge_videos(self):
        return self._config['opencast_merge_videos']

    @property
    def ilias_url(self):
        return self._config['ILIAS_URL']

    @property
    def home_url(self):
        return f'{self.ilias_url}/{self._config["USER_HOME"]}'

    @property
    def metadata_url(self):
        return f'{self.ilias_url}/{self._config["METADATA_URL"]}'

    @property
    def login_url(self):
        return f'{self.ilias_url}/{self._config["LOGIN_URL"]}'

    @property
    def save_path(self):
        return self._config['save_path']
