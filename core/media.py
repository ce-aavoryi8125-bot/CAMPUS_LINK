"""
core/media.py
-------------
Secure media upload and image re-encoding pipeline for CampusLink 2.0.
Protects against:
- Malicious file uploads disguised as images (e.g. PHP/shell scripts renamed to .png)
- Embedded metadata/EXIF injection and polyglot payloads
- Directory traversal filenames (../../exploit.png)
- Decompression bombs / oversized image dimensions
- Truncated or malformed image streams
Uses Pillow (PIL 12.3.0) to decode pixel buffers and re-encode clean images to disk.
"""
import os
import io
import uuid
import base64
from typing import Tuple, Optional
from PIL import Image

from .config import PlatformConfig

# Magic Byte Signatures for Image Formats
MAGIC_SIGNATURES = {
    "png": b"\x89PNG\r\n\x1a\n",
    "jpeg": b"\xff\xd8\xff",
    "webp_riff": b"RIFF",
    "webp_tag": b"WEBP"
}

def verify_magic_bytes(data: bytes) -> bool:
    """Verifies that the byte stream starts with recognized image magic bytes."""
    if not data or len(data) < 12:
        return False
    if data.startswith(MAGIC_SIGNATURES["png"]):
        return True
    if data.startswith(MAGIC_SIGNATURES["jpeg"]):
        return True
    if data.startswith(MAGIC_SIGNATURES["webp_riff"]) and data[8:12] == MAGIC_SIGNATURES["webp_tag"]:
        return True
    return False

def process_and_reencode_image(
    file_bytes: bytes,
    target_dir: str,
    output_format: str = "PNG"
) -> Tuple[bool, str, Optional[str]]:
    """
    Sanitizes, strips EXIF, and re-encodes an image to permanent storage.
    
    Returns: (success: bool, relative_path_or_error: str, filename: Optional[str])
    """
    # 1. Check size limit
    if len(file_bytes) > PlatformConfig.MAX_UPLOAD_SIZE_BYTES:
        return False, f"File exceeds maximum allowed size of {PlatformConfig.MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB.", None

    # 2. Check magic bytes
    if not verify_magic_bytes(file_bytes):
        return False, "Invalid image format. Magic byte signature check failed.", None

    # 3. Decode and validate structure using Pillow
    try:
        stream = io.BytesIO(file_bytes)
        with Image.open(stream) as img:
            img.verify() # First pass structural verification
    except Exception as e:
        return False, f"Malformed or corrupted image byte stream: {str(e)}", None

    # 4. Reload image for sanitization & re-encoding (verify() closes stream)
    try:
        stream.seek(0)
        with Image.open(stream) as img:
            # Check dimensions against decompression bomb
            width, height = img.size
            if width > PlatformConfig.MAX_IMAGE_DIMENSION or height > PlatformConfig.MAX_IMAGE_DIMENSION:
                return False, f"Image dimensions ({width}x{height}) exceed maximum allowed {PlatformConfig.MAX_IMAGE_DIMENSION}px.", None

            # Convert to clean RGBA or RGB to strip all EXIF/metadata
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                clean_img = img.convert("RGBA")
                ext = "png"
                save_format = "PNG"
            else:
                clean_img = img.convert("RGB")
                ext = "jpg" if output_format.upper() in ("JPEG", "JPG") else "png"
                save_format = "JPEG" if ext == "jpg" else "PNG"

            # 5. Generate secure random UUID filename (prevents directory traversal)
            unique_name = f"item_{uuid.uuid4().hex[:12]}.{ext}"
            os.makedirs(target_dir, exist_ok=True)
            output_filepath = os.path.join(target_dir, unique_name)

            # 6. Re-encode pixel data to new file on disk
            clean_img.save(output_filepath, format=save_format, optimize=True)
            
            return True, f"assets/{unique_name}", unique_name

    except Exception as e:
        return False, f"Failed to re-encode image: {str(e)}", None

def decode_base64_image(image_data_str: str) -> Tuple[bool, Optional[bytes], Optional[str]]:
    """Decodes data URL base64 image strings safely."""
    try:
        if not image_data_str or not isinstance(image_data_str, str):
            return False, None, "Empty image data."
            
        if image_data_str.startswith("data:image"):
            parts = image_data_str.split(",", 1)
            if len(parts) == 2:
                raw_bytes = base64.b64decode(parts[1])
                return True, raw_bytes, None
                
        raw_bytes = base64.b64decode(image_data_str)
        return True, raw_bytes, None
    except Exception as e:
        return False, None, f"Invalid base64 encoding: {str(e)}"
