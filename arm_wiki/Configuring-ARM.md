## Configure ARM

- Edit your "config" file (located at /opt/arm/arm.yaml) to determine what options you'd like to use.  Pay special attention to the 'directory setup' section and make sure the 'arm' user has write access to wherever you define these directories.

- Edit the music config file (located at /home/arm/.abcde.conf)

- To rip Blu-Rays after the MakeMKV trial is up you will need to purchase a license key or while MakeMKV is in BETA you can get a free key (which you will need to update from time to time) here:  https://www.makemkv.com/forum2/viewtopic.php?f=5&t=1053 and create /home/arm/.MakeMKV/settings.conf with the contents:

        app_Key = "insertlicensekeyhere"

- For ARM to identify movie/tv titles register for an API key at OMDb API: http://www.omdbapi.com/apikey.aspx and set the OMDB_API_KEY parameter in the config file.


**Email Notifications**

A lot of random problems are found in the sysmail, email alerting is a most effective method for debugging and monitoring.

I recommend you install postfix from here:http://mhawthorne.net/posts/2011-postfix-configuring-gmail-as-relay/

Then configure /etc/aliases 
	e.g.: 
	
	```	
	root: my_email@gmail.com
	arm: my_email@gmail.com
	userAccount: my_email@gmail.com
	```
	
Run below to pick up the aliases

	```
	sudo newaliases
	```
## Apprise notifications

You can enable Apprise notifications by editing your arm.yaml file. 
You will need to find
 
`APPRISE: ""`

Then add your apprise.yaml file to here like so.

`APPRISE: "/opt/arm/apprise.yaml"`

A sample apprise has been included with arm but is not enabled by default, you can find this file in the doc folder of your arm installation.
You can find how to get the keys/setting up the apprise.yaml from here https://github.com/caronc/apprise/wiki