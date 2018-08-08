"""
    must git submodule init and git submodule update -r 

    also watch out for: https://github.com/mdhiggins/sickbeard_mp4_automator/issues/643

"""

import argparse 
import os 
import subprocess 
import time 
import shutil
import random
import string 

parser = argparse.ArgumentParser(description='Running post-processing on media files')
parser.add_argument('media_dir', help="the location of the media files")
parser.add_argument('--delete', action="store_true")
parser.add_argument('--interval', default=-1, type=int, help="the repeat interval, -1 to disable (default)")
args = parser.parse_args()

script_location = os.path.dirname(__file__)
temp_dir = os.path.join(script_location, "_temp_")

def scan_directory(directory):
    files = []
    for file in os.listdir(directory):
        if file == "." or file == "..": continue 
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path):
            yield file_path 
        else:
            yield from scan_directory(file_path)

if os.path.exists(temp_dir):
    shutil.rmtree(temp_dir)
os.mkdir(temp_dir)

def get_temp_dir():
    loc = os.path.join(temp_dir, ''.join(random.choices(string.ascii_uppercase + string.digits, k=64)))
    os.mkdir(loc)
    return loc

os.nice(19)

print("running post-processing.py")
extensions_to_transcode = [
    ".flv",
    ".avi",
    ".mkv",
    ".wmv",
    ".mov",
    ".m4v",
]

if os.path.exists(os.path.join(script_location, "blacklist.txt")):
    with open(os.path.join(script_location, "blacklist.txt"), "r") as f:
        blacklist = set(f.read().split("\n"))
else:
    blacklist = set()

while True:
    print("scanning files...")
    files = list(scan_directory(args.media_dir))
    file_set = set(files)
    print("built directory list... %d files detected... now transcoding if needed." % (len(files)))

    for file in files:
        basename, ext = os.path.splitext(file)

        if file in blacklist: 
            print("skipping %s because it is BLACKLISTED" % file)
            continue 

        if ext not in extensions_to_transcode: continue 
        output_name = basename + ".mp4"
        if output_name in file_set: continue 
        
        print("found file %s which needs transcoding to mp4" % file)

        temp_location = get_temp_dir()
        print("\tcreated a temporary directory: %s" % temp_location)

        pargs = ["python"]
        pargs += [os.path.join(script_location, "./sickbeard_mp4_automator/manual.py")]
        pargs += ["--input", file]
        pargs += ["--config", os.path.join(script_location, "autoProcess.ini")]
        pargs += ["--moveto", os.path.join(temp_location, "temp.mp4")]
        if not args.delete:
            pargs += ["--nodelete"]
        pargs += ["--auto"]

        p = subprocess.Popen(pargs)
        p.wait()

        print("\tdone transcoding %s" % file)
        print("\tcopying to %s" % output_name)
        try:
            shutil.move(os.path.join(temp_location, "temp.mp4"), output_name)
        except:
            with open(os.path.join(script_location, "blacklist.txt"), "a") as f:
                f.write("%s\n" % file)

        shutil.rmtree(temp_location)

    print("done.")

    if args.interval >= 0:
        time.sleep(args.interval)
    else:
        break 