from io import BytesIO
from PIL import Image, ImageOps # Added ImageOps for EXIF orientation fix
from django.core.files.base import ContentFile
from django.conf import settings
import uuid
from cloudfocus_project.custom_storage import AzureMediaStorage, LocalMediaStorage

def handle_profile_picture_upload(image_file, max_size=(500, 500), use_azure=None):
    """
    Resizes an uploaded image to fit within max_size (default 500x500)
    before saving it to storage.
    """
    if not image_file:
        return None

    # 1. Auto-detect Environment
    if use_azure is None:
        use_azure = not settings.DEBUG 

    try:
        img = Image.open(image_file)
        
        # 2. Fix Orientation (Critical for phone photos!)
        # Phone cameras often save images rotated. This fixes it.
        img = ImageOps.exif_transpose(img)
        
        # 3. Convert to RGB (Fixes PNG/GIF transparency issues)
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # 4. FORCE RESIZE (Thumbnail)
        # This ensures the saved file is never larger than 500x500 pixels
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        # 5. Save to memory buffer as optimized JPEG
        buffer = BytesIO()
        unique_name = f"profile_pics/profile_{uuid.uuid4().hex}.jpg"
        
        # Quality=85 reduces file size significantly with no visible loss
        img.save(buffer, format='JPEG', quality=85) 
        file_content = ContentFile(buffer.getvalue(), name=unique_name)

        # 6. Save to Storage
        if use_azure:
            storage = AzureMediaStorage()
        else:
            storage = LocalMediaStorage()
            
        saved_file_name = storage.save(unique_name, file_content)
        return saved_file_name

    except Exception as e:
        print(f"Error in handle_profile_picture_upload: {e}")
        return None