import re
from json import loads
from json.decoder import JSONDecodeError
from os.path import join
from logging import INFO, DEBUG, WARNING, ERROR, FATAL
from pdb import set_trace
from sys import exit

import requests
from bs4 import BeautifulSoup as bs

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

    def crawl(self, ilias_link, parent_path=''):
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
            # set_trace()
            if '_fold_' in link['href']:
                self.crawl(link, path)

            elif '_grp_' in link['href']:
                log(WARNING, 'Groups are not supported yet.')

            elif '_frm_' in link['href']:
                log(WARNING,
                    'Forums are not supported yet.')

            elif '_crs_' in link['href']:
                # XXX can we safely assume the link name is the name of the
                # course?
                self.crawl(link, path)

            elif '_file_' in link['href']:
                if not self.config.download_files:
                    continue
                self.download_file(link, path)

            elif '_exc_' in link['href']:
                # TODO maybe download more files/ not only links with "Download"
                # maybe also save the text
                # TODO download handed in assignments
                self.handle_exercise(link)

            else:
                log(ERROR,
                    f'Unknown entity: {link["href"]}')
                self.unknown_files += 1

    def download_file(self, link, parent_path):# {{{
        response = self.session.get(link['href'])

        disposition = response.headers['content-disposition']
        file_name = re.findall('filename=\"(.+?)\"', disposition)[0]
        if not file_name:
            log(ERROR,
                'Could not get filename for item '
                f'{link["href"]} in {parent_path}')
            file_name = 'unknown'

        log(INFO, file_name)

        # TODO add try catch
        with open(join(parent_path, file_name), 'wb') as file:
            file.write(response.content)

        rate_limit_sleep()# }}}

    def handle_exercise(self, link, parent_path):
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
            self.download_file(assignment_link, path)


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

    elif 'ilObjPluginDispatchGUI' in link['href']:
        opencast_title = title
        log(INFO, opencast_title, indent + 1)
        mkdir(join(path, opencast_title))

        if not download_opencast:
            continue

        response = session.get(f'{ILIAS_URL}/{link["href"]}')
        soup = bs4.BeautifulSoup(response.text, 'html.parser')
        # video_links = soup.find_all('video')

        # for link in video_links:
        #     link = link.findChildren('source')[0]
        #     log(WARNING, 'todo')
        #     response = session.get(
        #         f'{ilias_url}/{link["src"].lstrip(".")}')
        #     file_name = re.findall('\/([-.\w]+?)\?', link['src'])[0]
        #     file_path = join(path, opencast_title, file_name)
        #     with open(file_path, 'wb') as f:
        #         f.write(response.content)
        #
        object_links = soup.find_all('a', href=re.compile('showEpisode'))

        if len(object_links) < 1:
            log(INFO, 'no Elements found')
            continue

        # Experimental: Only use links that only contain text so the
        # preview image links are ignored! (check if only one child in <a>
        # tag?)
        for object_link in object_links:
            object_name = object_link.contents[0]
            if isinstance(object_name, bs4.element.Tag):
                log(DEBUG, 'Skipping link')
                continue

            # crawlDir(
            #         session,
            #         f'{ilias_url}/{link["href"]}',
            #         path,
            #         indent=indent + 1)
            # continue

            object_href = object_link['href']
            mkdir(join(path, opencast_title, object_name))
            log(INFO, object_name, indent + 2)

            object_id = re.findall('&id=(.+?)&', object_href)[0]
            object_metadata_url = (
                f'{ILIAS_URL}/Customizing/global/plugins/Services/'
                'Repository/RepositoryObject/Opencast/api.php/'
                f'episode.json?id={object_id}')
            response = session.get(object_metadata_url)
            object_metadata_parsed = loads(response.text)
            object_track_list = object_metadata_parsed[
                'search-results'][
                    'result']['mediapackage']['media']['track']

            track_path_list = []

            for track in object_track_list:
                track_url = track['url']
                track_id = track['id']
                track_extension = re.findall('\.(\w+?)\?', track_url)[0]

                file_path = join(
                    path,
                    opencast_title,
                    object_name,
                    f'{track_id}.{track_extension}')

                track_path_list.append(file_path)

                log(INFO,
                    f'Downloading {track_id}.{track_extension} ...',
                    indent + 3)
                response = session.get(track_url)

                with open(file_path, 'wb') as file:
                    file.write(response.content)

            # trackFolderPath = join(path, opencast_title, object_name)

            if len(track_path_list) > 1:
                log(INFO, 'should be stacked')
                # log(INFO, 'Stacking videos with ffmpeg...', indent + 4)
            #
                # callList = [
                #         'ffmpeg\\bin\\ffmpeg.exe',
                #         '-hide_banner', '-loglevel', 'warning']
            #
            #     for trackPath in trackPathList:
            #         callList.extend(['-i', trackPath])
            #
                # callList.extend([
                #     '-filter_complex',
                #     'hstack=inputs=' + str(
                #         len(trackPathList)),
                #     trackFolderPath+'/stacked.mp4','-y'])
            #
            #     subprocess.run(callList)
            #
            #     log(INFO, 'done', 0)
            else:
                log(INFO,
                    'no ffmpeg stacking needed, only 1 video available',
                    indent + 4)

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
