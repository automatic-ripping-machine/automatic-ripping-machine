#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Automatic-Ripping-Machine Development Tools
    log to cli and file manager
"""

from colorama import Fore, Style


def console(msg, error=None):
    """
    Print message to the console/cli with colour
        INPUT: message string, error boolean (1 - error, 0 - good)
        OUTPUT: print to console
    """
    if error is None:
        print(msg)
    elif error == 1:
        print(f"{msg}\t[{Fore.RED}Error{Style.RESET_ALL}]")
    else:
        print(f"{msg}\t[{Fore.GREEN}Ok{Style.RESET_ALL}]")


def debug(msg):
    """
    Print debug message to console
        INPUT: message
        OUTPUT: print to console
    """
    console(f"DEBUG: {msg}")


def info(msg):
    """
    Print info message to console
        INPUT: message
        OUTPUT: print to console
    """
    console(f"INFO: {msg}")


def success(msg):
    """
    Print info message to console
        INPUT: message
        OUTPUT: print to console
    """
    console(f"INFO: {msg}", 0)


def error(msg):
    """
    Print error message
        INPUT: message
        OUTPUT: print to console with error
    """
    console(f"ERROR: {msg}", 1)
