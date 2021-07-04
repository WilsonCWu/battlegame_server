"""
Django settings for battlegame project.

Generated by 'django-admin startproject' using Django 3.0.4.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""

import os
from decouple import config
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
# TODO: consolidate this with DEVELOPMENT flag.
DEBUG = config('DEVELOPMENT', False)

SERVICE_ACCOUNT_FILE = '/home/battlegame/battlegame/.google-service-account.json'

DEVELOPMENT = config('DEVELOPMENT', False)

ALLOWED_HOSTS = ['salutationstudio.com', 'www.salutationstudio.com', 'localhost']
if DEVELOPMENT:
    ALLOWED_HOSTS += ['*']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'channels',
    'rest_framework',
    'rest_framework.authtoken',
    'django_json_widget',
    'django_extensions',
    'django_crontab',
    'django_better_admin_arrayfield',
    'django_prometheus',
    'bulk_admin',

    'chat',
    'playerdata',
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

ROOT_URLCONF = 'battlegame.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
               os.path.join(BASE_DIR, 'templates')
         ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'battlegame.wsgi.application'
ASGI_APPLICATION = "battlegame.routing.application"
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'battlegame',
        'USER': 'u_battlegame',
        'PASSWORD': config('POSTGRES_PASSWORD'),
        'HOST': 'localhost',
        'PORT': '',
    }
}

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = '/home/battlegame/staticfiles/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static/')
]


# Rest framework files
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
}


# Cron jobs.
# NOTE: for server performance, we should stagger our cron jobs so they don't
# all run at the same time.
CRONJOBS = [
    ('0 0 * * *', 'battlegame.cron.daily_quests_cron', '>> /tmp/daily_quest_job.log'),
    ('0 0 * * MON', 'battlegame.cron.weekly_quests_cron', '>> /tmp/weekly_quest_job.log'),

    ('0 0 * * *', 'battlegame.cron.daily_deals_cron', '>> /tmp/daily_deals_job.log'),

    ('0 5 * * *', 'battlegame.cron.daily_clean_matches_cron', '>> /tmp/daily_clean_matches.log'),
    ('0 0 * * *', 'battlegame.cron.reset_daily_wins_cron', '>> /tmp/reset_daily_wins_cron.log'),

    ('0 0 * * *', 'battlegame.cron.daily_dungeon_ticket_drop', '>> /tmp/daily_dungeon_ticket_drop.log'),
    ('0 0 * * 2,5', 'battlegame.cron.daily_dungeon_golden_ticket_drop', '>> /tmp/daily_dungeon_ticket_drop.log'),
    ('0 0 * * *', 'battlegame.cron.refresh_daily_dungeon', '>> /tmp/refresh_daily_dungeon.log'),

    # At 0 UTC on the 1st of every month
    ('0 0 1 * *', 'battlegame.cron.reset_season', '>> /tmp/reset_season.log'),

    # At 0 UTC on the 1st and 16th of every month
    ('0 0 1,16 * *', 'battlegame.cron.refresh_relic_shop', '>> /tmp/refresh_relic_shop.log')

    # ('0 16 * * THU', 'battlegame.cron.setup_tournament', '>> /tmp/setup_tournament_scheduled_job.log'),
    # ('0 16 * * 5-7', 'battlegame.cron.next_round', '>> /tmp/next_round_scheduled_job.log'),
    # ('5 16 * * TUE', 'battlegame.cron.end_tourney', '>> /tmp/end_tourney_scheduled_job.log')
]

# Monitoring
# Simply exposing metrics on :8000 gives us an incomplete view as there are 8
# workers per host (at the moment). See more at
# https://github.com/korfuri/django-prometheus/blob/master/documentation/exports.md#exporting-metrics-in-a-wsgi-application-with-multiple-processes-per-process.
if not DEVELOPMENT:
    PROMETHEUS_METRICS_EXPORT_PORT_RANGE = range(8001, 8009)
    PROMETHEUS_LATENCY_BUCKETS = (.05, .1, .15, .2, .25, .3, .35, .4, .45, .5, .6, .7, .8, .9, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0, float("inf"))

    sentry_sdk.init(
        dsn="https://d2e5bf5336d14219a7f067d70ffb7f9d@o474928.ingest.sentry.io/5512103",
        integrations=[DjangoIntegration()],
        traces_sample_rate=1.0,

        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True
    )

SHELL_PLUS_PRE_IMPORTS = [('battlegame.shell_settings', '*'),
                          ('battlegame.jobs', '*'),
                          ('battlegame.gameanalytics', '*')]
