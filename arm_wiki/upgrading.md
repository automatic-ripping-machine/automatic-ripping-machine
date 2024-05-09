# Command line update (newer versions)

## First backup config files
:bangbang: Backup config file and replace it with the updated config :bangbang:
```bash
mv /opt/arm/arm.yaml /MY/SAFE/PLACE/arm.yaml
```
You can than upgrade

-------------------------------------

## Update A.R.M (Version >v2.2)
Shell/Terminal commands
```
cd /opt/arm
git stash
git pull
# Remove old yaml file if it still exists
rm arm.yaml
# Copy new config file
sudo cp docs/arm.yaml.sample arm.yaml
# install any new packages
sudo pip3 install -r requirements.txt
sudo ln -s /opt/arm/arm.yaml /etc/arm/
sudo ln -s /opt/arm/setup/.abcde.conf /home/arm/
```
This should update most of A.R.M, you will still need to restart the armui service if you have one installed.

To do this run: `sudo systemctl restart armui` If you didn't install the service you can reboot, or find the running armui process and kill it.

-------------------------------------
## Upgrading From Very Old Versions (Pre v2.2)

Upgrading is now possible from version as old as v2.0

All you need to do is move all the new files from this repo into the arm folder `/opt/arm` 
Then insert a disc to start the upgrade process. The process is almost fully automatic. You still need to insert a disc to start the process. 

Sometimes the disc needs to be inserted/ejected twice for this to fully trigger.

If this process fails to update the arm database you may need to run the arm command manually with a disc already inserted.

`sudo -u arm /usr/bin/python3 /opt/arm/arm/ripper/main.py -d sr0`

-------------------------------------
### Notes...

#### :small_red_triangle: Pre version 2.6
- For your own clarity sake, it may be best to delete the folder `/opt/arm/arm/ui/static` completely before adding the files from this repo. 
The reason this is recommended is that previous versions of ARM shipped with a lot of extra files that were not used at all.
This made things slightly more cluttered, especially for users who want to customise or tinker with ARM. The newest version of ARM only ships with things it needs, and provides the sources so the end users can obtain those extra sources if they wish.
- It should be possible to run the shell commands, but this hasn't been tested.