#!/usr/bin/python3

import os
import logger
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


