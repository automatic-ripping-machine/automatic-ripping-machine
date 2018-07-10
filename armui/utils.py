import os
from time import strftime, localtime
from armui.config import cfg


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