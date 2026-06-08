README-TMDBAPI

## BACKGROUND:

ARMui uses a call to the tmdbapi (The Movie Database API) website to determine the full details of a movie.
It tries to get the full name and year, as well as poster/backdrop images,imdb_id and plot.

## HOW TO GET YOUR OWN TMDBAPI KEY:

Start by visiting https://www.themoviedb.org/ create an account then request an API key
This is normally very quick, however it can take a while.


## TO USE YOUR NEW TMDBAPI KEY:

Open the config file (usually /opt/arm/arm.yaml) with your favorite text editor and navigate to the
section 'TMDB_API_KEY=""', put your new API key between the double quotes. Then find 'METADATA_PROVIDER: "omdb"'  
change 'omdb' to 'tmdb' and save the file.
That's it! The API key will be propagated throughout the ARMui appropriate, and any future
links or tools using the API will be made aware.
