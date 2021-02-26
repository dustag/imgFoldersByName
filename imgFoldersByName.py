import os
from os import walk
import os.path
from os import path
import re
from datetime import datetime
import time
import piexif

sourcepath = r"C:/Users/Antoine/OneDrive/Images/Galerie Samsung/DCIM/Camera/"
destpath = r"C:/Users/Antoine/OneDrive/Images/Galerie Samsung/A classer/"

f=[]
for (dirpath, dirnames, filenames) in walk(sourcepath):
    f.extend(filenames)
    break

new_date = datetime(2021, 2, 26)
for img in f:
    imgdir = ""
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", img)              # Samsung S7
    if m is not None:
        imgdir = destpath + m.group(1) + "-" + m.group(2) + "-" + m.group(3) + "/"
        new_date = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), 0, 0, 0)
    else:
        m = re.search(r"(\d{4})(\d{2})(\d{2})", img)            # Samsung S10
        if m is not None:
            imgdir = destpath + m.group(1) + "-" + m.group(2) + "-" + m.group(3) + "/"
            new_date = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), 0, 0, 0)
        else:
            m = re.search(r"IMG-(\d{4})(\d{2})(\d{2})", img)    # Whatsapp
            if m is not None:
                imgdir = destpath + m.group(1) + "-" + m.group(2) + "-" + m.group(3) + "/"
                new_date = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), 0, 0, 0)
    if imgdir != "":
        if not path.exists(imgdir):
            os.makedirs(imgdir)
        print(img)
        try:
            exif_dict = piexif.load(sourcepath + img)
            #print(exif_dict)
            old_date = str(exif_dict['0th'][piexif.ImageIFD.DateTime])
            #print(old_date)
            if old_date[2:12] != new_date.strftime("%Y:%m:%d"):
                exif_dict['0th'][piexif.ImageIFD.DateTime] = new_date.strftime("%Y:%m:%d %H:%M:%S")
                exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = new_date.strftime("%Y:%m:%d %H:%M:%S")
                exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = new_date.strftime("%Y:%m:%d %H:%M:%S")
                exif_bytes = piexif.dump(exif_dict)
                piexif.insert(exif_bytes, sourcepath + img)
        except:
            print("Not an image")
            # Not an image
        finally :
            try:
                os.rename(sourcepath + img, imgdir + img)
            except FileExistsError:
                os.rename(sourcepath + img, imgdir + img + "-duplicate-" + time.time().strftime("%m/%d/%Y, %H:%M:%S"))


