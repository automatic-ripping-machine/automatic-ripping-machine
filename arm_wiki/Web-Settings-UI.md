# Settings - User Interface (UI) Settings
<!-- TOC -->
* [ARM Job Management](#arm-job-management)
  * [Overview](#overview)
  * [Main Page](#main-page)
  * [Jobs Page](#jobs-page)
    * [Job Modes](#job-modes)
      * [Auto (Default)](#auto-default)
      * [Manual](#manual)
<!-- TOC -->

## Overview

The UI settings configure update rates and presentation of the webpage.

## Settings

### Index Refresh

How often to refresh the home page in milliseconds, showing updates to any current jobs.
Default setting is '2000', updating the home page every 2 seconds.

### Notification Timeout

Set the Notification timeout value in milliseconds, values less than 1 second should be avoided.

### Use Icons

Use icons on jobs. If set to false ARM will use text.

### Save Remote Images

Save job images locally
If True: A.R.M will copy remote images to a local directory and use the update the job to use the local version.

### Bootstrap Skin

Change User Interface bootstrap skin.
You can find all versions available from https://www.bootstrapcdn.com/bootswatch/
You will need to refresh the page to see the updated bootstrap skin

### Language

Change the langauge A.R.M uses, defaults to English (en)

### Database Limit

Limit the number of jobs to show on each page, over 175 will make things go funky!
