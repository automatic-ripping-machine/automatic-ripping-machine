README-OMDBAPI

BACKGROUND:

The ARM uses a call to the omdbapi (Open Movie Database API) web site to determine whether a video disc
is a movie or a TV series. It also uses the database to determine the correct year for a movie, since
older movies frequently report the date of issue on DVD as opposed to the date of the actual movie. An
example of this is "The Enforcer" which was originally released in 1976, but released on DVD in 2008.

Give the two primary functions OMDBAPI is used for in ARM, it's fair to say that having it not work is
nothing more than a bit of a headache in re-titling and categorizing your final product. Years may be
wrong, and as the ARM is currently designed, your movies will be placed in the Unknown directory as 
opposed to the "Movies" directory. I can also see plenty of future uses for this functionality, so it
seemed prudent to repair it and make it work again. And I like shell scripts, and I wanted to
contribute something that might truly be useful to an already amazing project.

HISTORY:

Full writeup is here: https://www.patreon.com/posts/api-is-going-10743518

As of May 5, 2017, the developer/maintainer of the omdbapi.com website was forced to take the API
project private due to unforeseen request charges. Specifically, it appears (to me) that they were
generating significantly more requests to the API than they anticipated, and the costs were either
about to, or did, catch up with them. In short, they can no longer provide the API access for free
in the current term.  I am under the impression that they may open the API back up for casual and
limited use once the financial bleeding stops. In the meantime, a patronage program is available for
$1.00/month on a 12-month commitment which allows for 100,000 queries per day. It is this threshold
that leaves me with the hope that the API may go public again on a limited basis at some point in
the future, and it is upon this hope that I went ahead and made the minor code updates to support
the requirement for an API key.

HOW TO GET YOUR OWN OMDBAPI KEY:

Start by visiting http://www.omdbapi.com/ As of this writing (2017-06-08), you will find a
link labeled "Become a Patron." That link will take you to the Patreon site, where you can sign up.
Select the $1.00/month level and complete the process (or donate more if you feel so compelled -- it
seems to be a very useful project.) Once you have completed your donation, go back to the omdbapi
home page, look to the top menu bar, click on "Patrons --> API Key." Enter the email address under
which you registered, and your API key will be emailed to you. Reports are that it may take a few hours
but mine came within a minute or two.

TO USE YOUR NEW OMDBAPI KEY:

Open the config file (usually /opt/arm/config) with your favorite text editor and navigate to the
section 'OMDB_API_KEY=""', put your new API key between the double quotes, and save the file.
That's it! The API key will be propagated throughout the ARM tool as appropriate, and any future
links or tools using the API will be made aware.

DEVELOPER'S NOTES:

Since not everyone interested in testing this update prior to pulling it into the master codebase
may want to purchase an API key, and since each API key gives access to 100,000 queries per day,
I am willing to share my key for testing purposes provided you don't go over, oh let's say, 25,000
queries in a day (LOL). Contact me at my primary email cbunt1@yahoo.com or my github account cbunt1.

A special thank you to Aaron Helton (aargonian) for your help with the Python update...I'm a
Shell scripter, not a Python scripter...:-)