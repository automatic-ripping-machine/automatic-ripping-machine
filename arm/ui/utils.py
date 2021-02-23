import os
from time import strftime, localtime
import urllib
import json
import re
# import logging
# import omdb
from arm.config.config import cfg


def get_info(directory):
    file_list = []
    for i in os.listdir(directory):
        if os.path.isfile(os.path.join(directory, i)):
            a = os.stat(os.path.join(directory, i))
            fsize = os.path.getsize(os.path.join(directory, i))
            fsize = round((fsize / 1024), 1)
            fsize = "{0:,.1f}".format(fsize)
            create_time = strftime('%Y-%m-%d %H:%M:%S', localtime(a.st_ctime))
            access_time = strftime('%Y-%m-%d %H:%M:%S', localtime(a.st_atime))
            file_list.append([i, access_time, create_time, fsize])  # [file,most_recent_access,created]
    return file_list


def clean_for_filename(string):
    """ Cleans up string for use in filename """
    string = re.sub('\[(.*?)\]', '', string)  # noqa: W605
    string = re.sub('\s+', ' ', string)  # noqa: W605
    string = string.replace(' : ', ' - ')
    string = string.replace(':', '-')
    string = string.replace('&', 'and')
    string = string.replace("\\", " - ")
    string = string.strip()
    # return re.sub('[^\w\-_\.\(\) ]', '', string)
    return string


def getsize(path):
    st = os.statvfs(path)
    free = (st.f_bavail * st.f_frsize)
    freegb = free/1073741824
    return freegb


def convert_log(logfile):
    logpath = cfg['LOGPATH']
    fullpath = os.path.join(logpath, logfile)

    output_log = os.path.join('static/tmp/', logfile)

    with open(fullpath) as infile, open(output_log, 'w') as outfile:
        txt = infile.read()
        txt = txt.replace('\n', '\r\n')
        outfile.write(txt)
    return(output_log)


def call_omdb_api(title=None, year=None, imdbID=None, plot="short"):
    """ Queries OMDbapi.org for title information and parses if it's a movie
        or a tv series """
    omdb_api_key = cfg['OMDB_API_KEY']

    if imdbID:
        strurl = "http://www.omdbapi.com/?i={1}&plot={2}&r=json&apikey={0}".format(omdb_api_key, imdbID, plot)
    elif title:
        # try:
        title = urllib.parse.quote(title)
        year = urllib.parse.quote(year)
        strurl = "http://www.omdbapi.com/?s={1}&y={2}&plot={3}&r=json&apikey={0}".format(omdb_api_key, title, year, plot)
    else:
        print("no params")
        return(None)

    # strurl = urllib.parse.quote(strurl)
    # logging.info("OMDB string query"+str(strurl))
    print(strurl)
    title_info_json = urllib.request.urlopen(strurl).read()
    title_info = json.loads(title_info_json.decode())
    print(title_info)
    # logging.info("Response from Title Info command"+str(title_info))
    # d = {'year': '1977'}
    # dvd_info = omdb.get(title=title, year=year)
    print("call was successful")
    return(title_info)
    # except Exception:
    #     print("call failed")
    #     return(None)
