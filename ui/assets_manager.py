import os
from PySide6.QtGui import QPixmap, QPixmapCache
from PySide6.QtCore import Qt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
PRODUCTS_DIR = os.path.join(ASSETS_DIR, "products")
ITEMS_DIR = os.path.join(ASSETS_DIR, "items")

_pixmap_memory_cache = {}

def get_logo_path():
    """Returns absolute path to logo image if exists."""
    logo_path = os.path.join(ASSETS_DIR, "logo.jpg")
    if os.path.exists(logo_path):
        return logo_path
    return None

def get_item_image_path(thumbnail_path, category_id=1, item_id=None):
    """
    Resolves product image path. Prioritizes semantic thumbnail_path in assets/products/.
    """
    # 1. Try stored thumbnail_path (Primary semantic path in assets/products/)
    if thumbnail_path and isinstance(thumbnail_path, str):
        full_path = thumbnail_path if os.path.isabs(thumbnail_path) else os.path.join(BASE_DIR, thumbnail_path)
        if os.path.exists(full_path):
            return full_path

    # 2. Try explicit item_id path in assets/items/
    if item_id:
        item_path = os.path.join(ITEMS_DIR, f"item_{item_id}.png")
        if os.path.exists(item_path):
            return item_path

    # 3. Category fallback
    cat_fallback = os.path.join(ITEMS_DIR, f"category_{category_id}.png")
    if os.path.exists(cat_fallback):
        return cat_fallback

    # 4. Generic fallback
    generic_fallback = os.path.join(ITEMS_DIR, "placeholder.png")
    if os.path.exists(generic_fallback):
        return generic_fallback

    return None

def get_cached_item_pixmap(thumbnail_path, category_id=1, item_id=None, width=360, height=210):
    """
    Returns scaled, aspect-ratio-preserved & cached QPixmap.
    Uses KeepAspectRatio so the ENTIRE product is always visible — no cropping.
    Padding is left around the image if aspect ratios differ (standard marketplace behaviour).
    """
    cache_key = f"{thumbnail_path}_{item_id}_{category_id}_{width}_{height}"
    if cache_key in _pixmap_memory_cache:
        return _pixmap_memory_cache[cache_key]

    img_path = get_item_image_path(thumbnail_path, category_id, item_id)
    if img_path and os.path.exists(img_path):
        pixmap = QPixmap(img_path)
        if not pixmap.isNull():
            # KeepAspectRatio: scale to fit inside width×height — never crops, never stretches
            scaled = pixmap.scaled(
                width, height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            _pixmap_memory_cache[cache_key] = scaled
            return scaled

    # Return dark placeholder pixmap if image cannot be loaded
    empty_pix = QPixmap(width, height)
    empty_pix.fill(Qt.GlobalColor.darkGray)
    return empty_pix
