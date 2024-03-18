# Contributing Guide
## Introduction
Thank you for contributing to the Automatic Ripping Machine.

## Issues, Bugs, and Feature Requests
If you find a bug, please delete the existing log for that rip, change the log level to DEBUG in your arm.yaml file and then run the rip again to get a clean log for analysis.  You can drag and drop the log onto an issue comment to attach it to the issue.

Also, since ARM relies on software such a HandBrake and MakeMKV try running those programs manually to see if it's an issue there.  If you run ARM in DEBUG mode you should
be able to see the exact call out to each program.

When submitting a bug, enhancement, or feature request please indicate if you are able/willing to make the changes yourself in a pull request.

## Pull Requests
**Please submit pull request for bug fixes/features against the v2_devel branch.**

To make a pull request fork this project into your own github repository and after making changes create a PR.  Read https://help.github.com/articles/creating-a-pull-request/

Test your changes locally to the best of your ability to make sure nothing broke.

If you are making multiple changes, please create  separate pull requests so they can be evaluated and approved individually (obviously if changes are trivial, or multiple changes are dependent on each other then one PR is fine).

Update the README file in your PR if your changes require them.

After submitting your PR check that the Travis CI build passes, if it doesn't you can fix those issues with additional commits.

## Hardware/OS Documentation
The installation guide is for Ubuntu20.04/Debian Buster/OMVault(debian) and the devs run it in VMware, however, many are running ARM in different environments.  If you have successfully set ARM up in a different environment and would like to assist others, please submit a howto to the [wiki](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki).   

## Testing, Quality, etc.
 
 ARM is written to meed the Python style guide PEP8 (https://pep8.org/). On submitting a new PR to ARM, the new and modified code will be checked against PEP8 for compliance. Prior to loading up a new PR, it is recommended that the each new or modified file within the PR be run through PEP8 (now pycodestyle).
 ### Setting up pycodestyle
 
 You can install, upgrade, and uninstall pycodestyle.py with these commands:
 
 ```
 $ pip install pycodestyle
 $ pip install --upgrade pycodestyle
 $ pip uninstall pycodestyle
 ```
 
 There’s also a package for Debian/Ubuntu, but it’s not always the latest version.
 
 Example usage and output
 
 ```
 $ pycodestyle --first optparse.py
 optparse.py:69:11: E401 multiple imports on one line
 optparse.py:77:1: E302 expected 2 blank lines, found 1
 optparse.py:88:5: E301 expected 1 blank line, found 0
 optparse.py:222:34: W602 deprecated form of raising exception
 optparse.py:347:31: E211 whitespace before '('
 optparse.py:357:17: E201 whitespace after '{'
 optparse.py:472:29: E221 multiple spaces before operator
 optparse.py:544:21: W601 .has_key() is deprecated, use 'in'
 ```
 
 You can also make pycodestyle.py show the source code for each error, and even the relevant text from PEP 8:
 
 ```
 $ pycodestyle --show-source --show-pep8 testsuite/E40.py
 testsuite/E40.py:2:10: E401 multiple imports on one line
 import os, sys
          ^
     Imports should usually be on separate lines.
 
     Okay: import os\nimport sys
     E401: import sys, os
 ```
 
 Or you can display how often each error was found:
 
 ```
 $ pycodestyle --statistics -qq Python-2.5/Lib
 232     E201 whitespace after '['
 599     E202 whitespace before ')'
 631     E203 whitespace before ','
 842     E211 whitespace before '('
 2531    E221 multiple spaces before operator
 4473    E301 expected 1 blank line, found 0
 4006    E302 expected 2 blank lines, found 1
 165     E303 too many blank lines (4)
 325     E401 multiple imports on one line
 3615    E501 line too long (82 characters)
 612     W601 .has_key() is deprecated, use 'in'
 1188    W602 deprecated form of raising exception
 ```
 
 Source: https://pypi.org/project/pycodestyle/
 
### Testing out ARM
 
 If you are interested in helping out with testing, quality, etc. please let us know.
