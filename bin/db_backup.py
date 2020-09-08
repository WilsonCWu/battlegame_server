#!/usr/bin/env python3
import subprocess
import time

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

def authenticate(cred_file):
    gauth = GoogleAuth()
    gauth.LoadCredentialsFile(cred_file)
    if gauth.credentials is None:
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        gauth.Refresh()
    else:
        gauth.Authorize()

    gauth.SaveCredentialsFile(cred_file)
    return gauth

def dump_database():
    subprocess.run(['./manage.py dumpdata --exclude auth.permission --exclude contenttypes > db.json'], shell=True)

def upload_file(auth, file_name, file):
    drive = GoogleDrive(auth)

    upload = drive.CreateFile({'title': file_name})
    upload.SetContentFile(file)
    upload.Upload()
    drive.CreateFile({'id':upload['id']}).GetContentFile(file)

if __name__ == "__main__":
    auth = authenticate('.gdrive_auth')
    dump_database()
    upload_file(auth, 'db_%s.json' % str(int(time.time())), 'db.json')
