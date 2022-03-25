import urllib
import json
import re
import requests
from flask.logging import default_handler  # noqa: F401

from arm.ui import app
from arm.config.config import cfg

TMDB_YEAR_REGEX = "-[0-9]{0,2}-[0-9]{0,2}"


def call_omdb_api(title=None, year=None, imdb_id=None, plot="short"):
    """ Queries OMDbapi.org for title information and parses if it's a movie
        or a tv series """
    omdb_api_key = cfg['OMDB_API_KEY']

    if imdb_id:
        strurl = f"https://www.omdbapi.com/?i={imdb_id}&plot={plot}&r=json&apikey={omdb_api_key}"
    elif title:
        # try:
        title = urllib.parse.quote(title)
        if year and year is not None:
            year = urllib.parse.quote(year)
            strurl = f"https://www.omdbapi.com/?s={title}&y={year}&plot={plot}&r=json&apikey={omdb_api_key}"
        else:
            strurl = f"https://www.omdbapi.com/?s={title}&plot={plot}&r=json&apikey={omdb_api_key}"
    else:
        app.logger.debug("no params")
        return None
    # app.logger.debug(f"omdb - {strurl}")
    try:
        title_info_json = urllib.request.urlopen(strurl).read()
        title_info = json.loads(title_info_json.decode())
        title_info['background_url'] = None
        app.logger.debug(f"omdb - {title_info}")
        if 'Error' in title_info or title_info['Response'] == "False":
            return None
    except urllib.error.HTTPError as error:
        app.logger.debug(f"omdb call failed with error - {error}")
        return None
    app.logger.debug("omdb - call was successful")
    return title_info


def get_omdb_poster(title=None, year=None, imdb_id=None, plot="short"):
    """ Queries OMDbapi.org for the poster for movie/show """
    omdb_api_key = cfg['OMDB_API_KEY']
    title_info = {}
    if imdb_id:
        strurl = f"https://www.omdbapi.com/?i={imdb_id}&plot={plot}&r=json&apikey={omdb_api_key}"
        strurl2 = ""
    elif title:
        strurl = f"https://www.omdbapi.com/?s={title}&y={year}&plot={plot}&r=json&apikey={omdb_api_key}"
        strurl2 = f"https://www.omdbapi.com/?t={title}&y={year}&plot={plot}&r=json&apikey={omdb_api_key}"
    else:
        app.logger.debug("no params")
        return None, None
    r = requests.utils.requote_uri(strurl)
    r2 = requests.utils.requote_uri(strurl2)
    try:
        title_info_json = urllib.request.urlopen(r).read()
    except Exception as error:
        app.logger.debug(f"Failed to reach OMdb - {error}")
        return None, None
    else:
        title_info = json.loads(title_info_json.decode())
        # app.logger.debug("omdb - " + str(title_info))
        if 'Error' not in title_info:
            return title_info['Search'][0]['Poster'], title_info['Search'][0]['imdbID']

        try:
            title_info_json2 = urllib.request.urlopen(r2).read()
            title_info2 = json.loads(title_info_json2.decode())
            # app.logger.debug("omdb - " + str(title_info2))
            if 'Error' not in title_info2:
                return title_info2['Poster'], title_info2['imdbID']
        except Exception as e:
            app.logger.debug(f"Failed to reach OMdb - {e}")
            return None, None

    return None, None


def get_tmdb_poster(search_query=None, year=None):
    """ Queries api.themoviedb.org for the poster/backdrop for movie """
    tmdb_api_key = cfg['TMDB_API_KEY']
    p, poster_base, response = tmdb_fetch_results(search_query, year, tmdb_api_key)
    # if status_code is in p we know there was an error
    if 'status_code' in p:
        app.logger.debug(f"get_tmdb_poster failed with error -  {p['status_message']}")
        return {}
    x = json.dumps(response.json(), indent=4, sort_keys=True)
    print(x)
    if p['total_results'] > 0:
        app.logger.debug(p['total_results'])
        for s in p['results']:
            if s['poster_path'] is not None and 'release_date' in s:
                x = re.sub(TMDB_YEAR_REGEX, "", s['release_date'])
                app.logger.debug(f"{s['title']} ({x})- {poster_base}{s['poster_path']}")
                s['poster_url'] = f"{poster_base}{s['poster_path']}"
                s["Plot"] = s['overview']
                # print(poster_url)
                s['background_url'] = f"{poster_base}{s['backdrop_path']}"
                s['Type'] = "movie"
                app.logger.debug(s['background_url'])
                return s
    else:
        url = f"https://api.themoviedb.org/3/search/tv?api_key={tmdb_api_key}&query={search_query}"
        response = requests.get(url)
        p = json.loads(response.text)
        v = json.dumps(response.json(), indent=4, sort_keys=True)
        app.logger.debug(v)
        x = {}
        if p['total_results'] > 0:
            app.logger.debug(p['total_results'])
            for s in p['results']:
                app.logger.debug(s)
                s['poster_path'] = s['poster_path'] if s['poster_path'] is not None else None
                s['release_date'] = '0000-00-00' if 'release_date' not in s else s['release_date']
                s['imdbID'] = tmdb_get_imdb(s['id'])
                s['Year'] = re.sub(TMDB_YEAR_REGEX, "", s['first_air_date']) if 'first_air_date' in s else \
                    re.sub(TMDB_YEAR_REGEX, "", s['release_date'])
                s['Title'] = s['title'] if 'title' in s else s['name']  # This isnt great
                s['Type'] = "movie"
                search_query_pretty = fix_post_plot(poster_base, s, search_query)
                if search_query_pretty.capitalize() == s['Title'].capitalize():
                    s['Search'] = s
                    app.logger.debug("x=" + str(x))
                    s['Response'] = True
                    return s
            x['Search'] = p['results']
            return x
        app.logger.debug("no results found")
        return None


def fix_post_plot(poster_base, s, search_query):
    app.logger.debug(f"{s['Title']} ({s['Year']})- {poster_base}{s['poster_path']}")
    s['Poster'] = f"{poster_base}{s['poster_path']}"  # print(poster_url)
    s['background_url'] = f"{poster_base}{s['backdrop_path']}"
    s["Plot"] = s['overview']
    app.logger.debug(s['background_url'])
    search_query_pretty = str.replace(r"\+", " ", search_query)
    app.logger.debug(f"trying {search_query.capitalize()} == {s['Title'].capitalize()}")
    return search_query_pretty


def tmdb_search(search_query=None, year=None):
    """
        Queries api.themoviedb.org for movies close to the query

    """
    tmdb_api_key = cfg['TMDB_API_KEY']
    p, poster_base, response = tmdb_fetch_results(search_query, year, tmdb_api_key)

    if 'status_code' in p:
        app.logger.debug(f"get_tmdb_poster failed with error -  {p['status_message']}")
        return None
    x = {}
    if p['total_results'] > 0:
        app.logger.debug(f"tmdb_search - found {p['total_results']} movies")
        for s in p['results']:
            s['poster_path'] = s['poster_path'] if s['poster_path'] is not None else None
            s['release_date'] = '0000-00-00' if 'release_date' not in s else s['release_date']
            s['imdbID'] = tmdb_get_imdb(s['id'])
            s['Year'] = re.sub(TMDB_YEAR_REGEX, "", s['release_date'])
            s['Title'] = s['title']
            s['Type'] = "movie"
            app.logger.debug(f"{s['title']} ({s['Year']})- {poster_base}{s['poster_path']}")
            s['Poster'] = f"{poster_base}{s['poster_path']}"
            s['background_url'] = f"{poster_base}{s['backdrop_path']}"
            app.logger.debug(s['background_url'])
        x['Search'] = p['results']
        return x
    else:
        # Search for tv series
        app.logger.debug("tmdb_search - movie not found, trying tv series ")
        url = f"https://api.themoviedb.org/3/search/tv?api_key={tmdb_api_key}&query={search_query}"
        response = requests.get(url)
        p = json.loads(response.text)
        x = {}
        if p['total_results'] > 0:
            app.logger.debug(p['total_results'])
            for s in p['results']:
                app.logger.debug(s)
                s['poster_path'] = s['poster_path'] if s['poster_path'] is not None else None
                s['release_date'] = '0000-00-00' if 'release_date' not in s else s['release_date']
                s['imdbID'] = tmdb_get_imdb(s['id'])
                s['Year'] = re.sub(TMDB_YEAR_REGEX, "", s['first_air_date']) if 'first_air_date' in s else \
                    re.sub(TMDB_YEAR_REGEX, "", s['release_date'])
                s['Title'] = s['title'] if 'title' in s else s['name']  # This isnt great
                s['Type'] = "series"
                fix_post_plot(poster_base, s, search_query)
            x['Search'] = p['results']
            return x

    # We got to here with no results give nothing back
    app.logger.debug("tmdb_search - no results found")
    return None


def tmdb_get_imdb(tmdb_id):
    """
        Queries api.themoviedb.org for imdb_id by TMDB id

    """
    # https://api.themoviedb.org/3/movie/78?api_key=
    # &append_to_response=alternative_titles,changes,credits,images,keywords,lists,releases,reviews,similar,videos
    tmdb_api_key = cfg['TMDB_API_KEY']
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={tmdb_api_key}&" \
          f"append_to_response=alternative_titles,credits,images,keywords,releases,reviews,similar,videos,external_ids"
    url_tv = f"https://api.themoviedb.org/3/tv/{tmdb_id}/external_ids?api_key={tmdb_api_key}"
    # Making a get request
    response = requests.get(url)
    search_results = json.loads(response.text)
    app.logger.debug(f"tmdb_get_imdb - {search_results}")
    # 'status_code' means id wasn't found
    if 'status_code' in search_results:
        # Try tv series
        response = requests.get(url_tv)
        tv = json.loads(response.text)
        app.logger.debug(tv)
        if 'status_code' not in tv:
            return tv['imdb_id']
    else:
        return search_results['external_ids']['imdb_id']


def tmdb_find(imdb_id):
    """
    basic function to return an object from TMDB from only the IMDB id
    :param imdb_id: the IMDB id to lookup
    :return: dict in the standard 'arm' format
    """
    tmdb_api_key = cfg['TMDB_API_KEY']
    url = f"https://api.themoviedb.org/3/find/{imdb_id}?api_key={tmdb_api_key}&external_source=imdb_id"
    poster_size = "original"
    poster_base = f"https://image.tmdb.org/t/p/{poster_size}"
    # Making a get request
    response = requests.get(url)
    search_results = json.loads(response.text)
    app.logger.debug(f"tmdb_find = {search_results}")
    if len(search_results['movie_results']) > 0:
        # We want to push out everything even if we dont use it right now, it may be used later.
        s = {'results': search_results['movie_results']}
        release_year = re.sub(TMDB_YEAR_REGEX, "", s['results'][0]['release_date'])
        # app.logger.debug(f"{s['results'][0]['title']} ({release_year})-{poster_base}{s['results'][0]['poster_path']}")
        s['poster_url'] = f"{poster_base}{s['results'][0]['poster_path']}"
        s["Plot"] = s['results'][0]['overview']
        s['background_url'] = f"{poster_base}{s['results'][0]['backdrop_path']}"
        s['Type'] = "movie"
        s['imdbID'] = imdb_id
        s['Poster'] = s['poster_url']
        s['Year'] = release_year
        s['Title'] = s['results'][0]['title']
    else:
        # We want to push out everything even if we dont use it right now, it may be used later.
        s = {'results': search_results['tv_results']}
        release_year = re.sub(TMDB_YEAR_REGEX, "", s['results'][0]['first_air_date'])
        # app.logger.debug(f"{s['results'][0]['name']} ({x})- {poster_base}{s['results'][0]['poster_path']}")
        s['poster_url'] = f"{poster_base}{s['results'][0]['poster_path']}"
        s["Plot"] = s['results'][0]['overview']
        s['background_url'] = f"{poster_base}{s['results'][0]['backdrop_path']}"
        s['imdbID'] = imdb_id
        s['Type'] = "series"
        s['Poster'] = s['poster_url']
        s['Year'] = release_year
        s['Title'] = s['results'][0]['name']
    return s


def validate_imdb(imdb_id):
    """
    Validate that the imdb id we got
    :param imdb_id:
    :return:
    """
    # ['tt', 'nm', 'co', 'ev', 'ch' or 'ni'] - 123456789
    # /ev\d{7}\/\d{4}(-\d)?|(ch|co|ev|nm|tt)\d{7}/
    # /^ev\d{7}\/\d{4}(-\d)?$|^(ch|co|ev|nm|tt)\d{7}$/
    ...


def tmdb_fetch_results(search_query, year, tmdb_api_key):
    """
    Main function for fetching results from TMDB\n\n
    :param str search_query: search query from ARMui
    :param str year: the year of the movie/tv-show
    :param str tmdb_api_key: tmdb API key
    :return tuple: [search_results dict, poster_img string, requests Response]
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
