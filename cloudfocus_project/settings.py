"""
Django settings for cloudfocus_project project.
FINAL - Dual-Mode (Production & Local)
"""

from pathlib import Path
from decouple import config
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- (1) CORE DJANGO SETTINGS ---
SECRET_KEY = config('SECRET_KEY')

# DEBUG is now the master switch for our settings!
DEBUG = config('DEBUG', default=False, cast=bool)

# Add your Azure URL here.
ALLOWED_HOSTS = [
    'cloudfocus-d8frducfd6fjgdbx.uksouth-01.azurewebsites.net',
    '127.0.0.1',
    '10.0.0.22', # Your VM's local IP
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
    'axes', # For brute force security
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # For static files
    'axes.middleware.AxesMiddleware', # For brute force 
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


# --- (2) DUAL-MODE SETTINGS (DATABASE, MEDIA, EMAIL) ---

if DEBUG:
    # --- LOCAL DEVELOPMENT SETTINGS ---
    print("Running in LOCAL DEBUG mode")
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

else:
    # --- PRODUCTION (AZURE) SETTINGS ---
    print("Running in PRODUCTION mode")
    
    # Use Azure MySQL Database
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
    
    # Use our new custom Azure Storage class
    DEFAULT_FILE_STORAGE = 'cloudfocus_project.custom_storage.AzureMediaStorage'
    
    # Build the MEDIA_URL
    MEDIA_URL = f"https://{config('AZURE_STORAGE_ACCOUNT_NAME')}.blob.core.windows.net/{config('AZURE_STORAGE_CONTAINER')}/"
    
    # Use SendGrid for emails
    EMAIL_BACKEND = 'sendgrid_backend.SendgridBackend'
    EMAIL_HOST = 'smtp.sendgrid.net'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    SENDGRID_API_KEY = config('SENDGRID_API_KEY')
    EMAIL_HOST_USER = config('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = config('SENDGRID_API_KEY')
    DEFAULT_FROM_EMAIL = config('YOUR_EMAIL_ADDRESS')
    
    # Production-only security settings
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True


# --- (3) STATIC FILES (Same for both) ---
STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles_build')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# --- (4) OTHER SETTINGS (Same for both) ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Europe/London'
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SESSION_COOKIE_AGE = 60 * 10
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True

LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

