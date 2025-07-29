"""Main file for interacting with omdb and tmdb"""
import urllib
import json
import re
import requests
from flask.logging import default_handler  # noqa: F401

from arm.ui import app
import arm.config.config as cfg

TMDB_YEAR_REGEX = r"-\d{0,2}-\d{0,2}"


def call_omdb_api(title=None, year=None, imdb_id=None, plot="short"):
    """
    Queries OMDbapi.org for title information and parses if it's a movie
        or a tv series
    :param title: Title of job
    :param year: year if supplied
    :param imdb_id: imdb if supplied
    :param plot: if plot should be short/full. Defaults "short"
    :return: dict of
    """
    omdb_api_key = cfg.arm_config['OMDB_API_KEY']
    title_info = None
    # Default url
    str_url = f"https://www.omdbapi.com/?s={title}&plot={plot}&r=json&apikey={omdb_api_key}"
    # Build url for omdb
    if imdb_id:
        str_url = f"https://www.omdbapi.com/?i={imdb_id}&plot={plot}&r=json&apikey={omdb_api_key}"
    elif title:
        # try:
        title = urllib.parse.quote(title)
        if year and year is not None:
            year = urllib.parse.quote(year)
            str_url = f"https://www.omdbapi.com/?s={title}&y={year}&plot={plot}&r=json&apikey={omdb_api_key}"
        else:
            str_url = f"https://www.omdbapi.com/?s={title}&plot={plot}&r=json&apikey={omdb_api_key}"
    else:
        app.logger.debug("no params")
    # connect to omdb and add background key
    try:
        title_info_json = urllib.request.urlopen(str_url).read()
        title_info = json.loads(title_info_json.decode())
        title_info['background_url'] = None
        app.logger.debug(f"omdb - {title_info}")
        if 'Error' in title_info or title_info['Response'] == "False":
            title_info = None
    except urllib.error.HTTPError as error:
        app.logger.error(f"omdb call failed with error - {error}")
    else:
        app.logger.debug("omdb - call was successful")
    return title_info


def get_omdb_poster(title=None, year=None, imdb_id=None, plot="short"):
    """
    Queries OMDbapi.org for the poster for movie/show
    :param title: title of movie/show
    :param year: year of release
    :param imdb_id: imdb id of movie/show
    :param plot: short or full plot
    :return: [poster_link, imdb_id]
    """
    omdb_api_key = cfg.arm_config['OMDB_API_KEY']
    if imdb_id:
        str_url = f"https://www.omdbapi.com/?i={imdb_id}&plot={plot}&r=json&apikey={omdb_api_key}"
        str_url_2 = ""
    elif title:
        str_url = f"https://www.omdbapi.com/?s={title}&y={year}&plot={plot}&r=json&apikey={omdb_api_key}"
        str_url_2 = f"https://www.omdbapi.com/?t={title}&y={year}&plot={plot}&r=json&apikey={omdb_api_key}"
    else:
        app.logger.debug("no params")
        return None, None
    try:
        title_info_json = urllib.request.urlopen(requests.utils.requote_uri(str_url)).read()
    except Exception as error:
        app.logger.debug(f"Failed to reach OMdb - {error}")
    else:
        title_info = json.loads(title_info_json.decode())
        # app.logger.debug("omdb - " + str(title_info))
        if 'Error' not in title_info:
            return title_info['Search'][0]['Poster'], title_info['Search'][0]['imdbID']

        try:
            title_info_json2 = urllib.request.urlopen(requests.utils.requote_uri(str_url_2)).read()
            title_info2 = json.loads(title_info_json2.decode())
            # app.logger.debug("omdb - " + str(title_info2))
            if 'Error' not in title_info2:
                return title_info2['Poster'], title_info2['imdbID']
        except Exception as error:
            app.logger.error(f"Failed to reach OMdb - {error}")

    return None, None


def get_tmdb_poster(search_query=None, year=None):
    """
    Queries api.themoviedb.org for the poster and backdrop for movie
    :param search_query: title of movie/show
    :param year: year of movie/show
    :return: dict of search results
    """
    tmdb_api_key = cfg.arm_config['TMDB_API_KEY']
    search_results, poster_base, response = tmdb_fetch_results(search_query, year, tmdb_api_key)

    # if status_code is in search_results we know there was an error
    if 'status_code' in search_results:
        app.logger.debug(f"get_tmdb_poster failed with error -  {search_results['status_message']}")
        return None

    # If movies are found return those after processing
    if search_results['total_results'] > 0:
        app.logger.debug(search_results['total_results'])
        return tmdb_process_poster(search_results, poster_base)

    # Search tmdb for tv series
    url = f"https://api.themoviedb.org/3/search/tv?api_key={tmdb_api_key}&query={search_query}"
    response = requests.get(url)
    search_results = json.loads(response.text)
    # app.logger.debug(json.dumps(response.json(), indent=4, sort_keys=True))
    if search_results['total_results'] > 0:
        app.logger.debug(search_results['total_results'])
        return tmdb_process_poster(search_results, poster_base)
    app.logger.debug("No results found")
    return None


def tmdb_process_poster(search_results, poster_base):
    """
    Process the results from tmdb and fix results with poster\n
    :param search_results: results from tmdb search
    :param poster_base: poster_base from search
    :return: Single media entry with poster or None if none found
    """
    for media in search_results['results']:
        if media['poster_path'] is not None and 'release_date' in media:
            released_date = re.sub(TMDB_YEAR_REGEX, "", media['release_date'])
            app.logger.debug(f"{media['title']} ({released_date})- {poster_base}{media['poster_path']}")
            media['poster_url'] = f"{poster_base}{media['poster_path']}"
            media["Plot"] = media['overview']
            media['background_url'] = f"{poster_base}{media['backdrop_path']}"
            media['Type'] = "movie"
            app.logger.debug(media['background_url'])
            return media
    return None


def tmdb_search(search_query=None, year=None):
    """
    Queries api.themoviedb.org for movies close to the query
    :param search_query: title of movie or tv show
    :param year: year of release
    :return: json/dict of search results
    """
    tmdb_api_key = cfg.arm_config['TMDB_API_KEY']
    search_results, poster_base, response = tmdb_fetch_results(search_query, year, tmdb_api_key)
    app.logger.debug(f"Search results - movie - {search_results}")
    if 'status_code' in search_results:
        app.logger.error(f"tmdb_fetch_results failed with error -  {search_results['status_message']}")
        return None
    return_results = {}
    if search_results['total_results'] > 0:
        app.logger.debug(f"tmdb_search - found {search_results['total_results']} movies")
        return tmdb_process_results(poster_base, return_results, search_results, "movie")
    # Search for tv series
    app.logger.debug("tmdb_search - movie not found, trying tv series ")
    url = f"https://api.themoviedb.org/3/search/tv?api_key={tmdb_api_key}&query={search_query}"
    response = requests.get(url)
    search_results = json.loads(response.text)
    if search_results['total_results'] > 0:
        app.logger.debug(search_results['total_results'])
        return tmdb_process_results(poster_base, return_results, search_results, "series")

    # We got to here with no results give nothing back
    app.logger.debug("tmdb_search - no results found")
    return None


def tmdb_process_results(poster_base, return_results, search_results, media_type="movie"):
    """
    Process search result so that it follows omdb style of output
    :param poster_base: Base path to the poster
    :param return_results: dict of results to be returned in omdb format
    :param search_results: results from tmdb
    :param media_type: movie or series
    :return: dict/json that will be returned to arm
    """
    for result in search_results['results']:
        app.logger.debug(result)
        result['poster_path'] = result['poster_path'] if result['poster_path'] is not None else None
        result['release_date'] = '0000-00-00' if 'release_date' not in result else result['release_date']
        result['imdbID'] = tmdb_get_imdb(result['id'])
        result['Year'] = re.sub(TMDB_YEAR_REGEX, "", result['first_air_date']) if 'first_air_date' in result else \
            re.sub(TMDB_YEAR_REGEX, "", result['release_date'])
        result['Title'] = result['title'] if 'title' in result else result['name']  # This isn't great
        result['Type'] = media_type
        result['Poster'] = f"{poster_base}{result['poster_path']}"
        result['background_url'] = f"{poster_base}{result['backdrop_path']}"
        result["Plot"] = result['overview']
    return_results['Search'] = search_results['results']
    return return_results


def tmdb_get_imdb(tmdb_id):
    """
    Queries api.themoviedb.org for imdb_id by TMDB id\n
    :param tmdb_id: tmdb id of media
    :return: str of imdb_id
    """
    # https://api.themoviedb.org/3/movie/78?api_key=
    # &append_to_response=alternative_titles,changes,credits,images,keywords,lists,releases,reviews,similar,videos
    tmdb_api_key = cfg.arm_config['TMDB_API_KEY']
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={tmdb_api_key}&" \
          f"append_to_response=alternative_titles,credits,images,keywords,releases,reviews,similar,videos,external_ids"
    url_tv = f"https://api.themoviedb.org/3/tv/{tmdb_id}/external_ids?api_key={tmdb_api_key}"
    # Making a get request
    response = requests.get(url)
    search_results = json.loads(response.text)
    # 'status_code' means id wasn't found
    if 'status_code' in search_results:
        # Try tv series
        response = requests.get(url_tv)
        tv_json = json.loads(response.text)
        app.logger.debug(tv_json)
        if 'status_code' not in tv_json:
            return tv_json['imdb_id']
        return None
    return search_results['external_ids']['imdb_id']


def tmdb_find(imdb_id):
    """
    basic function to return an object from TMDB from only the IMDB id
    :param str imdb_id: the IMDB id to lookup
    :return: dict in the standard 'arm' format
    """
    tmdb_api_key = cfg.arm_config['TMDB_API_KEY']
    url = f"https://api.themoviedb.org/3/find/{imdb_id}?api_key={tmdb_api_key}&external_source=imdb_id"
    poster_size = "original"
    poster_base = f"https://image.tmdb.org/t/p/{poster_size}"
    # Making a get request
    response = requests.get(url)
    search_results = json.loads(response.text)
    # app.logger.debug(f"tmdb_find = {search_results}")
    if len(search_results['movie_results']) > 0:
        # We want to push out everything even if we don't use it right now, it may be used later.
        return_results = {'results': search_results['movie_results']}
        return_results['poster_url'] = f"{poster_base}{return_results['results'][0]['poster_path']}"
        return_results["Plot"] = return_results['results'][0]['overview']
        return_results['background_url'] = f"{poster_base}{return_results['results'][0]['backdrop_path']}"
        return_results['Type'] = "movie"
        return_results['imdbID'] = imdb_id
        return_results['Poster'] = return_results['poster_url']
        return_results['Year'] = re.sub(TMDB_YEAR_REGEX, "", return_results['results'][0]['release_date'])
        return_results['Title'] = return_results['results'][0]['title']
    else:
        # We want to push out everything even if we don't use it right now, it may be used later.
        return_results = {'results': search_results['tv_results']}
        return_results['poster_url'] = f"{poster_base}{return_results['results'][0]['poster_path']}"
        return_results["Plot"] = return_results['results'][0]['overview']
        return_results['background_url'] = f"{poster_base}{return_results['results'][0]['backdrop_path']}"
        return_results['imdbID'] = imdb_id
        return_results['Type'] = "series"
        return_results['Poster'] = return_results['poster_url']
        return_results['Year'] = re.sub(TMDB_YEAR_REGEX, "", return_results['results'][0]['first_air_date'])
        return_results['Title'] = return_results['results'][0]['name']
    return return_results


def validate_imdb(imdb_id):
    """
    Validate that the imdb id we got
    :param str imdb_id:
    :return:
    """
    # ['tt', 'nm', 'co', 'ev', 'ch' or 'ni'] - 123456789
    # /ev\d{7}\/\d{4}(-\d)?|(ch|co|ev|nm|tt)\d{7}/
    # /^ev\d{7}\/\d{4}(-\d)?$|^(ch|co|ev|nm|tt)\d{7}$/
    app.logger.debug(imdb_id)


def tmdb_fetch_results(search_query, year, tmdb_api_key):
    """
    Main function for fetching movie results from TMDB\n
    :param str search_query: search query from ARMui
    :param str year: the year of the movie/tv-show
    :param str tmdb_api_key: tmdb API key
    :return: [search_results dict, poster_img string, requests Response]
    """
    # https://api.themoviedb.org/3/movie/78?api_key= # base url
    # Additional
    # &append_to_response=alternative_titles,changes,credits,images,keywords,lists,releases,reviews,similar,videos
    if year:
        url = f"https://api.themoviedb.org/3/search/movie?api_key={tmdb_api_key}&query={search_query}&year={year}"
    else:
        url = f"https://api.themoviedb.org/3/search/movie?api_key={tmdb_api_key}&query={search_query}"
    # Valid poster sizes
    # "w92", "w154", "w185", "w342", "w500", "w780", "original"
    poster_size = "original"
    poster_base = f"https://image.tmdb.org/t/p/{poster_size}"
    response = requests.get(url)
    return_json = json.loads(response.text)
    return return_json, poster_base, response
