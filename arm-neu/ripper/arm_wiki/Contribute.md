# Contributing Guide
## Introduction
Thank you for contributing to the Automatic Ripping Machine.

## Issues, Bugs, and Feature Requests
If you find a bug, please delete the existing log for that rip,
change the log level to DEBUG in your arm.yaml file and then run the rip again to get a clean log for analysis.  You can drag and drop the log onto an issue comment to attach it to the issue.

Also, since ARM relies on software such as HandBrake and MakeMKV,
try running those programs manually to see if it's an issue there.
If you run ARM in DEBUG mode you should
be able to see the exact call-out to each program.

When submitting a bug, enhancement, or feature request please indicate if you are able/willing to make the changes yourself in a pull request.

## Making Code Changes

To make changes to the code, fork this project into your own GitHub repository.
Make the changes to the code, to implement the feature, or bug fix.
More information can be found in the [GitHub docs](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo).

Once the new feature or bugfix has been incorporated,
test your changes locally to the best of your ability to ensure no new bugs have been introduced.
See [Testing](#Testing) for more information.

If significant changes have been made to ARM, ensure the following:
- Update the README file in your PR
- Update the ARM Wiki, see [ARM Wiki](Contribute-Wiki)

## Raise a Pull Request

Once your code is ready, raise a new Pull Request (PR) within Github from your fork to the ARM main branch.
For additional information, see the [GitHub Docs](https://help.github.com/articles/creating-a-pull-request/)

To make it easier on the Developers reviewing any PR, avoid creating massive changes to the code base in one PR.
Where possible, try to reduce changes to a small feature or bug fix for easy review.

ARM versioning follows the [Semantic Versioning](https://semver.org/) standard and is managed automatically via [release-please](https://github.com/googleapis/release-please). Ensure your commits follow [conventional commit](https://www.conventionalcommits.org/) format:

- `feat:` prefix for features (triggers MINOR version bump)
- `fix:` prefix for bug fixes (triggers PATCH version bump)
- `feat!:` or `BREAKING CHANGE:` in commit body for breaking changes (triggers MAJOR version bump)

On submitting your PR,
GitHub will automatically run multiple checks against the code and report back on the code quality.
Should any issues be identified with the code,
resolve them against the same branch used to raise the PR and push to GitHub.
GitHub will do the rest, re-running all tests.

## Hardware/OS Documentation
The installation guide covers Docker deployment on Linux. Many are running ARM in different environments.
If you have successfully set ARM up in a different environment and would like to assist others, please submit a howto to the [wiki](https://github.com/uprightbass360/automatic-ripping-machine-neu/wiki).

## Testing

ARM follows PEP 8 style guidelines. CI checks (pytest) run automatically on pull requests via GitHub Actions.

To run tests locally:

```
pytest test/ -v
```

If you are interested in helping out with testing, quality, etc. please let us know.
