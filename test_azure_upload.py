# test_azure_upload.py
import django
import os
from django.core.files.base import ContentFile
from cloudfocus_project.custom_storage import AzureMediaStorage
from decouple import config

# --- Setup Django environment ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloudfocus_project.settings')
django.setup()

# --- Initialize Azure Storage ---
storage = AzureMediaStorage()

# --- Create a test file ---
file_name = 'test_upload.png'
file_content = b'Hello Azure! This is a test image.'
content_file = ContentFile(file_content, name=file_name)

# --- Save file to Azure ---
try:
    saved_name = storage.save(file_name, content_file)
    print(f"File successfully uploaded to Azure: {saved_name}")
    print(f"Access URL: {storage.url(saved_name)}")
except Exception as e:
    print(f"Upload failed: {e}")
