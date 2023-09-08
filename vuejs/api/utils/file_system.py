"""
Anything that directly works/interacts with the file system
"""
import json
import os
from time import strftime, localtime, time, sleep

def log_list(logs):
    print(logs)
    base_path = ""  # cfg.arm_config['LOGPATH']
    files = get_info(base_path)
    return {'success': True, 'files': files}

def get_info(directory):
    """
    Used to read stats from files
    -Used for view logs page
    :param directory:
    :return: list containing a list with each files stats
    """
    file_list = []
    for i in os.listdir(directory):
        if os.path.isfile(os.path.join(directory, i)):
            file_stats = os.stat(os.path.join(directory, i))
            file_size = os.path.getsize(os.path.join(directory, i))
            file_size = round((file_size / 1024), 1)
            file_size = f"{file_size :,.1f}"
            create_time = strftime(cfg.arm_config['DATE_FORMAT'], localtime(file_stats.st_ctime))
            access_time = strftime(cfg.arm_config['DATE_FORMAT'], localtime(file_stats.st_atime))
            # [file,most_recent_access,created, file_size]
            file_list.append([i, access_time, create_time, file_size])
    return file_list


def generate_comments():
    """
    load comments.json and use it for settings page
    allows us to easily add more settings later
    :return: json
    """
    comments_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "comments.json")
    try:
        with open(comments_file, "r") as comments_read_file:
            try:
                comments = json.load(comments_read_file)
            except Exception as error:
                print(f"Error with comments file. {error}")
                comments = "{'error':'" + str(error) + "'}"
    except FileNotFoundError:
        comments = "{'error':'File not found'}"
    return comments