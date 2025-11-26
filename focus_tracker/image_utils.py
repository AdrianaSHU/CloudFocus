from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
from django.conf import settings # Import settings to check DEBUG/Production
import uuid

# Import your storage classes
from cloudfocus_project.custom_storage import AzureMediaStorage, LocalMediaStorage

def handle_profile_picture_upload(image_file, min_size=(256, 256), use_azure=None):
    if not image_file:
        return None

    # --- 1. Auto-detect Environment if not specified ---
    # If use_azure is not passed, decide based on DEBUG setting
    if use_azure is None:
        # If DEBUG is False (Production), use Azure. Otherwise Local.
        use_azure = not settings.DEBUG 

    # --- 2. Process Image ---
    try:
        img = Image.open(image_file)
        
        # Handle Palette mode (like GIFs) which can't be resized easily
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Resize if needed
        # Fix for Pillow 10+: ANTIALIAS is deprecated, use Resampling.LANCZOS
        if img.width < min_size[0] or img.height < min_size[1]:
            try:
                resample_filter = Image.Resampling.LANCZOS
            except AttributeError:
                # Fallback for older Pillow versions
                resample_filter = Image.ANTIALIAS 
            img = img.resize(min_size, resample_filter)

        # Save image to memory buffer
        buffer = BytesIO()
        img_format = 'JPEG' # Standardize on JPEG for consistency
        
        # Generate unique filename
        ext = 'jpg'
        unique_name = f"profile_pics/profile_{uuid.uuid4().hex}.{ext}"
        
        img.save(buffer, format=img_format, quality=85) # Compress slightly
        file_content = ContentFile(buffer.getvalue(), name=unique_name)

        # --- 3. Save to Correct Storage ---
        if use_azure:
            storage = AzureMediaStorage()
        else:
            storage = LocalMediaStorage()
            
        # storage.save returns the name of the file as saved
        saved_file_name = storage.save(unique_name, file_content)
        
        return saved_file_name

    except Exception as e:
        print(f"Error in handle_profile_picture_upload: {e}")
        return None