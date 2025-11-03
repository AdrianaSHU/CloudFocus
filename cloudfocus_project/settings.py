"""
Django settings for cloudfocus_project project.
FINAL - Production Ready
"""

from pathlib import Path
from decouple import config
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- (1) CORE DJANGO SETTINGS ---
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)

# Add your Azure URL here.
ALLOWED_HOSTS = [
    'cloudfocus-d8frducfd6fjgdbx.uksouth-01.azurewebsites.net',
    '127.0.0.1',
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'focus_tracker.apps.FocusTrackerConfig',
    'rest_framework',
    'storages', # For Azure Blob Storage
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # For static files
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


# --- (2) DATABASE (Azure MySQL) ---
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

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# --- (3) STATIC FILES (For CSS/JS - Handled by WhiteNoise) ---
STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles_build')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# --- (4) MEDIA FILES (For User Uploads - Handled by Azure Blob Storage) ---

# Read Blob Storage credentials from Azure config
AZURE_ACCOUNT_NAME = config('AZURE_ACCOUNT_NAME')
AZURE_ACCOUNT_KEY = config('AZURE_ACCOUNT_KEY')
AZURE_CONTAINER = config('AZURE_CONTAINER')

# This is the storage backend Django will use for all user uploads.
DEFAULT_FILE_STORAGE = 'storages.backends.azure_storage.AzureStorage'

# This is the base URL for media files.
# Your model's 'upload_to' (e.g., 'profile_pics/') will be appended to this.
MEDIA_URL = f'https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net/{AZURE_CONTAINER}/'

# These settings are required by django-storages
AZURE_STORAGE_ACCOUNT_NAME = AZURE_ACCOUNT_NAME
AZURE_STORAGE_ACCOUNT_KEY = AZURE_ACCOUNT_KEY


# --- (5) EMAIL (SendGrid) ---
EMAIL_BACKEND = 'sendgrid_backend.SendgridBackend'
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
SENDGRID_API_KEY = config('SENDGRID_API_KEY')
EMAIL_HOST_USER = config('EMAIL_HOST_USER') # This should be 'apikey'
EMAIL_HOST_PASSWORD = config('SENDGRID_API_KEY')
DEFAULT_FROM_EMAIL = config('YOUR_EMAIL_ADDRESS')


# --- (6) SESSION & LOGIN SETTINGS ---
SESSION_COOKIE_AGE = 60 * 10  # 10 minutes
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True

LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'


# --- (7) FINAL AZURE PROXY/CSRF FIX ---
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'httpsClick here to go to Environment Variables menu')
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
