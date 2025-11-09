from storages.backends.azure_storage import AzureStorage
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from decouple import config

# -----------------------------
# Local Storage (MEDIA_ROOT)
# -----------------------------
class LocalMediaStorage(FileSystemStorage):
    """
    Saves files to the local MEDIA_ROOT.
    """
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('location', settings.MEDIA_ROOT)
        kwargs.setdefault('base_url', settings.MEDIA_URL)
        super().__init__(*args, **kwargs)


# -----------------------------
# Azure Blob Storage
# -----------------------------
class AzureMediaStorage(AzureStorage):
    """
    Custom storage class for Azure Blob Storage.
    Reads settings from environment variables.
    """
    account_name = config('AZURE_STORAGE_ACCOUNT_NAME')
    account_key = config('AZURE_STORAGE_ACCOUNT_KEY')
    azure_container = config('AZURE_STORAGE_CONTAINER')
    
    # Ensure uploaded files are permanent and URLs do not expire
    expiration_secs = None
