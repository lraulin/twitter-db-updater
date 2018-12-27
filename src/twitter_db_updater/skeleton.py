#!/usr/bin/env python
# pylint: disable=wrong-import-position
# -*- coding: utf-8 -*-
"""
To run this script uncomment the following lines in the
[options.entry_points] section in setup.cfg:

    console_scripts =
         fibonacci = dbupdater.skeleton:run

Then run `python setup.py install` which will install the command `fibonacci`
inside your current environment.
"""

import argparse
import sys
import logging
import twitter
import pickle
import json
from inspect import getframeinfo, currentframe
from pathlib import Path
import psycopg2
import geocoder

# Ensure filepath for data files is in module directory regardless of cwd.
FILENAME = getframeinfo(currentframe()).filename
PARENT = Path(FILENAME).resolve().parent
INCIDENT_TYPE_FILE = PARENT / 'incidentTypes.json'
DB_FILE = PARENT / 'db.json'
CONFIG_FILE = PARENT / 'config.json'

incident_types = {}
tweets = {}
config = {}


def search_for_category():
    # initiate a twitter search for each category
    for key in incident_types:
        search_string = incident_types[key]['searchString']
        search_twitter(key, search_string)
    save_to_json(tweets, DB_FILE)


def search_twitter(incident_type, search_string):
    global tweets
    api = twitter.Api(config["CONSUMER_KEY"], config["CONSUMER_SECRET"],
                      config["ACCESS_TOKEN"], config["ACCESS_TOKEN_SECRET"])
    verified = r"filter:verified"
    raw_query = search_string.replace(' ', '') + verified
    results = api.GetSearch(raw_query)
    for tweet in results:
        print(tweet.user.verified)
        tweets[tweet.id] = tweet._json
        tweets[tweet.id]['incidentType'] = incident_type


def load_json(file):
    with open(file, 'r') as f:
        return json.load(f)


def save_to_json(data, file):
    with open(file, 'w') as f:
        json.dump(data, f)


def save_id_to_dab():
    sql = """
    INSERT INTO incidenttypes (id, displayname, searchstring, crisistype, regex)
    VALUES(%s);
    """

    conn = None
    try:
        # connect to the PostgreSQL database
        conn = psycopg2.connect(
            f"dbname='{config['dbName']}' user='{config['dbUser']}' password='{config['dbPassword']}'")
        # create a new cursor
        cur = conn.cursor()
        # create values list
        values_list = []
        for key, value in incident_types.items():
            values_list.append(
                (key, value['displayname'], value['searchstring'], value['crisistype'], value['regex']))
        # execute the INSERT statement
        psycopg2.extras.execute_values(cur, sql, values_list)
        # commit the changes to the database
        conn.commit()
        # close communication with the database
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()


def db_load():
    conn = psycopg2.connect(
        f"dbname='{config['dbName']}' user='{config['dbUser']}' password='{config['dbPassword']}'")


def saveToPosgres():
    sql = """
    INSERT INTO public.tweets(id, incidenttype, body, latitude, longitude, serialized)
    VALUES(%s)
    ON CONFLICT DO NOTHING;
    """

    sql2 = '''
    INSERT INTO tweets (id, incidenttype, body, latitude, longitude, serialized)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT DO NOTHING;
    '''

    conn = None
    try:
        # connect to the PostgreSQL database
        conn = psycopg2.connect(
            f"dbname='{config['dbName']}' user='{config['dbUser']}' password='{config['dbPassword']}'")
        # create a new cursor
        cur = conn.cursor()
        # test
        # cur.execute("SELECT * FROM incidenttypes;")
        # res = cur.fetchone(fetchone)
        # print(f'First row: {res}')
        # create values list
        values_list = []
        print(len(tweets))
        for key, value in tweets.items():
            print(key)
            print(value)
            lat = lng = None
            coords = value.get('coordinates')
            if coords:
                lat = coords['Latitude']
                lng = coords['Longitude']
            else:
                location = value['user']['location']
                g = geocoder.google(location, key=config['googleMapsApiKey'])
                lat = g.lat
                lng = g.lng
            # don't add this tweet if we can't get coordinates
            if (lat == None or lng == None):
                continue
            values = (key, value['incidentType'],
                      value['text'], lat, lng, json.dumps(value))
            values_list.append(values)
            cur.execute(sql2, values)
            conn.commit()
        # execute the INSERT statement
        # psycopg2.extras.execute_values(cur, sql, values_list)
        # commit the changes to the database
        conn.commit()
        # close communication with the database
        cur.close()
    except (Exception, psycopg2.DatabaseError) as e:
        print(f"Error: {e}")
    finally:
        if conn is not None:
            conn.close()


def main(args):
    print('Starting main')
    global config
    config = load_json(CONFIG_FILE)
    global incident_types
    incident_types = load_json(INCIDENT_TYPE_FILE)
    search_for_category()
    saveToPosgres()
    print('Done')


def run():
    """Entry point for console_scripts
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
