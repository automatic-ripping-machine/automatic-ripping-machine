# git.py
import re
import subprocess

INSTALLPATH = "/opt/arm"
def get_git_revision_hash() -> str:
    """Get full hash of current git commit"""
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                                   cwd=INSTALLPATH).decode('ascii').strip()


def get_git_revision_short_hash() -> str:
    """Get short hash of current git commit"""
    return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'],
                                   cwd=INSTALLPATH).decode('ascii').strip()


def git_check_updates(current_hash) -> bool:
    """Check if we are on latest commit"""
    git_update = subprocess.run(['git', 'fetch',
                                 'https://github.com/automatic-ripping-machine/automatic-ripping-machine'],
                                cwd=INSTALLPATH, check=False)
    # git for-each-ref refs/remotes/origin --sort="-committerdate" | head -1
    git_log = subprocess.check_output('git for-each-ref refs/remotes/origin --sort="-committerdate" | head -1',
                                      shell=True, cwd="/opt/arm").decode('ascii').strip()
    print(git_update.returncode)
    print(git_log)
    print(current_hash)
    print(bool(re.search(rf"\A{current_hash}", git_log)))
    return bool(re.search(rf"\A{current_hash}", git_log))


def git_get_updates() -> dict:
    """update arm"""
    git_log = subprocess.run(['git', 'pull'], cwd=INSTALLPATH, check=False)
    return {'stdout': git_log.stdout, 'stderr': git_log.stderr,
            'return_code': git_log.returncode, 'form': 'ARM Update', "success": (git_log.returncode == 0)}