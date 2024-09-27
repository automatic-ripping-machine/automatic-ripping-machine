# IMPORTANT

***
This installation method is not supported or maintained by the ARM Developers.
For full support and continued maintenance,
recommend installing ARM via the supported [Docker Container](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/docker).

**Use at your own risk** 

***

# TrueNAS Installation Guide

This is a step-by-step walkthrough adding ARM (Automatic Ripping Machine) to a TrueNAS Scale system as a custom app.

**Note**: The following guide was performed on the Cobia version of TrueNAS Scale.
Prior versions of TrueNAS Scale have an issue with GPU Allocation, which Cobia fixes.


1. Create a custom app, Apps → Discover Apps → Custom App 

    Refer to TrueNAS documentation for additional information [Documentation Hub](https://www.truenas.com/docs/scale/24.04/scaletutorials/apps/usingcustomapp/)

2. Name the Application, e.g. ‘arm’, ‘autorip’

3. Set the image repository to ‘automaticrippingmachine/automatic-ripping-machine’ without quotes.

4. Create a custom directory under the ‘Host Path Volumes’ by pressing ‘Add’.
    Configure the following directories:

    | Local Path                     | ARM Docker Directory |
    |--------------------------------|----------------------|
    | <path_to_arm_user_home_folder> | /home/arm            |
    | <path_to_music_folder>         | /home/arm/music      |
    | <path_to_logs_folder>          | /home/arm/logs       |
    | <path_to_media_folder>         | /home/arm/media      |
    | <path_to_config_folder>        | /etc/arm/config      |
   

5. (Optional) GPU Configuration.
   If you don’t have a compatible GPU or wish to keep your video files raw, you can skip this step as this is only required for transcoding.
   Continue down to the ‘Resource Reservation’ section and into the ‘GPU Configuration’
   If you have a supported GPU, allocate at least a single one of the GPUs to enable the NVENC(Geforce) or other encodings, it will show you multiple GPUs that you can allocate, choose at least one.
      - For NVIDIA GPUs, not only do need to allocate your GPU, but you must also add a pair of variables in the ‘Container Environment Variables’ section:
        - name: `NVIDIA_VISIBLE_DEVICES` value: `all`
        - name: `NVIDIA_DRIVER_CAPABILITIES` value: `all`

6. (Optional) Enable Web Portal. Not a necessary step, but this will create a button on the ARM app in TrueNAS Scale
to allow quick access to the ARM Web GUI.
Web Portal access requires enabling of port forwarding. Under 'Enable WebUI Porta' configure port forwarding

    | Container Port | Node Port         |
    |----------------|-------------------|
    | 8080           | <port-of-choice>  |

7. The ARM container's internal user has User ID `uid 1000` and Group ID `gid 1000`.
You will need to make sure the container has read and write permissions in the paths set in Step 4.
You have 2 choices for this:
   - **Preferred**: In the Container Environment Variables section add the variables `ARM_UID` and `ARM_GID`
   and set both to `568` (TrueNAS' default apps user/group). 
   - **Alternate**: Adjust the directory and file permissions to allow read/write access for user and group ID `1000`,
   either through chowning the directories/files, or adding corresponding ACLs.

8. Click the ‘Install’ button at the bottom and wait for it to complete.

If everything was done properly, ARM should now work.
Head into the WebGUI either using the Webportal button on the ARM app if you made one or using the ‘ip:port’ in the browser to check if ARM is working.

There you go. Any other TrueNAS Scale users can update or correct as needed.