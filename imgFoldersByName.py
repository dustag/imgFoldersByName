import os
from os import walk
import os.path
from os import path
import re
from datetime import datetime
import shutil
import time
import piexif

# sourcepath = r"C:/Users/Antoine/OneDrive/Images/Galerie Samsung/DCIM/Camera/"
sourcepath = r"C:/Users/Antoine/OneDrive/Images/Galerie Samsung/A classer/"
destpath = r"C:/Users/Antoine/OneDrive/Images/Galerie Samsung/Tri/"

new_date = datetime(2024, 7, 4)
for (dirpath, dirnames, filenames) in walk(sourcepath):
    for img in filenames:
        imgdir = ""
        imgdest = img
        m = re.search(r"(.*?)(\d{4})-(\d{2})-(\d{2})(.*)", img)  # Samsung S7
        if m is None:
            m = re.search(
                r"(.*?)(\d{4})(\d{2})(\d{2})(.*)", img
            )  # Samsung S10, S24 and Canon Powershot
            if m is None:
                m = re.search(r"(.*?)(\d{4})(\d{2})(\d{2})(.*)", img)  # Whatsapp
                if m is None:
                    try:
                        exif_dict = piexif.load(dirpath + "/" + img)
                        # print(exif_dict)
                        exif_date = str(exif_dict["0th"][piexif.ImageIFD.DateTime])[
                            2:12
                        ]
                        m2 = re.search(r"(\d{4}):(\d{2}):(\d{2})", exif_date)
                        imgdest = m2.group(1) + m2.group(2) + m2.group(3) + "_" + img
                        m = re.search(r"(.*?)(\d{4})(\d{2})(\d{2})(.*)", imgdest)
                    except:
                        path = dirpath + "/" + img
                        print(f"{path} is not an image")
                        # Not an image
                        continue

        if m is not None:
            print(img)
            try:
                if not path.exists(destpath + m.group(2) + "/"):
                    os.makedirs(destpath + m.group(2) + "/")
                if not path.exists(destpath + m.group(2) + "/" + m.group(3) + "/"):
                    os.makedirs(destpath + m.group(2) + "/" + m.group(3) + "/")
                imgdir = destpath + m.group(2) + "/" + m.group(3) + "/"
                new_date = datetime(
                    int(m.group(2)), int(m.group(3)), int(m.group(4)), 0, 0, 0
                )
                exif_dict = piexif.load(dirpath + "/" + img)
                # print(exif_dict)
                old_date = str(exif_dict["0th"][piexif.ImageIFD.DateTime])
                # print(old_date)
                if old_date[2:12] != new_date.strftime("%Y:%m:%d"):
                    imgdest = (
                        m.group(1) + old_date[2:12].replace(":", "") + m.group(5)
                    )
                    print("--> " + imgdest)

            except KeyError as ke:
                if ke.args[0] == 306:
                    # If exif date not present try to add it from filename date
                    exif_dict["0th"][piexif.ImageIFD.DateTime] = new_date.strftime(
                        "%Y:%m:%d %H:%M:%S"
                    )
                    exif_dict["Exif"][
                        piexif.ExifIFD.DateTimeOriginal
                    ] = new_date.strftime("%Y:%m:%d %H:%M:%S")
                    exif_dict["Exif"][
                        piexif.ExifIFD.DateTimeDigitized
                    ] = new_date.strftime("%Y:%m:%d %H:%M:%S")
                    exif_bytes = piexif.dump(exif_dict)
                    piexif.insert(exif_bytes, dirpath + "/" + img)
            except Exception as e:
                path = dirpath + "/" + img
                print(f"{path} is not an image: {e}")
                # Not an image
            finally:
                try:
                    os.rename(dirpath + "/" + img, imgdir + imgdest)
                except FileExistsError:
                    os.rename(
                        dirpath + img,
                        imgdir
                        + imgdest
                        + "-duplicate-"
                        + time.time().strftime("%m/%d/%Y, %H:%M:%S"),
                    )
    # If source directory is now empty, remove it
    if len(os.listdir(dirpath)) == 0:
        shutil.rmtree(dirpath)