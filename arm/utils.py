#!/usr/bin/python3

import os
import logging
import shutil
import requests
import argparse

from config import cfg


def notify(title, body):
    # Send notificaions
    # title = title for notification
    # body = body of the notification

    if cfg['PB_KEY']  != "":
        from pushbullet import Pushbullet
        pb = Pushbullet(cfg['PB_KEY'])
        push = pb.push_note(title, body)


    if cfg['IFTTT_KEY'] != "":
        import pyfttt as pyfttt        
        event = cfg['IFTTT_EVENT']
        pyfttt.send_event(cfg['IFTTT_KEY'], event, title, body)


    if cfg['PO_USER_KEY'] != "":
        from pushover import init, Client
        init(cfg['PO_APP_KEY'])
        Client(cfg['PO_USER_KEY']).send_message(body, title=title)

def scan_emby():
    """Trigger a media scan on Emby"""
    # log = logging.getLogger(__name__)

    logging.info("Sending Emby library scan request")
    url = "http://" + cfg['EMBY_SERVER'] + ":" + cfg['EMBY_PORT'] + "/Library/Refresh?api_key=" + cfg['EMBY_API_KEY']
    try:
        req = requests.post(url)
        if req.status_code > 299:
            req.raise_for_status()
        logging.info("Emby Library Scan request successful")
    except requests.exceptions.HTTPError:
        logging.error("Emby Library Scan request failed with status code: " + str(req.status_code))

def move_files(basepath, filename, hasnicetitle, videotitle, ismainfeature=False):
    """Move files into final media directory
    basepath = path to source directory
    filename = name of file to be moved
    hasnicetitle = hasnicetitle value
    ismainfeature = True/False"""

    logging.debug("Arguments: " + basepath + " : " + filename + " : " + str(hasnicetitle) + " : " + videotitle + " : " + str(ismainfeature))

    if hasnicetitle == "true":
        m_path = os.path.join(cfg['MEDIA_DIR'] + videotitle)

        if not os.path.exists(m_path):
            logging.info("Creating base title directory: " + m_path)
            os.makedirs(m_path)

        if ismainfeature is True:
            logging.info("Track is the Main Title.  Moving '" + filename + "' to " + m_path)

            try:
                shutil.move(os.path.join(basepath, filename), os.path.join(m_path, videotitle + "." + cfg['DEST_EXT']))
            except shutil.Error:
                logging.error("Unable to move '" + filename + "' to " + m_path)
        else:
            e_path = os.path.join(m_path, cfg['EXTRAS_SUB'])

            logging.info("Creating extras directory " + e_path)
            if not os.path.exists(e_path):
                os.makedirs(e_path)

            logging.info("Moving '" + filename + "' to " + e_path)

            try:
                shutil.move(os.path.join(basepath, filename), os.path.join(e_path, filename))
            except shutil.Error:
                logging.error("Unable to move '" + filename + "' to " + e_path)

    else:
        logging.info("hasnicetitle is false.  Not moving files.")

