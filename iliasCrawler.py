import re
from json import loads
from os.path import join
from logging import INFO, DEBUG, WARNING, ERROR, FATAL
from pdb import set_trace
from sys import exit

import bs4
import requests

from utils import mkdir, rate_limit_sleep, log, clean_text

ILIAS_URL = 'https://ilias3.uni-stuttgart.de'

BASE_URL = f'{ILIAS_URL}/goto_Uni_Stuttgart_crs_2122525.html'  # theo1
BASE_URL = f'{ILIAS_URL}/goto_Uni_Stuttgart_crs_2091913.html'  # irtm

download_files = True
download_mediacast = True
download_opencast = True
overrideLoginCheck = False
stitchSideBySideVideos = True

unknown_files = 0


def crawler(session, url, path, create_course_folder=False, indent=0):
    global unknown_files
    log(DEBUG, f'Crawling {path}', indent)
    response = session.post(url)
    soup = bs4.BeautifulSoup(response.text, 'html.parser')

    if create_course_folder:
        current_course_title = soup.find(id='il_mhead_t_focus').contents[0]
        path = join(path, current_course_title)
        mkdir(path)

    links = soup.findAll('a', attrs={'class': 'il_ContainerItemTitle'})
    rate_limit_sleep()

    for link in links:
        title = clean_text(link.contents[0])
        log(INFO, title, indent + 1)

        if '_fold_' in link['href']:
            folder_path = join(path, title)
            mkdir(folder_path)
            crawler(session, link['href'], folder_path, indent=indent + 1)

        elif '_file_' in link['href']:
            if download_files:
                response = session.get(link['href'])

                disposition = response.headers['content-disposition']
                file_name = re.findall('filename=\"(.+?)\"', disposition)[0]

                log(INFO, file_name, indent + 2)

                with open(join(path, file_name), 'wb') as file:
                    file.write(response.content)

                rate_limit_sleep()

        elif 'ilMediaCastHandler' in link['href']:
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

        elif '_frm_' in link['href']:
            log(WARNING,
                'ignoring Forum (No way to store as file)', indent + 2)

        elif '_exc_' in link['href']:
            # TODO maybe download more files/ not only links with "Download"
            # maybe also save the text
            # TODO download handed in assignments
            if not download_files:
                continue

            response = session.get(link['href'])
            soup = bs4.BeautifulSoup(response.text, 'html.parser')

            # Only get links with the text 'Download'
            assignment_links = [x for x in filter(
                lambda x: len(x.contents) > 0 and x.contents[0] == 'Download',
                soup.find_all('a'))]

            # Nothing to do if there are no links
            if len(assignment_links) < 1:
                log(DEBUG, 'No download links found', indent + 1)
                continue

            mkdir(join(path, title))
            log(DEBUG,
                f'Found {len(assignment_links)} download link(s)', indent + 1)

            # Download all files from the assignments page
            for assignment_link in assignment_links:
                response = session.get(
                    f'{ILIAS_URL}/{assignment_link["href"]}')
                disposition = response.headers['content-disposition']
                file_name = re.findall('filename=\"(.+?)\"', disposition)[0]
                if not file_name:
                    log(ERROR,
                        'Couldn\'t get file name for'
                        f'{assignment_link["href"]}',
                        indent + 2)
                    continue

                log(INFO, file_name, indent + 2)

                file_path = join(path, title)
                mkdir(file_path)

                with open(join(file_path, file_name), 'wb') as file:
                    file.write(response.content)

                rate_limit_sleep()

        # elif '_lm_' in link['href']:

        else:
            log(ERROR, 'Unknown Element found!', indent + 2)
            log(ERROR, link['href'], indent + 2)
            unknown_files += 1


def login(session):
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
    response = session.post(
        f'{ILIAS_URL}/ilias.php?'
        'lang=de&client_id=Uni_Stuttgart&cmd=post&cmdClass=ilstartupgui'
        '&cmdNode=zq&baseClass=ilStartUpGUI&rtoken=',
        data={
            'username': username.strip(),
            'password': password.strip(),
            'cmd[doStandardAuthentication]': 'Anmelden'},
        headers=headers)
    if 'Abmelden' not in response.text:
        log(FATAL,
            'login failed... '
            'check Login Data or try skipping login check '
            'by using overrideLoginCheck')
        exit(1)
    log(INFO, 'Login successful')


if __name__ == '__main__':
    log(INFO, 'Starting')
    with requests.Session() as session:
        if '_crs_' not in BASE_URL:
            log(WARNING,
                'INPUT URL DOES NOT APPEAR TO BE A COURSE, SUPPORT NOT TESTED')

        login(session)

        # TODO make this configurable
        output_dir = 'temp'
        mkdir(output_dir)

        log(INFO, 'Starting crawler')
        crawler(session, BASE_URL, output_dir, create_course_folder=True)

        if unknown_files > 0:
            log(WARNING,
                'There were some unknown files that couldn\'t be downloaded.')
            log(WARNING,
                f'A total of {str(unknown_files)} file(s) were skipped, '
                'for more information please consult the logs.')
        log(INFO, f'Finished downloading {BASE_URL}.')
