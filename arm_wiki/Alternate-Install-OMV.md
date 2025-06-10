# Auto Install Script For OpenMediaVault/Debian/Ubuntu 20,22 24.02

> > [!CAUTION]
> This installation method is not supported or maintained by the ARM Developers.
> For full support and continued maintenance,
> we recommend installing ARM via the supported [Docker Container](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/docker).
> This installation method was developed for those that wish to use ARM without Docker.
>
> **Use at your own risk**

This is **not recommended** for first time installations. This was only really intended to be used to reinstall on an environment you know works fully with ARM

**contrib repositories are required!**

## For the attended install use:
 ```
sudo apt install wget
wget https://raw.githubusercontent.com/automatic-ripping-machine/automatic-ripping-machine/main/scripts/installers/DebianInstaller.sh
sudo chmod +x DebianInstaller.sh
sudo ./DebianInstaller.sh
sudo chmod +x /opt/arm/scripts/update_key.sh
 ```
 ```reboot``` 
 to complete installation.


## Post install

### Setting up the database
You will need to visit your http://WEBSERVER_IP:WEBSERVER_PORT/setup  
							&#x26A0; &#x26A0; **!!!WARNING!!!** &#x26A0; &#x26A0;  					

Visiting this page will delete your current database and create a new db file. You WILL lose jobs/tracks/etc from your database
This will set up the new database, and ask you to make an admin account. Because of the changes to the armui it's not possible to view/change/delete entries without logging in. 
Due to these large number of changes to the database it's not currently possible to upgrade without creating a new database, this may change later
but for now you will lose all previous jobs/tracks/configs.

Once it has deleted the current database, it will redirect you to sign in. The default username and password is

- Username: admin 
- Password: password


Alternatively, you can insert a disc or trigger it manually by running 
`/usr/bin/python3 /opt/arm/arm/ripper/main.py -d sr0 | at now` in a terminal/ssh

### File Permissions 

Make sure arm has write permission to the folder you have selected in the arm.yaml. If you haven't changed the arm.yaml it will be `/home/arm`

For example `sudo chmod -R 777 /home/arm` **Please check/change these, this is for example only!**