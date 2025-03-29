import os
import re
import argparse
import piexif
import shutil
import json
from datetime import datetime
from pathlib import Path
from PIL import Image
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from collections import defaultdict
import subprocess
import time

IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.heic')
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.avi', '.mkv')
DATE_REGEXES = [
    re.compile(r"(.*?)(\d{4})-(\d{2})-(\d{2})(.*)"),   # Samsung S7
    re.compile(r"(.*?)(\d{4})(\d{2})(\d{2})(.*)"),     # Samsung S10, S24, Canon, WhatsApp
]

geolocator = Nominatim(user_agent="photo-organizer")

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", nargs="?", default="C:\\Users\\Antoine\\OneDrive\\Images\\Galerie Samsung\\ATrier")
    parser.add_argument("dest", nargs="?", default="C:\\Users\\Antoine\\OneDrive\\Images\\Galerie Samsung\\Trie")
    parser.add_argument("-m", "--move", action="store_true", help="Moving files instead of copying")
    return parser.parse_args()

def get_decimal_from_dms(dms, ref):
    degrees = dms[0][0] / dms[0][1]
    minutes = dms[1][0] / dms[1][1]
    seconds = dms[2][0] / dms[2][1]
    sign = -1 if ref in ['S', 'W'] else 1
    return sign * (degrees + minutes / 60 + seconds / 3600)

def extract_image_metadata(path):
    try:
        exif_dict = piexif.load(path)
        gps = exif_dict.get("GPS", {})
        date = exif_dict["Exif"].get(piexif.ExifIFD.DateTimeOriginal)
        if date:
            date = date.decode("utf-8")
        coords = None
        if piexif.GPSIFD.GPSLatitude in gps:
            lat = get_decimal_from_dms(gps[piexif.GPSIFD.GPSLatitude], gps[piexif.GPSIFD.GPSLatitudeRef].decode())
            lon = get_decimal_from_dms(gps[piexif.GPSIFD.GPSLongitude], gps[piexif.GPSIFD.GPSLongitudeRef].decode())
            coords = (lat, lon)
        return date, coords
    except Exception:
        return None, None

def extract_video_metadata(path):
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_format', '-show_streams',
            str(path)
        ], capture_output=True, text=True)
        metadata = json.loads(result.stdout)
        tags = metadata.get("format", {}).get("tags", {})
        date_str = tags.get("creation_time")
        if date_str:
            try:
                date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                date = date.strftime("%Y:%m:%d %H:%M:%S")
            except Exception:
                date = None
        else:
            date = None
        return date, None
    except Exception:
        return None, None

def extract_date_from_filename(filename):
    filename = Path(filename).stem  # supprime l’extension
    for regex in DATE_REGEXES:
        match = regex.match(filename)
        if match:
            y, m, d = match.group(2), match.group(3), match.group(4)
            rest = match.group(5)
            # Cherche une heure dans la suite du nom
            hour_match = re.search(r"(\d{2})[.:_]?(\d{2})[.:_]?(\d{2})", rest)
            if hour_match:
                hh, mm, ss = hour_match.groups()
                return f"{y}:{m}:{d} {hh}:{mm}:{ss}"
            else:
                return f"{y}:{m}:{d} 00:00:00"
    return None

def merge_date_and_time(date_str, fallback_time="00:00:00"):
    if " " in date_str:
        return date_str
    return f"{date_str} {fallback_time}"

def update_exif_date(path, new_date):
    try:
        exif_dict = piexif.load(path)
        new_bytes = new_date.encode('utf-8')
        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = new_bytes
        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, path)
    except Exception as e:
        print(f"EXIF update error: {path} → {e}")

def get_place_name(coord):
    try:
        time.sleep(1.1)
        location = geolocator.reverse(coord, exactly_one=True, language='en')
        if location:
            address_parts = location.raw.get('address', {})
            place_name = " - ".join([
                address_parts.get('tourism') or address_parts.get('isolated_dwelling') or address_parts.get('locality') or address_parts.get('hamlet') or address_parts.get('road', ''),
                address_parts.get('village') or address_parts.get('town') or address_parts.get('city', ''),
                address_parts.get('state', ''),
                address_parts.get('country', '')
            ])
            return place_name
    except:
        pass
    return ""

def cluster_by_location(files, max_dist_km=25):
    clusters = []
    for file in files:
        placed = False
        for cluster in clusters:
            if file['coords'] and cluster['center']:
                dist = geodesic(file['coords'], cluster['center']).km
                if dist <= max_dist_km:
                    cluster['files'].append(file)
                    placed = True
                    break
        if not placed:
            clusters.append({'center': file['coords'], 'files': [file]})
    return clusters

def save_file(full_path, target, move=False):
    """Saves a file to the target location, avoiding duplicates"""
    base, ext = os.path.splitext(target)
    counter = 1
    
    file_name = os.path.basename(full_path)  # Retrieves the file name only

    while os.path.exists(target):
        target = f"{base} - dup {counter}{ext}"
        counter += 1

    try:
        if move:
            shutil.move(full_path, target)
            print(f"Moved : {file_name} → {target}")
        else:
            shutil.copy2(full_path, target)
            print(f"Copy : {file_name} → {target}")
    except Exception as e:
        print(f"Error when copying/moving {full_path} : {e}")


def organize_files(source, dest, move=False):
    if move:
        print(f"Move requested from {source} to {dest}")
    else:
        print(f"Copy requested from {source} to {dest}")
    
    files_data = []
    last_root = None
    for root, _, files in os.walk(source):
        if root != last_root:  # Displays only if the file has changed
            print(f"📂 Walking in: {root}")
            last_root = root
            
        for name in files:
            ext = name.lower().endswith
            full_path = os.path.join(root, name)
            if ext(IMAGE_EXTENSIONS):
                date, coords = extract_image_metadata(full_path)
            elif ext(VIDEO_EXTENSIONS):
                date, coords = extract_video_metadata(full_path)
            else:
                continue

            date_from_name = extract_date_from_filename(name)
            if date:
                date = merge_date_and_time(date)
            if date_from_name:
                date_from_name = merge_date_and_time(date_from_name)

            if date and date_from_name:
                if date.split(" ")[0] != date_from_name.split(" ")[0]:
                    print(f"Date correction for {name}")
                    update_exif_date(full_path, date_from_name)
                    date = date_from_name
            elif not date:
                date = date_from_name

            if not date:
                print(f"Date not found for {name}")
                continue

            files_data.append({
                'path': full_path,
                'date': datetime.strptime(date, "%Y:%m:%d %H:%M:%S"),
                'coords': coords
            })

    date_groups = defaultdict(list)
    for f in files_data:
        key = f['date'].strftime("%Y-%m-%d")
        date_groups[key].append(f)

    for date_str, files in date_groups.items():
        year = files[0]['date'].strftime("%Y")
        clusters = cluster_by_location(files)
        for i, cluster in enumerate(clusters):
            location = get_place_name(cluster['center']) if cluster['center'] else ""
            clean_location = ""
            if len(location)>0:
                clean_location = f" - {location.replace("/", "_")}"
            folder = Path(dest) / year / f"{date_str}{clean_location}"
            folder.mkdir(parents=True, exist_ok=True)

            for f in cluster['files']:
                target = folder / Path(f['path']).name
                save_file(f['path'], target, move=move)

if __name__ == "__main__":
    args = parse_args()
    organize_files(args.source, args.dest, move=args.move)
