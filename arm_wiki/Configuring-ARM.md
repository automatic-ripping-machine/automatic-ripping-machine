## Configure ARM

ARM's config file is usually located at `/etc/arm/config/arm.yaml`. This path can be changed by advanced users by setting the [environment variable](https://wiki.archlinux.org/title/Environment_variables) `ARM_CONFIG_FILE`.

`arm.yaml` includes explanations for each option. Pay special attention to the 'directory setup' section and make sure the 'arm' user has write access to wherever you define these directories.

In case you want to adjust settings specific to audio CDs, you can find the ABCDE config file at `/etc/arm/config/.abcde.conf` unless configured otherwise in `arm.yaml`.

To allow ARM to identify movie/tv titles, register for an [OMDb API key](http://www.omdbapi.com/apikey.aspx) and set the OMDB_API_KEY parameter in the config file.


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