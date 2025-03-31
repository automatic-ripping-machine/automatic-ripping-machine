"""
Function definition
  Wrapper for the python subprocess module
"""
import logging
import subprocess


def arm_subprocess(cmd, in_shell, check=False):
    """
    Handle creating new subprocesses and catch any errors
    """
    arm_process = None
    logging.debug(f"Running command: {cmd}")
    try:
        arm_process = subprocess.check_output(
            cmd,
            shell=in_shell
        )
    except subprocess.CalledProcessError as error:
        logging.error(f"Error executing command `{cmd}`: {error}")
        if check:
            raise error

    return arm_process
