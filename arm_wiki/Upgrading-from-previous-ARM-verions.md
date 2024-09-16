## Upgrading from v2_master to v2.2_dev

If you wish to upgrade from v2_master to v2.2_dev instead of a clean install, these directions should get you there.  

```bash
cd /opt/arm
sudo git checkout v2.2_dev
sudo pip3 install -r requirements.txt
```
Backup config file and replace it with the updated config
```bash
mv arm.yaml arm.yaml.old
cp docs/arm.yaml.sample arm.yaml
```

There are new config parameters so review the new arm.yaml file

Make sure the 'arm' user has write permissions to the db directory (see your arm.yaml file for locaton). is writeable by the arm user.  A db will be created when you first run ARM.

Make sure that your rules file is properly **copied** instead of linked:
```
sudo rm /usr/lib/udev/rules.d/51-automedia.rules
sudo cp /opt/arm/setup/51-automedia.rules /etc/udev/rules.d/
```
Otherwise you may not get the auto-launching of ARM when a disc is inserted behavior
on Ubuntu 20.04.

Please log any issues you find.  Don't forget to run in DEBUG mode if you need to submit an issue (and log files).  Also, please note that you are running 2.2_dev in your issue.

You will also need to visit your http://WEBSERVER_IP:WEBSERVER_PORT/setup  
							&#x26A0; &#x26A0; **!!!WARNING!!!** &#x26A0; &#x26A0;  					

Visiting this page will delete your current database and create a new db file. You WILL lose jobs/tracks/etc from your database
This will setup the new database, and ask you to make an admin account. Because of the changes to the armui its not possible to view/change/delete entries without logging in. 
Due to these large number of changes to the database its not currently possible to upgrade without creating a new database

