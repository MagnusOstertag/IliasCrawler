class Config:
    def __init__(self):
        self._config = {
            'download_files': True,
            'download_mediacast': True,
            'download_opencast': True,
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

    def update(self, new_config):
        self._config.update(new_config)

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
