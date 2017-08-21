#!/usr/bin/python3

import os
import logger
import requests
import argparse


from pushbullet import Pushbullet
import pyfttt as pyfttt
from config import cfg

# def entry():
#     """ Entry to program, parses arguments
#     This is just for testing..."""

    # parser = argparse.ArgumentParser(description='Send notifications')
    # parser.add_argument('-t', '--title', help='Title', required=True)
    # parser.add_argument('-b', '--body', help='Body', required=True)

    # return parser.parse_args()

def notify(title, body):
    # Send notificaions
    # title = title for notification
    # body = body of the notification

    if cfg['PB_KEY'] is not None:
        pb = Pushbullet(cfg['PB_KEY'])
        push = pb.push_note(title, body)
        # for key, value in push.items():
        #     print (key, value)

    if cfg['IFTTT_KEY'] is not None:
        
        event = cfg['IFTTT_EVENT']
        pyfttt.send_event(cfg['IFTTT_KEY'], event, title, body)


# args = entry()

# notify(args.title, args.body)