# Setup guide for Developing an ARM docker image

1. The first step is to make you sure have docker installed (either locally or over a network)

2. Choose your preferred IDE (Notepad++ can work or even IDLE, but a full IDE with all the extras will make things much easier)
    - PyCharm (CE is free) 
    - Visual Studio
    - Atom
    - etc, etc
3. Install the docker plugin for your IDE (You can skip this step if you IDE comes with Dockerfile support)

4. Clone the docker branch to your filesystem
    - `git clone --recurse-submodule https://github.com/1337-server/automatic-ripping-machine.git` (This will clone to the current directory)

5. Open the cloned directory with your IDE

**From this point on i assume that you are using PyCharm, The IDE's all vary in how they deploy/build the docker image. And i prefer PyCharm so I'll explain the steps for it, in hopes that this might apply to other IDE's.**

6. With the project folder open
    - Open the Dockerfile Look for the line `FROM ubuntu:20.04 as base`
    - If you can see 2 green arrows `>>` in the gutter (beside the line numbers), You can click it to run/build the docker image.
    - This will build with all default settings. This might work depending on your setup
    - If not continue to next step

7. Add/connect your docker server
    - File -> Settings - > Build, Execution, Deployment -> Docker
    - Click the + icon
    - Name can be anything
    - If your docker is on the same machine You can use the Unix socket default
    - If you're working over a network you will need to provide the link to either the docker executable or your docker api url
    - Pycharm will tell you if the connection was successful or not.
    - Apply/Ok

8. Add a Run/Debug configuration
    - run-> Edit Configurations
    - The + icon to add a new configuration 
    - Select Docker->'Dockerfile'
    - Name: Can be anything
    - Server: This can vary depending on your use case (Use the server you setup from the previous step)
    - Build
      - Dockerfile: Select the Dockerfile using the built in Browser or enter the path to the Dockerfile
      - Image tag: `1337-server/automatic-ripping-machine` (Your preference if you change this)
    - Run
      - Click [Modify]() and enable/tick
        - Run built image
        - Bind ports
        - Bind mounts
        - Environment Variables
        - Run Options
      - Container Name: arm-rippers
      - Bind ports 
        - `8080:8080`
      - Bind mounts (Each folder/-v needs to be added as with the docker run command)
        - `/home/arm:/home/arm`
        - `/home/arm/config:/home/arm/config`  
        - `/home/arm/Music:/home/arm/Music`  
        - `/home/arm/logs:/home/arm/logs`
        - `/home/arm/media:/home/arm/media`

      - Environment Variables (Change these as needed)
        - `MAKEMKV_APP_KEY=keygoeshere` 
        - `UID=1000`
        - `GID=1000` 
        - `PYTHONUNBUFFERED=0`
      - Run Options
        - `--privileged`
9. Save the Run config

10. Once you have made changes you should now be able to Run/build the image (Shift+F10).
   It should now build the image, push the image to docker and then open a new tab in Pycharm labeled Services. 
   This will output the dockers log for easier debugging.

# Troubleshooting

### `[Errno 2] No such file or directory: 'curl-config'` when installing python requirements
This issue is caused by your system not having the `curl` libraries installed.  
To fix this on Ubuntu or Debian, run:
```bash
sudo apt install libcurl4-openssl-dev libssl-dev
```