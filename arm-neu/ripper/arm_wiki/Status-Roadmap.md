# Automatic Ripping Machine (ARM) Development Roadmap

## Overview
The ARM development roadmap outlines the key features, enhancements, and milestones planned for the project.
The aim of this page is to provide some information around where the developers are focusing effort and time to upgrade ARM.

---

## v2.x Goals and Objectives
ARM version 2.x is the current released codebase.
The goals and objectives for any v2.x software is:

1. Maintain the software, resolving any bugs
2. Resolve any security issues as they arise
3. Implement small features as requested by the community

---

## v3.x Goals and Objectives
The primary goals and objectives of the ARM development roadmap are:

1. Improve system performance and stability
   1. Rewrite of ARM Ripper Code
   2. Rewrite of ARM UI code
2. Move from docker to docker-compose
3. Move the database from SQLite to MySQL
4. Implementation of Sessions

---

### Improve system performance and stability
- **1:** Rewrite and separation of ARM UI code from the Ripper code base
- **2:** Following 1, rewrite of the Ripper code base
- **3:** Implementation of pytest (unit testing) against all rewritten code

### Move from docker to docker-compose
- **1:** Update docker build and run files to docker-compose
- **2:** Split the ARM Ripper and ARM UI into seperate containers
- **3:** Implement MySQL docker container as a new standalone image
- **4:** Implement container networking between containers

### Move the database from SQLite to MySQL
- **1:** Migrate the current database from SQLite to MySQL
- **2:** Support user migration of existing databases to the new container

### Implementation of Sessions 
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