from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
from cloudfocus_project.custom_storage import AzureMediaStorage, LocalMediaStorage
import uuid

def handle_profile_picture_upload(image_file, min_size=(256, 256), use_azure=False):
    if not image_file:
        return None

    # Open image with Pillow
    img = Image.open(image_file)
    if img.width < min_size[0] or img.height < min_size[1]:
        img = img.resize(min_size, Image.ANTIALIAS)

    # Save image to memory
    buffer = BytesIO()
    img_format = img.format if img.format else 'PNG'
    
    # Create a unique filename
    ext = image_file.name.split('.')[-1]
    unique_name = f"profile_{uuid.uuid4().hex}.{ext}"
    
    img.save(buffer, format=img_format)
    file_content = ContentFile(buffer.getvalue(), name=unique_name)

    storage = AzureMediaStorage() if use_azure else LocalMediaStorage()
    saved_file_name = storage.save(unique_name, file_content)
    
    return saved_file_name