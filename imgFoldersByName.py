import os
from os import walk
import os.path
from os import path
import re

mypath = r"C:/Users/Antoine/OneDrive/Images/Galerie Samsung/A classer/"

f=[]
for (dirpath, dirnames, filenames) in walk(mypath):
    f.extend(filenames)
    break

for img in f:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", img)
    if m is not None:
        imgdir = mypath + m.group(1) + "/"
        if not path.exists(imgdir):
            os.makedirs(imgdir)
        os.rename(mypath + img, imgdir + img)



