import re
from json import loads
from json.decoder import JSONDecodeError
from os.path import join
from logging import INFO, DEBUG, WARNING, ERROR, FATAL
from pdb import set_trace
from sys import exit, stdout
from subprocess import run

import requests
from bs4 import BeautifulSoup as bs, element

from utils import mkdir, rate_limit_sleep, log, clean_text
from config import Config


class IliasCrawler:
    def __init__(self):# {{{
        log(INFO, 'Instantiating ...')
        self.session = requests.Session()
        self.unknown_files = 0
        self.config = Config()

        try:
            log(DEBUG, 'Reading config file')
            with open('.ilias_crawler_config') as config_file:
                # This will override values from the default config
                self.config.update(loads(config_file.read()))
        except FileNotFoundError:
            log(WARNING,
                'It seems like the config file is missing! '
                'Will use the defaults.')
        except PermissionError:
            log(FATAL,
                'Failed to read config file, check permissions! Aborting')
            exit(5)
        except JSONDecodeError:
            log(FATAL,
                'Failed to parse config file! Aborting')
            exit(4)

    def __del__(self):
        try:
            self.session.close()
        except Exception as ex:
            # log(ERROR, ex)
            pass# }}}

    def start(self):# {{{
        self.login()
        log(INFO, 'Starting crawler')
        self.crawl(self.config.home_url)# }}}

    def login(self):# {{{
        try:
            with open('.iliassecret') as cred_file:
                username, password = cred_file.readlines()
        except Exception as ex:
            log(WARNING,
                f'Couldn\'t read credentials file at ./.iliassecret: {ex}')
            username = input('Please enter a username: ')
            from getpass import getpass
            password = getpass('Please enter a password: ')

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        response = self.session.post(
            self.config.login_url,
            data={
                'username': username.strip(),
                'password': password.strip(),
                'cmd[doStandardAuthentication]': 'Anmelden'},
            headers=headers)

        if 'Abmelden' not in response.text:
            log(FATAL,
                'Login failed! Please check the correctnes of the Login Data.')
            exit(1)
        log(INFO, 'Login successful')# }}}

    def crawl(self, ilias_link, parent_path=''):# {{{
        '''This method crawls an ilias link for different subsections and
        invoke the corrensponding subroutines.'''
        # TODO can there be courses inside of courses?
        # TODO use something link a type?
        # if not membership_links:
        #     log(ERROR, 'You don\'t seem to have subscribed to any courses.')
        #     exit(2)
        if isinstance(ilias_link, str):
            log(INFO, 'Crawling home')
            name = self.config.save_path
            ilias_link = {'href': ilias_link}
        else:
            name = ilias_link.contents[0]
            log(INFO, f'Crawling {name}')

        ilias_link['href'] = self.fix_url(ilias_link['href'])

        response = self.session.get(ilias_link['href'])
        soup = bs(response.text, 'html.parser')
        # TODO error check

        links = soup.findAll('a', attrs={'class': 'il_ContainerItemTitle'})
        if not links:
            log(DEBUG,
                f'Link {ilias_link["href"]} does not contain any items.')
            return

        path = join(parent_path, clean_text(name))
        mkdir(path)

        for link in links:
            if '_fold_' in link['href'] or '_crs_' in link['href']:
                # XXX can we safely assume the link name is the name of the
                # course?
                self.crawl(link, path)

            elif 'cmd=infoScreen' in link['href']:
                self.crawl(link, path)

            elif '_grp_' in link['href']:
                log(WARNING, 'Groups are not supported yet.')

            elif '_frm_' in link['href']:
                log(WARNING, 'Forums are not supported yet.')

            elif '_file_' in link['href']:
                if not self.config.download_files:
                    continue
                self.download_file(link, path)

            elif '_exc_' in link['href']:
                # TODO maybe download more files/ not only links with "Download"
                # maybe also save the text
                # TODO download handed in assignments
                self.handle_exercise(link, path)

            elif 'cmd=calldirectlink' in link['href']:
                log(DEBUG, 'External link, skipping')
                continue

            elif 'ilObjPluginDispatchGUI' in link['href']:
                if not self.config.download_opencast:
                    log(DEBUG, 'Will skip downloading opencast videos')
                    return
                self.handle_opencast(link, path)

            else:
                log(ERROR,
                    f'Unknown entity: {link["href"]}')
                self.unknown_files += 1# }}}

    def handle_opencast(self, ilias_link, parent_path):
        ilias_link['href'] = self.fix_url(ilias_link['href'])

        response = self.session.get(ilias_link['href'])
        soup = bs(response.text, 'html.parser')
        # TODO error check

        path = join(parent_path, clean_text(ilias_link.contents[0]))
        mkdir(path)

        object_links = soup.find_all('a', href=re.compile('showEpisode'))

        if len(object_links) < 1:
            log(INFO, 'no Elements found')
            return

        for object_link in object_links:
            # Only use links that only contain text so the preview image links
            # are ignored! (check if only one child in <a> tag?)
            object_name = object_link.contents[0]
            if isinstance(object_name, element.Tag):
                log(DEBUG, 'Skipping link')
                continue

            log(INFO, object_name)
            object_href = object_link['href']

            if 'ilias_xmh_2778520/d223059c-c82e-49ce-bdc3-886ab1cf5774' not in object_href:
                log(DEBUG, 'skipping vid')
                continue

            object_path = join(path, object_name)
            mkdir(object_path)

            object_id = re.findall('&id=(.+?)&', object_href)[0]
            object_metadata_url = self.config.metadata_url + object_id
            response = self.session.get(object_metadata_url)

            object_track_list = response.json()['search-results']['result'][
                    'mediapackage']['media']['track']

            track_path_list = []
            for track in object_track_list:
                track_url = track['url']

                track_extension = re.findall(r'\.(\w+)\?token', track_url)[0]
                file_name = f'{track["id"]}.{track_extension}'

                track_path_list.append(join(object_path, file_name))
                self.download_file(track_url, object_path, file_name)

            if len(track_path_list) > 1 and self.config.opencast_merge_videos:
                log(INFO,
                    'Merging videos with ffmpeg, '
                    'this might take a while')
                arguments = ['ffmpeg', '-hide_banner', '-loglevel', 'warning']

                for video in track_path_list:
                    arguments.extend(['-i', video])

                arguments.extend([
                    '-filter_complex',
                    'hstack',
                    join(object_path, 'merged.mp4'),
                    '-y'])

                # TODO add error handling
                run(arguments, check=True)

    def download_file(self, link, parent_path, file_name=None):# {{{
        if isinstance(link, str):
            url = link
        else:
            url = link['href']
        url = self.fix_url(url)
        response = self.session.get(url, stream=True)
        total = response.headers.get('content-length')

        if file_name is None:
            disposition = response.headers['content-disposition']
            file_name = re.findall('filename=\"(.+?)\"', disposition)[0]
            if not file_name:
                log(ERROR,
                    f'Could not get filename for item {url} in {parent_path}')
                file_name = 'unknown'
        log(INFO, file_name)

        file_path = join(parent_path, file_name)

        # Inspired by
        # https://sumit-ghosh.com/articles/python-download-progress-bar/
        # TODO add try catch
        with open(file_path, 'wb') as out_file:
            if total is None:
                out_file.write(response.content)
                return

            downloaded = 0
            total = int(total)
            for data in response.iter_content(
                    chunk_size=max(int(total/1000), 1024*1024)):
                downloaded += len(data)
                out_file.write(data)
                done = int(50*downloaded/total)
                stdout.write(
                    f'\r[{"=" * done}{" " * (50-done)}] {downloaded}/{total}')
                stdout.flush()
        stdout.write('\n')

        rate_limit_sleep()# }}}

    def fix_url(self, url):# {{{
        # TODO improve this
        if url.startswith('ilias.php'):
            log(DEBUG, f'Fixing url {url}')
            return f'{self.config.ilias_url}/{url}'
        return url# }}}

    def handle_exercise(self, link, parent_path):# {{{
        title = clean_text(link.contents[0])
        log(INFO, f'Descending to exercise {title}')

        if not self.config.download_files:
            log(INFO, 'Downloading of files disabled in the config. Skipping')
            return

        response = self.session.get(link['href'])
        soup = bs(response.text, 'html.parser')

        # Only get links with the text 'Download'
        assignment_links = [x for x in filter(
            lambda x: (
                len(x.contents) > 0 and x.contents[0] == 'Download'),
            soup.find_all('a'))]

        # Nothing to do if there are no links
        if len(assignment_links) < 1:
            log(DEBUG, 'No download links found in assignment')
            return

        # TODO should we create the directory even if there are no files?
        path = join(parent_path, title)
        mkdir(path)

        log(DEBUG, f'Found {len(assignment_links)} download link(s)')

        # Download all files from the assignments page
        for assignment_link in assignment_links:
            self.download_file(assignment_link, path)# }}}


def crawler(session, url, path, create_course_folder=False, indent=0):
    if 'ilMediaCastHandler' in link['href']:
        log(ERROR, 'TODO')
        if download_mediacast:
            overview_page_url = f'{ILIAS_URL}/{link["href"]}'

            response = session.get(overview_page_url)

            soup = bs4.BeautifulSoup(response.text, 'html.parser')

            download_links = soup.findAll('a', text='Download')

            rate_limit_sleep()

            if len(download_links) > 0:
                download_link = download_links[0]
                meta_data = download_link.nextSibling.strip()

                response = session.head(
                    f'{ILIAS_URL}/{download_link["href"]}')

                disposition = response.headers['content-disposition']
                file_name = re.findall(
                    'filename=\"(.+?)\"', disposition)[0]

                log(INFO, f'{file_name} {meta_data}', indent + 1)

                log(INFO, 'Downloading Media... ', indent+2)

                response = session.get(
                    '{ILIAS_URL}/{download_link["href"]}')

                disposition = response.headers['content-disposition']
                file_name = re.findall(
                    'filename=\"(.+?)\"', disposition)[0]

                file_path = join(path, file_name)

                with open(file_path, 'wb') as file:
                    file.write(response.content)

                log(INFO, 'done')

                rate_limit_sleep()

            else:
                log(ERROR,
                    'Mediacast Element without Download link found',
                    indent + 2)
                log(ERROR, f'URL: {overview_page_url}', indent + 2)

    elif 'ilobjtestgui' in link['href']:
        test_title = title
        log(INFO, test_title, indent + 1)
        log(WARNING, 'ignoring Test (No way to store as file)', indent + 2)

    elif 'ilHTLMPresentationGUI' in link['href']:
        html_title = title
        log(INFO, html_title, indent + 1)
        log(WARNING,
            'ignoring HTML content (No way to store as file)', indent + 2)

    elif 'ilLinkResourceHandlerGUI' in link['href']:
        link_title = title
        log(INFO, link_title, indent + 1)
        log(WARNING,
            'ignoring Link content (No way to store as file)', indent + 2)

    elif '_xlvo_' in link['href']:
        vote_title = title
        log(INFO, vote_title, indent + 1)
        log(WARNING,
            'ignoring Vote (No way to store as file)', indent + 2)


if __name__ == '__main__':
    # TODO add cmd line arguments

    my_crawler = IliasCrawler()
    my_crawler.start()

    if my_crawler.unknown_files > 0:
        log(WARNING,
            'There were some unknown files that couldn\'t be downloaded.')
        log(WARNING,
            f'A total of {str(my_crawler.unknown_files)} file(s) '
            'were skipped, for more information please consult the logs.')

    log(INFO, 'Finished downloading.')
    log(INFO, 'Shutting down ...')

    # with requests.Session() as session:
    #     if '_crs_' not in BASE_URL:
    #         log(WARNING,
    #             'INPUT URL DOES NOT APPEAR TO BE A COURSE, SUPPORT NOT TESTED')
