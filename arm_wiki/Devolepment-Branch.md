# ARM Development Branch
<!-- TOC -->
* [ARM Development Branch](#arm-development-branch)
  * [v3.x Goals and Objectives](#v3x-goals-and-objectives)
  * [v3.x Implementation Checklist](#v3x-implementation-checklist)
  * [v3.x Key Aims](#v3x-key-aims)
    * [Improve system performance and stability](#improve-system-performance-and-stability)
    * [Move from docker to docker-compose](#move-from-docker-to-docker-compose)
    * [Move the database from SQLite to MySQL](#move-the-database-from-sqlite-to-mysql)
  * [Setup PyCharm for v3.x](#setup-pycharm-for-v3x)
    * [ARM v2.x](#arm-v2x)
    * [ARM v3.x](#arm-v3x)
    * [ARM Unit Testing - UI](#arm-unit-testing---ui)
    * [ARM Unit Testing - Ripper](#arm-unit-testing---ripper)
    * [MySQL Database Configuration](#mysql-database-configuration)
  * [Docker Compose Setup](#docker-compose-setup)
    * [ARM UI](#arm-ui)
    * [ARM Ripper](#arm-ripper)
    * [ARM Database](#arm-database)
    * [ARM Network](#arm-network)
  * [Implementation of Sessions](#implementation-of-sessions-)
<!-- TOC -->

## v3.x Goals and Objectives
The primary goals and objectives of the ARM development roadmap are:

1. Improve system performance and stability
   1. Rewrite of ARM Ripper Code
   2. Rewrite of ARM UI code
2. Move from docker to docker-compose
3. Move the database from SQLite to MySQL
4. Implementation of Sessions

## v3.x Implementation Checklist

Checklist for the developers of v3.x to check the current status of development.
The following information is intended for the developers (or anyone wishing to help out), to see current status.

1. Improve system performance and stability
   1. Rewrite of ARM Ripper Code
      - [ ] Break out of tasks required
        - Define what the ripper looks like
      - [ ] Tasks due to UI seperation
        - [ ] DVD scan in the ripper to the database
        - [ ] Mounted directory size/status to the database
        - [ ] Ripper system information and status to the database
      - [ ] Testing - Unit testing of modules and functions
      - [ ] Testing - Standardise end to end testing for cd/dvd/bluray
      
   2. Rewrite of ARM UI code
      - [x] Refactor to Flask Factory
      - [x] Refactor Models to remove links to ripper code
         - [x] Models refactor
         - [x] Models Unit Test
      - [ ] Models - remove UI and Ripper dependency to models
      - [x] Config - de-tangle integration
      - [x] Refactor Blueprints to align with Models
      - [ ] Add Unit Testing in for UI pages and key functions
        - completed in part
      - Code cleanup
        - [ ] Remove ui/utils, once code moved out


2. Move from docker to docker-compose
   - [x] Implemented, docker-compose.yml created and configured
   - [x] Create separate ARM DB Container
   - [ ] Create separate ARM Ripper Container
   - [x] Create separate ARM UI Container

3. Move the database from SQLite to MySQL
   - [x] Create MySQL container
   - [x] Migrate ARM UI
   - [ ] Migrate ARM Ripper

4. Implementation of Sessions
   - [ ] Pending ARM UI and Ripper rewrite
   - [x] Create DB structure

## v3.x Key Aims

### Improve system performance and stability
- **1:** Rewrite and separation of ARM UI code from the Ripper code base
- **2:** Following 1, rewrite of the Ripper code base
- **3:** Implementation of pytest (unit testing) against all rewritten code

### Move from docker to docker-compose
- **1:** Update docker build and run files to docker-compose
- **2:** Split the ARM Ripper and ARM UI into separate containers
- **3:** Implement MySQL docker container as a new standalone image
- **4:** Implement container networking between containers

### Move the database from SQLite to MySQL
- **1:** Migrate the current database from SQLite to MySQL
- **2:** Support user migration of existing databases to the new container

## Setup PyCharm for v3.x
PyCharm supports code development and testing, with Docker, MySQL, Flask and Test integration.

### ARM v2.x
Create a new 'Flask Server' configuration.
For easier management, name as 'ARM 2.0' or similar.

Configuration:
- Python 3.10
- Script: /opt/arm/arm/runui.py
- Working directory: /opt/arm/arm
- Environment Variables: None
- Paths to ".env" files: none
- Flask env: development
- Enable EnvFile: not checked

### ARM v3.x
Create a new 'Flask Server' configuration.
For easier management, name as 'ARM 3.0' or similar.

Configuration:
- Python 3.10
- Script: /opt/arm/arm/runui.py
- Working directory: /opt/arm/arm
- Environment Variables: MYSQL_IP=127.0.0.1;MYSQL_PASSWORD=example;MYSQL_USER=arm
- Paths to ".env" files: none
- Flask env: development
- Enable EnvFile: not checked

### ARM Unit Testing - UI
Create a new 'Python tests' configuration.
For easier management, name as 'Test - ARM UI' or similar.

Configuration:
- Python 3.10
- Script: /opt/arm/test_ui
- Additional arguments: none
- Working directory: none
- Environment Variables: none
- Paths to ".env" files: none
- Enable EnvFile: not checked

### ARM Unit Testing - Ripper
Create a new 'Python tests' configuration.
For easier management, name as 'Test - ARM Ripper' or similar.

Configuration:
- TBC

### MySQL Database Configuration
Create a new database connection, under 'Data Sources and Drivers'

Name: arm@localhost (user can define)
Host: localhost
Authentication: User and Password
User: arm
Password: example (same password as Env Variables)
database: arm
url: jdbc:mysql://localhost:3306/arm

## Docker Compose Setup
ARM has been split into three containers, database, UI and ripper, all connected together via the arm-network.

### ARM UI
The UI is currently built using the temporary build files for ARM v3.x
Prior to production roll out the following files will need editing:
- docker-compose.yml
  - remove build file
- Dockerfile-UI
  - Move this into the ARM dependencies repo for users to pull
- temp_add-ppa.sh
  - copy pulled from ARM dependencies for the build script
- temp_healthcheck.sh
  - copy pulled from ARM dependencies for the build script

**Volumes**
The UI doesn't need access to all the same volumes as the ripper.
However, to avoid issues all volumes are currently passed. Work is required to remove the need for these volumes.

**Devices**
No devices are passed into the UI, as such no CD/DVD/BRAY drives will show when scanning for drives.
Additional work is required to remove the code and associate with the ripper container loading into the database.

### ARM Ripper
TBD

### ARM Database
ARM DB is pulled from the mysql:latest, with minimal configuration required.
User, password and database need to align with the values entered into the UI and ripper.
The database only requires a single volume, a local folder for the mysql database to reside.

_Note: The arm-db-test is added for running tests against the database. Avoiding entries into a production database_

### ARM Network
The ARM network is a docker network link, allowing data to pass between the UI, Ripper and Database.
For systems where the ripper, UI and database are on separate machines, additional testing will be required.


## Implementation of Sessions 
Implementation of sessions to be conducted once both the rewrite and docker-compose completed

Details from Community Discussion - [ARM Sessions for Drives](https://github.com/automatic-ripping-machine/automatic-ripping-machine/discussions/815)

ARM Default data types - not user editable, based on the current ARM architecture
User Sessions - User editable configuration for sessions, an example set below. User can create, read, update and delete any session

Before starting down the path of implementing this, rather large change, I would like feedback from the ARM users on what they would like in such an update. If you could respond, with any pro's/con's/I can help statements, I will compile them below

**Behaviour**
Edited to add behaviour. These items will be added into the [Project Sessions](https://github.com/orgs/automatic-ripping-machine/projects/6) as tasks for the developers (or anyone) to implement.
The idea with implementing each of these will be a gradual progress towards the ARM sessions.
- ARM default data types will not change, these will be defined within the ARM code base as specific methods of ripping media **[new]**
- ARM User Sessions will be defined within the ARM code base but within the initial database load and configurable by the user to change specific fields as required **[new]**
- Ripping a movie - will rip a movie as the current ARM does **[update]**
- Ripping a TV Show will rip similar to a movie; however, using the session a User will specify the TV series to be ripped and which season is being ripped. Noting that a lot of TV series have strange disk names. Using data from movie database, ARM will use the TV series length to find the number of episodes on the disk and commence ripping. The user will be able to specify which episode the session is starting at, and then the format of the episode naming **[new]**
- Add in TV Series episode name convention. For example SERIES E1E02, Series_s01_e02, or others as defined by the user **[new]**
- Ripping music will be similar to current, but allow for multiple abcde configurations that can rip with different settings, i.e. MP3, FLAC **[new]**
- Ripping media like a home movie, or some other content that needs transcoding but with no media lookup **[new]**
- Ripping/copying data with no media look up or transcoding **[update]**
- Ripping/copying data as an ISO with no media lookup **[update]**

Overview of what some of the settings and sessions could look like.
**ARM Default Data Types**
- DVD: ARM will rip new media as a movie
- Bluray: ARM will rip new media as a blueray movie
- Music: ARM will rip new media as a music
- Data: ARM will rip new media as a data disk (copy contents)
- ISO: ARM will rip new media as an ISO image of the disk

**User Sessions**
- Movie - DVD: ARM session to rip DVD movies - Type: DVD
- Movie - Blueray: ARM sessionto rip Bluray movies - Type: Bluray
- TV - DVD: ARM session to rip DVD TV Series - Type: DVD
- TV - Blueray: ARM session to rip Bluray TV Series - Type: Bluray
- Music - MP3 : ARM session to rip music as mp3 - Type: Music
- Music - flac: ARM session to rip music as flac - Type: Music
- Data: ARM session to rip data disk - Type: Data
- HomeMovie - DVD: ARM session to rip dvd contents but with no title lookup - Type: DVD
- HomeMovie - Bluray: ARM session to rip dvd contents but with no title lookup - Type: Bluray
- ISO: ARM session to create ISO - Type: iso

**Example UI changes**
Sessions listed against the ARM system drives - from [microtechno9000 fork](https://github.com/microtechno9000/automatic-ripping-machine/tree/sessions)
![arm_sessions_drives](https://user-images.githubusercontent.com/62650032/230104782-76f405fa-907e-4848-ab3b-9889609200ce.png)

User editable session / configuration
![arm_sessions_edit](https://user-images.githubusercontent.com/62650032/230104790-a2441e99-df04-4601-8a21-60989e22a55d.png)

Help file, explaining how to use sessions and what they do
![arm_sessions_help](https://user-images.githubusercontent.com/62650032/230104798-0266fa2a-d305-40f7-95bb-5abc6d5d9eb1.png)