# Roadmap

There are a lot of new features and ideas that get suggested.
To help provide context on where the developers are heading, here are is the current ARM Roadmap.

## Version 2.x

This is the current main branch of ARM.

- Small feature improvements will continue to be made
- Bug fixes will be carried out
- Security fixes will be carried out

## Version 3.x

ARM Version 3.x is being worked on to improve some of the core features of ARM.
Reach out if you can provide assistance to help develop code or provide assistance testing.

- Code rewrite/separation between the ripper and UI codebase
- UI code improvements
  - Alignment to Flask Factory layout
  - Separation of functions/functions into blueprints
  - Aligning UI code, names and functions to make future upgrades easier to implement
- Unit Testing
  - Addition of unit testing for UI, Ripper and Database models
- Database Update
  - Migration from SQLite database to mySQL
  - Separate docker container for database
- Migration from docker to docker-compose
  - docker-compose migration provides easier container management
  - provides easier maintenance for users