"""
CitiZen AI — GPS and Geocoding Utilities
Extract GPS from EXIF, geocode addresses, hash images, calculate distances.
"""
import hashlib
import math
import requests
from PIL import Image, ExifTags


def extract_gps_from_image(image_path):
    """Extract GPS coordinates from image EXIF data."""
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
        if not exif_data:
            return None, None
        gps_info = {}
        for tag_id, value in exif_data.items():
            tag = ExifTags.TAGS.get(tag_id, tag_id)
            if tag == "GPSInfo":
                for gps_tag_id, gps_value in value.items():
                    gps_tag = ExifTags.GPSTAGS.get(gps_tag_id, gps_tag_id)
                    gps_info[gps_tag] = gps_value
        if not gps_info:
            return None, None
        lat = _convert_to_decimal(
            gps_info.get('GPSLatitude'),
            gps_info.get('GPSLatitudeRef')
        )
        lon = _convert_to_decimal(
            gps_info.get('GPSLongitude'),
            gps_info.get('GPSLongitudeRef')
        )
        return lat, lon
    except Exception:
        return None, None


def _convert_to_decimal(dms, direction):
    """Convert GPS DMS (degrees, minutes, seconds) to decimal degrees."""
    if not dms:
        return None
    try:
        d = float(dms[0])
        m = float(dms[1])
        s = float(dms[2])
        decimal = d + m / 60 + s / 3600
        if direction in ['S', 'W']:
            decimal = -decimal
        return decimal
    except Exception:
        return None


def geocode_address(address):
    """Convert address to lat/lon using Nominatim (free, no API key)."""
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": address + ", India",
            "format": "json",
            "limit": 1,
            "addressdetails": 1
        }
        headers = {"User-Agent": "CitiZenAI-Hackathon/1.0"}
        response = requests.get(url, params=params, headers=headers, timeout=5)
        data = response.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
        return None, None
    except Exception:
        return None, None


def get_image_hash(image_path):
    """Generate MD5 hash of image for duplicate detection."""
    try:
        with open(image_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return None


def get_image_hash_from_bytes(image_bytes):
    """Generate MD5 hash from image bytes."""
    try:
        return hashlib.md5(image_bytes).hexdigest()
    except Exception:
        return None


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in meters between two GPS coordinates."""
    R = 6371000  # Earth's radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))
