"""
Class definition
 ARM system information and version numbers
"""
import os
import sys
import re
import getpass  # noqa E402
import logging  # noqa: E402

from arm.ripper import ProcessHandler


class ARMInfo:
    arm_version = 0
    python_version = 0
    git_branch = ""
    git_commit = ""
    user = ""
    userenv = ""
    install_path = ""

    def __int__(self, install_path):
        self.install_path = install_path
        self.get_git_commit()
        self.get_arm_version()
        self.get_python_version()
        self.get_user_details()

    def get_git_commit(self):
        """
        Function to get the current arm git version
        """
        branch_len = 10
        cmd = "cd /opt/arm && git branch && git log -1"
        git_output = ProcessHandler.arm_subprocess(cmd, True).decode("utf-8")
        git_regex = r"\*\s(\S+)\n(?:\s*\S*\n)*commit ([a-z\d]{5,7})"
        git_match = re.search(git_regex, str(git_output))

        if git_match:
            (self.git_branch, self.git_commit) = git_match.groups()
            if len(self.git_branch) > branch_len:
                self.git_branch = self.git_branch[0:branch_len] + "..."
        else:
            self.git_branch = "unknown"
            self.git_commit = "unknown"

    def get_arm_version(self):
        try:
            version_file = open(os.path.join(self.install_path, 'VERSION'))

            try:
                self.arm_version = version_file.read().strip()

            except (OSError, IOError, FileNotFoundError) as e:
                logging.info(f"ARM Version error: {e}")
                self.arm_version = "unknown"

        except (FileNotFoundError):
            self.arm_version = "unknown"

    def get_python_version(self):
        version = sys.version
        if version:
            self.python_version = version
        else:
            self.python_version = "unknown"

    def get_user_details(self):
        """
        Get the user ARM is running
        getuser reports the process/efective user
        """
        user = getpass.getuser()
        if user:
            self.user = user
        else:
            self.user = "unknown"
