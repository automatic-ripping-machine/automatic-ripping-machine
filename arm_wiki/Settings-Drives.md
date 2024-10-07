# ARM Drive Management
<!-- TOC -->
* [ARM Drive Management](#arm-drive-management)
  * [Overview](#overview)
  * [Drive Settings](#drive-settings)
    * [1. Scanning For New Drives](#1-scanning-for-new-drives)
    * [2. Edit Drive Details](#2-edit-drive-details)
    * [3. Removing a Drive](#3-removing-a-drive)
    * [4. Eject or Close Drive](#4-eject-or-close-drive)
<!-- TOC -->

## Overview

The ARM Settings page provides an overview of the connected CD, DVD or Bluray drives connected to the system.
Scanning for drives allows easier management, viewing and status of jobs running on the ARM system.

> [!NOTE]
> For ARM to rip media the drives do not need to appear on the settings, drive page.
> However, if ARM cannot find a drive following a scan, there may be issues with the docker configuration.

<img title="ARM Settings Page" alt="Default ARM Settings page with no drives" src="images/arm_settings.png" width="50%" height=""/>

## Drive Settings

The following options are available from the ARM settings page, for each of the connected CD, DVD or Blu-ray drives.

1. Scan for Drives
2. Edit Drive Details
3. Remove a Drive
4. Eject or Close Drive

<img title="ARM Settings Page" alt="Default ARM Settings page with no drives" src="images/arm_settings_drives.png" width="30%" height=""/>

### 1. Scanning For New Drives

To add a new drive to the ARM system, select 'Scan for Drives'
ARM will scan the system looking for any new drive on the system, and associate any previous jobs to the drive.

Once ARM has scanned the system, the following information will be presented.

| Field        | Details                                                        | System or User |
|--------------|----------------------------------------------------------------|----------------|
| Name         | Defaults to `Drive x` where x is the total number of drives    | User editable  |
| Type         | Type of drive, CD, DVD or Bluray or combination of all three   | System field   |
| Mount Path   | System mount path reported                                     | System field   |
| Current Job  | When the drive is processing a job, current jobs will be shown | System field   |
| Previous Job | Once competed, previous or old jobs will be shown              | System field   |
| Description  | User defined description for the drive                         | User editable        |


### 2. Edit Drive Details

Drive names and descriptions can be modified to help in finding the right drive.
As great as knowing a drive is `sr0` or `sr1`, adding in a description like 'top disk - Blu-ray' can help put the disk in the right drive.
Especially for users with multiple drives in a system.


### 3. Removing a Drive

Sometimes you might just get to a point where removing a drive is necessary.
A drive might give up and just quit, removing it from the ARM web page makes life easier and cleaner.

> [!NOTE]
> If you remove a drive accidentally, don't worry.
> Simply running the 'Scan for Drives' will return all drives back if you accidentally remove the wrong drive.

### 4. Eject or Close Drive

From here you can click on a drive and control the drive open (eject) or close state.
Handy if you have a lot of drives and still not quite sure which drive is what.
