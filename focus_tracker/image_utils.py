from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
from cloudfocus_project.custom_storage import AzureMediaStorage, LocalMediaStorage

def handle_profile_picture_upload(image_file, min_size=(256, 256), use_azure=False):
    """
    Resize an uploaded profile picture to minimum size and save to chosen storage.
    
    Args:
        image_file: Uploaded file from form
        min_size: Minimum width and height (default 256x256)
        use_azure: Whether to save to Azure blob or local storage
    Returns:
        The saved image file name
    """
    if not image_file:
        return None

    # Open image with Pillow
    img = Image.open(image_file)

    # Resize if smaller than min_size
    if img.width < min_size[0] or img.height < min_size[1]:
        img = img.resize(min_size, Image.ANTIALIAS)

    # Save image to memory
    buffer = BytesIO()
    img_format = img.format if img.format else 'PNG'
    img.save(buffer, format=img_format)
    file_content = ContentFile(buffer.getvalue(), name=image_file.name)

    # Choose storage backend
    storage = AzureMediaStorage() if use_azure else LocalMediaStorage()
    
    # Save file to storage
    saved_file_name = storage.save(image_file.name, file_content)
    
    return saved_file_name
