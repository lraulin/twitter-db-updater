from inspect import getframeinfo, currentframe
from os.path import expanduser
from pathlib import Path

import pyrebase
import json

# Ensure filepath for data files is in module directory regardless of cwd.
FILENAME = getframeinfo(currentframe()).filename
PARENT = Path(FILENAME).resolve().parent
INCIDENT_TYPE_FILE = PARENT / 'incidentTypes.json'
DB_FILE = PARENT / 'db.json'
CONFIG_FILE = PARENT / 'config.json'
FIREBASE_ADMIN = PARENT / 'incident-report-map-firebase-adminsdk-rx0ey-6ec9058686.json'


def update_firebase(data):
    config = {}
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)

    # initialize connection
    firebase = pyrebase.initialize_app(config.firebase)
    db = firebase.database()

    # save data to firebase
    db.push(data)

def admin():
    import firebase_admin
    from firebase_admin import credentials

    cred = credentials.Certificate("path/to/serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
