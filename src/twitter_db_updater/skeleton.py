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
from psycopg2.extras import execute_values
import geocoder
from os.path import expanduser
from time import sleep
import pyrebase
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

# Ensure filepath for data files is in module directory regardless of cwd.
FILENAME = getframeinfo(currentframe()).filename
PARENT = Path(FILENAME).resolve().parent
INCIDENT_TYPE_FILE = PARENT / 'incidentTypes.json'
DB_FILE = PARENT / 'db.json'
CONFIG_FILE = PARENT / 'config.json'
JSON_SERVER_FILE = expanduser("~/Projects/twitter_map_react/db.json")
FIREBASE_ADMIN = PARENT / 'incident-report-map-firebase-adminsdk-rx0ey-6ec9058686.json'

incident_types = {}
tweets = {}
config = {}
fb_admin_config = {}


def create_conn():
    if (config == {}):
        print("Error: Config has not been loaded.")
        return
    else:
        return psycopg2.connect(
            f"dbname='{config['dbName']}' user='{config['dbUser']}' password='{config['dbPassword']}'")


def search_for_category():
    # initiate a twitter search for each category
    print("Searching for new Tweets...")
    for key in incident_types:
        search_string = incident_types[key]['searchString']
        search_twitter(key, search_string)
    print(f'{len(tweets.keys())} Tweets found')


def search_twitter(incident_type, search_string):
    global tweets
    api = twitter.Api(config["CONSUMER_KEY"], config["CONSUMER_SECRET"],
                      config["ACCESS_TOKEN"], config["ACCESS_TOKEN_SECRET"])
    verified = r"filter:verified"
    raw_query = search_string.replace(' ', '') + verified
    results = api.GetSearch(raw_query)
    for tweet in results:
        tweets[tweet.id] = tweet._json
        tweets[tweet.id]['incidentType'] = incident_type


def load_json(file):
    with open(file, 'r') as f:
        return json.load(f)


def save_to_json_server():
    print(f"Replacing JSON Server file at {JSON_SERVER_FILE}")
    json_server_data = {
        "posts": tweets,
        "comments": [
            {
                "id": 1,
                "body": "some comment",
                "postId": 1
            }
        ],
        "profile": {
            "name": "typicode"
        }
    }

    with open(JSON_SERVER_FILE, 'w') as f:
        json.dump(json_server_data, f)


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
    print("Loading Tweets from database...")
    global tweets
    tweets = {}

    conn = create_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, incidenttype, latitude, longitude, serialized FROM tweets;")
    rows = cur.fetchall()
    for row in rows:
        tweet = row[4]
        if (tweet["coordinates"] == None):
            tweet["coordinates"] = {
                "Latitude": row[2],
                "Longitude": row[3]
            }
        tweet["incidentType"] = row[1]
        tweets[tweet["id"]] = tweet
    pass


def saveToPosgres():
    print("Saving Tweets to database...")

    # For use with psycopg2.extras.execute_many.
    sql = """
    INSERT INTO public.tweets(id, incidenttype, latitude, longitude, serialized)
    VALUES %s
    ON CONFLICT DO NOTHING;
    """

    # For use with default execute.
    sql2 = '''
    INSERT INTO tweets (id, incidenttype, latitude, longitude, serialized)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT DO NOTHING;
    '''

    conn = None
    try:
        # connect to the PostgreSQL database
        conn = create_conn()
        # create a new cursor
        cur = conn.cursor()
        # test
        # cur.execute("SELECT * FROM incidenttypes;")
        # res = cur.fetchone(fetchone)
        # print(f'First row: {res}')
        # create values list
        values_list = []
        for key, value in tweets.items():
            lat = lng = None
            coords = value.get('coordinates')
            if coords:
                lat = coords['Latitude']
                lng = coords['Longitude']
            else:
                location = value['user']['location']
                if (location):
                    g = geocoder.google(location, key=config['googleMapsApiKey'])
                    lat = g.lat
                    lng = g.lng
                else:
                    # don't add this tweet if we can't get coordinates
                    continue
            values = (key, value['incidentType'],
                      lat, lng, json.dumps(value))
            values_list.append(values)
            # cur.execute(sql2, values)
            # conn.commit()
        # execute the INSERT statement
        print("Executing SQL")
        execute_values(cur, sql, values_list)
        # commit the changes to the database
        conn.commit()
        # close communication with the database
        cur.close()
    except (Exception, psycopg2.DatabaseError) as e:
        print(f"Error: {e}")
    finally:
        if conn is not None:
            conn.close()


def countdown(seconds):
    while (seconds >= 0):
        print(f"Restarting in {seconds} seconds; Press Ctrl-C to abort",
              end='\r', flush=True)
        seconds -= 1
        sleep(1)


def update_firebase(data):
    print("Pushing to Firebase...")
    import firebase_admin
    from firebase_admin import credentials

    # Fetch the service account key JSON file contents
    try:
        cred = credentials.Certificate(fb_admin_config)

        # Initialize the app with a service account, granting admin privileges
        firebase_admin.initialize_app(cred, {
            'databaseURL': "https://incident-report-map.firebaseio.com"
        })
    except ValueError:
        # The connection has already been initialized
        pass

    # As an admin, the app has access to read and write all data, regradless of Security Rules
    ref = db.reference('tweets')
    print(ref.get())

    # Push data
    ref.update(tweets)



def load_config():
    global config
    config = load_json(CONFIG_FILE)
    config['firebase']['serviceAccount'] = FIREBASE_ADMIN
    global incident_types
    incident_types = load_json(INCIDENT_TYPE_FILE)
    global fb_admin_config
    fb_admin_config = load_json(FIREBASE_ADMIN)



def main(args):
    while True:
        print('Starting main')
        load_config()
        search_for_category()
        saveToPosgres()
        print('Done')
        db_load()
        save_to_json_server()
        update_firebase(tweets)
        countdown((120))


def run():
    """Entry point for console_scripts
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
