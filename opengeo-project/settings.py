"""
Django settings for opengeo-project project.

Generated by 'django-admin startproject' using Django 3.1.5.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

from pathlib import Path

import django_filters.rest_framework
# Build paths inside the project like this: BASE_DIR / 'subdir'.
import yaml
from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parent.parent

with (BASE_DIR / "config" / "config.yml").open("r") as config:
    LOADED_CONFIG = yaml.load(config, yaml.FullLoader)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = LOADED_CONFIG["SECRET_KEY"]

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = LOADED_CONFIG["DEBUG"]

ALLOWED_HOSTS = LOADED_CONFIG["ALLOWED_HOSTS"]

# Application definition

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'opengeo.apps.OpenGeoConfig',
    'rest_framework',
    "channels",
    'leaflet',
    "drf_spectacular",
    "django_filters",
    "mathfilters",
    'corsheaders',
    "graphene_django",
    'schema_graph',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'opengeo.middleware.GraphQlAuthenticationStatusCodeMiddleware',
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'opengeo-project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'opengeo-project.wsgi.application'

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = LOADED_CONFIG["DATABASES"]

# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Admin settings
ADMIN_ENABLED = False

if ADMIN_ENABLED is True:
    INSTALLED_APPS.append('django.contrib.admin')

# DRF settings

REST_FRAMEWORK = {
    # YOUR SETTINGS
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend']
}

SECURE_CONTENT_TYPE_NOSNIFF = False
SECURE_REFERRER_POLICY = "origin"

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/
# Used from GraphiQL

STATIC_URL = '/static/'
STATIC_ROOT = 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / "static"
]

# Graphene settings

GRAPHENE = {
    'SCHEMA_INDENT': 4,
    "SCHEMA": "opengeo.schema.schema.schema",
    'MIDDLEWARE': [
        'graphene_django_extras.ExtraGraphQLDirectiveMiddleware',
        'graphql_jwt.middleware.JSONWebTokenMiddleware',
    ]
}

# Extras library

GRAPHENE_DJANGO_EXTRAS = {
    'DEFAULT_PAGINATION_CLASS': 'graphene_django_extras.paginations.LimitOffsetGraphqlPagination',
    'DEFAULT_PAGE_SIZE': 30,
    'MAX_PAGE_SIZE': 100,
    'CACHE_ACTIVE': True,
    'CACHE_TIMEOUT': 300  # seconds
}

# Authentication user model

AUTH_USER_MODEL = "opengeo.PlayerModel"

AUTHENTICATION_BACKENDS = [
    'graphql_jwt.backends.JSONWebTokenBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Channels settings (for subscriptions)

CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
ASGI_APPLICATION = "opengeo.asgi.application"

# CORS settings

CORS_ALLOW_HEADERS = default_headers + (
    'Access-Control-Allow-Origin',
)
CSRF_COOKIE_SECURE = False
CORS_ALLOW_CREDENTIALS = True
# TODO \/
CORS_ORIGIN_WHITELIST = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
    "http://localhost:8000"
]

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname} | pid {process:d} | tid {thread:d}] {asctime} - {message} | mod. {module}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {asctime} - {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'console-production': {
            'level': 'INFO',
            'filters': ['require_debug_false'],
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'console-production'],
            'propagate': True,
            'level': 'INFO'
        },
        'django.server': {
            'handlers': ['console'],
            'propagate': False,
            'level': 'INFO'
        },
        'opengeo': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'DEBUG',
        }
    }
}
