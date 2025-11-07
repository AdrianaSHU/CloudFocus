from storages.backends.azure_storage import AzureStorage
from decouple import config

class AzureMediaStorage(AzureStorage):
    """
    This is a custom storage class for all user-uploaded media files.
    It reads its settings directly from the Azure environment variables.
    """
    # Read the 3 environment variables you set in the Azure App Service
    account_name = config('AZURE_STORAGE_ACCOUNT_NAME')
    account_key = config('AZURE_STORAGE_ACCOUNT_KEY')
    azure_container = config('AZURE_STORAGE_CONTAINER')
    
    # This ensures files are not auto-deleted and links do not expire
    expiration_secs = None
