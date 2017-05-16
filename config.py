# -*- coding: utf8 -*-
import os
basedir = os.path.abspath(os.path.dirname(__file__))

CSRF_ENABLED = False
SECRET_KEY = 'you-will-never-guess'

S3_BUCKET = 'outandaboutuserimages'
AWS_ACCESS_KEY = 'AKIAJNUMJZMGVEZHZZYQ'
AWS_SECRET_KEY = '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'

OPENID_PROVIDERS = [
    {'name': 'Google', 'url': 'https://www.google.com/accounts/o8/id'},
    {'name': 'Yahoo', 'url': 'https://me.yahoo.com'},
    {'name': 'AOL', 'url': 'http://openid.aol.com/<username>'},
    {'name': 'Flickr', 'url': 'http://www.flickr.com/<username>'},
    {'name': 'MyOpenID', 'url': 'https://www.myopenid.com'}]

SQLALCHEMY_DATABASE_URI = 'postgresql://sammy:button16@localhost/rideapp'
#SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_RECORD_QUERIES = True

WHOOSH_BASE = os.path.join(basedir, 'search.db')

DATABASE_QUERY_TIMEOUT = 0.5

# email server
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 465
MAIL_USE_TLS = False
MAIL_USE_SSL = True
MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

# available languages
LANGUAGES = {
    'en': 'English',
    'es': 'Español'
}

# microsoft translation service
MS_TRANSLATOR_CLIENT_ID = '' # enter your MS translator app id here
MS_TRANSLATOR_CLIENT_SECRET = '' # enter your MS translator app secret here

# administrator list
ADMINS = ['kevin.bradicich@gmail.com']

# pagination
POSTS_PER_PAGE = 50
MAX_SEARCH_RESULTS = 50