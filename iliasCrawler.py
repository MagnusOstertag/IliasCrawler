import requests
import bs4
import os
import re
import time
import json
import subprocess


username = "test"
password = "test"


print("BITTE KEINE HERUNTERGELADENEN DATEIEN WEITERGEBEN!")
print("Dieses Programm ist nur zum Herunterladen von Dateien zum Offline lernen gedacht")
print("Das Copyright der Ersteller der Inhalte gilt trotzdem!")
print("")
print("Gebe J ein wenn du einverstanden bist:")
userConsent = input(">>> ")
if userConsent.lower() not in "yj":
    print("Dann darfst du das Programm leider nicht benutzen.")
    exit()
print("Vielen Dank.")

if username == "test" or password == "test":
    print("Please change login info in iliasCrawler.py")
    exit()


baseUrl = "https://ilias3.uni-stuttgart.de/goto_Uni_Stuttgart_crs_2088402.html"

enableColors = False
useColorama = False
loadFiles = True
loadMediacast = True
loadOpencast = True
overrideLoginCheck = False
stitchSideBySideVideos = True
antiDosRateLimit = False


logStr = ""

unknownFilesFound = 0

if useColorama:
    import colorama
    colorama.init()

def textCol(col):
    global enableColors
    escCodes = {
        "0":   "",
        "rst": "\033[0m",       # reset all (colors and brightness)
        "brt": "\033[1m",       # bright
        "dim": "\033[2m",       # dim (looks same as normal brightness)
        "nrm": "\033[22m",      # normal brightness

        # FOREGROUND:
        "fblck": "\033[30m",      # black
        "fr": "\033[31m",      # red
        "fg": "\033[32m",      # green
        "fy": "\033[33m",      # yellow
        "fb": "\033[34m",      # blue
        "fm": "\033[35m",      # magenta
        "fc": "\033[36m",      # cyan
        "fw": "\033[37m",      # white
        "frst": "\033[39m",      # reset

        # BACKGROUND
        "bblck": "\033[40m",      # black
        "br": "\033[41m",      # red
        "bg": "\033[42m",      # green
        "by": "\033[43m",      # yellow
        "bb": "\033[44m",      # blue
        "bm": "\033[45m",      # magenta
        "bc": "\033[46m",      # cyan
        "bw": "\033[47m",      # white
        "brst": "\033[49m",      # reset

        # clear the screen
        "clsc": "\033[mode J",    # clear the screen

        # clear the line
        "clln": "\033[mode K"    # clear the line
    }
    if enableColors:
        return escCodes[col]
    else:
        return ""

def mkdir(path):
    try:
        os.mkdir(path)
    except FileExistsError:
        pass


def printIndented(str, indent, end="\n", col="0"):
    global logStr
    print(textCol(col) + "    " * indent + str + textCol("rst"), end=end, flush=True)
    logStr += "    " * indent + str + end

def rateLimitSleep():
    global antiDosRateLimit
    if antiDosRateLimit:
        time.sleep(3)

def crawlDir(session, url, path, createBaseFolder = False, indent=0):
    global unknownFilesFound
    global rateLimitSleep

    #printIndented("Crawling " + path + " at " + url, indent)

    r = s.request("POST", url)

    soup = bs4.BeautifulSoup(r.text, 'html.parser')

    if createBaseFolder:
        currentTitle = soup.find(id="il_mhead_t_focus").contents[0]

        printIndented(currentTitle, indent)

        mkdir(path + "/" + currentTitle)

        path += "/" + currentTitle

    links = soup.findAll('a',attrs={'class':'il_ContainerItemTitle'})

    rateLimitSleep()

    for link in links:
        if "_fold_" in link["href"]:
            folderTitle = link.contents[0].strip().replace("/", "-").replace("?", "")
            printIndented(folderTitle, indent+1)
            folderPath = path + "/" + folderTitle
            mkdir(folderPath)
            crawlDir(session, link["href"], folderPath, indent=indent+1)    # recursively crawl the next Folder

        elif "_file_" in link["href"]:
            fileTitle = link.contents[0].strip().replace("/", "-").replace("?", "")
            printIndented(fileTitle, indent+1, col="fr")

            if loadFiles:
                r = s.request("GET", link["href"])

                d = r.headers['content-disposition']
                fileName = re.findall("filename=\"(.+?)\"", d)[0]

                printIndented(fileName, indent+2, col="fr")

                filePath = path + "/" + fileName

                with open(filePath, 'wb') as f:
                    f.write(r.content)

                rateLimitSleep()

        elif "ilMediaCastHandler" in link["href"]:
            mediacastTitle = link.contents[0].strip().replace("/", "-").replace("?", "")
            printIndented(mediacastTitle, indent+1)

            if loadMediacast:

                overviewPageUrl = "https://ilias3.uni-stuttgart.de/" + link["href"]

                r = s.request("GET", overviewPageUrl)

                soup = bs4.BeautifulSoup(r.text, 'html.parser')

                downloadLinks = soup.findAll('a',text="Download")

                rateLimitSleep()

                if len(downloadLinks) > 0:
                    downloadLink = downloadLinks[0]
                    metaData = downloadLink.nextSibling.strip()

                    r = s.head("https://ilias3.uni-stuttgart.de/" + downloadLink["href"])

                    d = r.headers['content-disposition']
                    fileName = re.findall("filename=\"(.+?)\"", d)[0]

                    printIndented(fileName + " " + metaData, indent + 1)

                    printIndented("Downloading Media... ", indent+2, end="")

                    r = s.request("GET", "https://ilias3.uni-stuttgart.de/" + downloadLink["href"])

                    d = r.headers['content-disposition']
                    fileName = re.findall("filename=\"(.+?)\"", d)[0]

                    filePath = path + "/" + fileName

                    with open(filePath, 'wb') as f:
                        f.write(r.content)

                    printIndented("done", indent=0)

                    rateLimitSleep()

                else:
                    printIndented("ERROR: Mediacast Element without Download link found", indent+2)
                    printIndented("Error URL: " + overviewPageUrl, indent+2)

        elif "ilObjPluginDispatchGUI" in link["href"]:
            opencastTitle = link.contents[0].strip().replace("/", "-").replace("?", "")
            printIndented(opencastTitle, indent+1)

            mkdir(path + "/" + opencastTitle)

            if loadOpencast:

                overviewPageUrl = "https://ilias3.uni-stuttgart.de/" + link["href"]

                r = s.request("GET", overviewPageUrl)

                soup = bs4.BeautifulSoup(r.text, 'html.parser')

                videoLinks = soup.find_all("video")

                for link in videoLinks:
                    link = link.findChildren("source")[0]
                    print(link)
                    r = s.request("GET", "https://ilias3.uni-stuttgart.de" + link["src"].lstrip("."))

                    fileName = re.findall("\/([-.\w]+?)\?", link["src"])[0]

                    filePath = path + "/" + opencastTitle + "/" + fileName

                    with open(filePath, 'wb') as f:
                        f.write(r.content)

                objectLinks = soup.find_all("a", href=re.compile("showEpisode"))

                if len(objectLinks) < 1:
                    pass
                    #print("no Elements found")

                for link in objectLinks:    # Experimental: Only use links that only contain text so the preview image links are ignored! (check if only one child in <a> tag?)
                    objectName = link.contents[0]
                    if type(objectName) != bs4.element.Tag:
                        #print("using link")
                        objectLink = link["href"]
                        mkdir(path + "/" + opencastTitle + "/" + objectName)
                        printIndented(objectName, indent+2)

                        #objectPageUrl = "https://ilias3.uni-stuttgart.de/" + link["href"]

                        #r = s.request("GET", "https://ilias3.uni-stuttgart.de/" + objectLink)

                        objectId = re.findall("&id=(.+?)&", objectLink)[0]

                        objectMetadataUrl = "https://ilias3.uni-stuttgart.de/Customizing/global/plugins/Services/Repository/RepositoryObject/Opencast/api.php/episode.json?id=" + objectId

                        r = s.request("GET", objectMetadataUrl)

                        #print(r.text)

                        objectMetadata = r.text

                        objectMetadataParsed = json.loads(r.text)

                        objectTrackList = objectMetadataParsed["search-results"]["result"]["mediapackage"]["media"]["track"]

                        trackPathList = []

                        for track in objectTrackList:
                            trackUrl = track["url"]

                            trackExtension = re.findall("\.(\w+?)\?", trackUrl)[0]

                            printIndented(track["id"] + "." + trackExtension, indent+3)
                            #printIndented(trackUrl, indent+3)

                            filePath = path + "/" + opencastTitle + "/" + objectName + "/" + track["id"] + "." + trackExtension

                            trackPathList.append(filePath)

                            printIndented("Loading Media...", indent+4, end="")
                            r = s.request("GET", trackUrl)

                            with open(filePath, 'wb') as f:
                                f.write(r.content)

                            printIndented("done", indent+0)

                        trackFolderPath = path + "/" + opencastTitle + "/" + objectName

                        if len(trackPathList) > 1:
                            printIndented("Stacking videos with ffmpeg...", indent+4, end="")

                            callList = ["ffmpeg\\bin\\ffmpeg.exe", "-hide_banner", "-loglevel", "warning"]

                            for trackPath in trackPathList:
                                callList.extend(["-i", trackPath])

                            callList.extend(["-filter_complex","hstack=inputs=" + str(len(trackPathList)),trackFolderPath+"/stacked.mp4","-y"])

                            subprocess.run(callList)

                            printIndented("done", 0)
                        else:
                            printIndented("no ffmpeg stacking needed, only 1 video available", indent+4)
                    else:
                        pass
                        #print("skipped link")

        elif "ilobjtestgui" in link["href"]:
            testTitle = link.contents[0].strip().replace("/", "-").replace("?", "")
            printIndented(testTitle, indent+1)
            printIndented("WARNING: ignoring Test (No way to store as file)", indent+2, col="fm")

        elif "ilHTLMPresentationGUI" in link["href"]:
            htmlTitle = link.contents[0].strip().replace("/", "-").replace("?", "")
            printIndented(htmlTitle, indent+1)
            printIndented("WARNING: ignoring HTML content (No way to store as file)", indent+2, col="fm")

        elif "ilLinkResourceHandlerGUI" in link["href"]:
            linkTitle = link.contents[0].strip().replace("/", "-").replace("?", "")
            printIndented(linkTitle, indent+1)
            printIndented("WARNING: ignoring Link content (No way to store as file)", indent+2, col="fm")

        elif "_xlvo_" in link["href"]:
            voteTitle = link.contents[0].strip().replace("/", "-").replace("?", "")
            printIndented(voteTitle, indent+1)
            printIndented("WARNING: ignoring Vote (No way to store as file)", indent+2, col="fm")

        elif "_frm_" in link["href"]:
            forumTitle = link.contents[0].strip().replace("/", "-").replace("?", "")
            printIndented(forumTitle, indent+1)
            printIndented("WARNING: ignoring Forum (No way to store as file)", indent+2, col="fm")

        else:
            unknownFilesFound += 1
            printIndented("Unknown Element", indent+1, col="fr")
            printIndented("ERROR: Unknown Element found!", indent+2, col="fm")
            printIndented(link["href"], indent+2)



printIndented("starting", indent=0)

with requests.Session() as s:

    if not "_crs_" in baseUrl:
        printIndented("INPUT URL DOES NOT APPEAR TO BE A COURSE, SUPPORT NOT TESTED", 0, col="fr")

    headers = {'Content-Type':'application/x-www-form-urlencoded'}

    r = s.request("POST", "https://ilias3.uni-stuttgart.de/ilias.php?lang=de&client_id=Uni_Stuttgart&cmd=post&cmdClass=ilstartupgui&cmdNode=zq&baseClass=ilStartUpGUI&rtoken=", data="username=" + username + "&password=" + password + "&cmd%5BdoStandardAuthentication%5D=Anmelden", headers=headers)

    if "Abmelden" in r.text or overrideLoginCheck:
        printIndented("logged in", indent=0)

        mkdir("temp")

        printIndented("starting crawling\n", indent=0)
        crawlDir(s, baseUrl, "temp", createBaseFolder = True)
        printIndented("\ndone", indent=0)
        printIndented("Unknown Files: " + str(unknownFilesFound), indent=0)
        print("Writing Lofile...", end="", flush=True)
        with open("log.txt", 'w') as f:
            f.write(logStr)
        print("done")
    else:
        printIndented("login failed... check Login Data or try skipping login check by using overrideLoginCheck", 0, col="fr")
