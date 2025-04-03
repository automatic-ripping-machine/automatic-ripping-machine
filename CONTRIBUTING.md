# Contributing Guide
## Introduction
Thank you for contributing to the Automatic Ripping Machine.

## Issues, Bugs, and Feature Requests
If you find a bug, please delete the existing log for that rip, change the log level to DEBUG in your arm.yaml file and then run the rip again to get a clean log for analysis.  You can drag and drop the log onto an issue comment to attach it to the issue.

Also, since ARM relies on software such a HandBrake and MakeMKV try running those programs manually to see if it's an issue there.  If you run ARM in DEBUG mode you should
be able to see the exact call-out to each program.

When submitting a bug, enhancement, or feature request please indicate if you are able/willing to make the changes yourself in a pull request.

## Pull Requests
Please submit pull request for bug fixes against the v2_fixes branch and features against the v2.x_dev branch.

To make a pull request fork this project into your own GitHub repository and after making changes create a PR.  Read https://help.github.com/articles/creating-a-pull-request/

Test your changes locally to the best of your ability to make sure nothing broke.

If you are making multiple changes, please create separate pull requests, so they can be evaluated and approved individually (obviously if changes are trivial, or multiple changes are dependent on each other, then one PR is fine).

Update the README file in your PR if your changes require them.

After submitting your PR check that the Travis CI build passes, if it doesn't you can fix those issues with additional commits.

## Hardware/OS Documentation
The installation guide is for Ubuntu 20.04 and the devs run it in VMware, however, many are running ARM in different environments.  If you have successfully set ARM up in a different environment and would like to assist others, please submit a howto to the [wiki](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki).   

## Testing, Quality, etc.
If you are interested in helping out with testing, quality, etc. please let us know.


