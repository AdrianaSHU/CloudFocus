"""
Django settings for cloudfocus_project project.
"""

from pathlib import Path
from decouple import config
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- (1) SECRET KEY ---
SECRET_KEY = config('SECRET_KEY')

# --- (2) DEBUG ---
# Reads 'DEBUG' from .env or Azure config. Defaults to False.
DEBUG = config('DEBUG', default=False, cast=bool)

# --- (3) ALLOWED HOSTS ---
# This tells your app which domains it's allowed to serve.
ALLOWED_HOSTS = [
    'cloudfocus-d8frducfd6fjgdbx.uksouth-01.azurewebsites.net', # Your Azure URL
    '127.0.0.1', # For local testing
    'localhost', # For local testing
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # My apps
    'focus_tracker.apps.FocusTrackerConfig',

    # Third-party apps
    'rest_framework',
    'storages',
]

# --- (4) MIDDLEWARE ---
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # Add WhiteNoise right after SecurityMiddleware
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cloudfocus_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'cloudfocus_project.wsgi.application'


# --- (5) DATABASE ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': '3306',
        'OPTIONS': {
            'ssl': {
                'ca': os.path.join(BASE_DIR, 'DigiCertGlobalRootG2.crt.pem')
            }
        }
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Europe/London'
USE_I18N = True
USE_TZ = True


# --- (6) STATIC FILES (CSS, JavaScript, Images) ---
# This is the setup for WhiteNoise (production static files)
STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
# This is the folder where 'collectstatic' will put all files
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles_build')
# This tells WhiteNoise to serve files from that folder
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- (7) EMAIL (SendGrid) ---
# This is your production email setup.
EMAIL_BACKEND = 'sendgrid_backend.SendgridBackend'
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

# Get credentials from .env file
SENDGRID_API_KEY = config('SENDGRID_API_KEY')
EMAIL_HOST_USER = config('EMAIL_HOST_USER') # This should be 'apikey'
EMAIL_HOST_PASSWORD = config('SENDGRID_API_KEY')
DEFAULT_FROM_EMAIL = config('YOUR_EMAIL_ADDRESS') # The email you verified with SendGrid

# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# --- (8) MEDIA / AZURE BLOB STORAGE ---
AZURE_ACCOUNT_NAME = config('AZURE_ACCOUNT_NAME')
AZURE_ACCOUNT_KEY = config('AZURE_ACCOUNT_KEY')
AZURE_CONTAINER = config('AZURE_CONTAINER')

AZURE_CUSTOM_DOMAIN = f'{AZURE_ACCOUNT_NAME}.blob.core.windows.net'
DEFAULT_FILE_STORAGE = 'storages.backends.azure_storage.AzureStorage'
MEDIA_URL = f'https://{AZURE_CUSTOM_DOMAIN}/{AZURE_CONTAINER}/'
AZURE_STORAGE_ACCOUNT_NAME = AZURE_ACCOUNT_NAME
AZURE_STORAGE_ACCOUNT_KEY = AZURE_ACCOUNT_KEY


# --- (9) SESSION & LOGIN SETTINGS (Unchanged) ---
SESSION_COOKIE_AGE = 60 * 10  # 600 seconds = 10 minutes
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True

LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

