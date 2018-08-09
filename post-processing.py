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
import sys

script_location = os.path.dirname(__file__)
temp_dir = os.path.join(script_location, "_temp_")

parser = argparse.ArgumentParser(description='Running post-processing on media files')
parser.add_argument('media_dir', help="the location of the media files")
parser.add_argument('--delete', action="store_true")
parser.add_argument('--interval', default=-1, type=int, help="the repeat interval, -1 to disable (default)")
parser.add_argument('--ffmpeg', default='ffmpeg')
parser.add_argument('--ffprobe', default='ffprobe')
parser.add_argument('--blacklist', default= os.path.join(script_location, "blacklist.txt"))
args = parser.parse_args()


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

if os.path.exists(args.blacklist):
    with open(args.blacklist, "r") as f:
        blacklist = set(line.strip() for line in f if line[0] != "\t")
else:
    blacklist = set()

def add_to_blacklist(file, message=None):
    with open(args.blacklist, "a") as f:
        f.write(file + "\n")
        if message != None:
            f.write("\t" + message + "\n")

def get_temp_dir():
    loc = os.path.join(temp_dir, ''.join(random.choices(string.ascii_uppercase + string.digits, k=64)))
    os.mkdir(loc)
    return loc

os.nice(19)

print("running post-processing.py")
extensions_to_transcode = set([
    ".flv",
    ".avi",
    ".mkv",
    ".wmv",
    ".mov",
    ".m4v",
    ".mp4",
])

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

        if ext not in extensions_to_transcode: continue 
        output_name = basename + "new.mp4"
        if output_name in file_set: continue 
        
        if file in blacklist: 
            print("skipping %s because it is BLACKLISTED" % file)
            continue 

        print("processing file: " + file)
        pargs = [args.ffprobe]
        pargs += [
            "-v", "error", 
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_name",
            file 
        ]
        
        try:
            p = subprocess.Popen(pargs, stdout=subprocess.PIPE)
            p.wait()
            video_codec = p.stdout.read().decode('ascii').strip().split("\n")[1]
            print(video_codec)
        except Exception as e:
            add_to_blacklist(file, "ffprobe failed to fetch media info")
        
        temp_location = get_temp_dir()
        temp_video = os.path.join(temp_location, "test.mp4")

        if "h264" not in video_codec:
            print("\tfile needs transcoding from non-streamable codec")
            pargs = [args.ffmpeg]
            pargs += [
                "-i", file, 
                "-movflags", "faststart",
                "-preset", "fast",
                "-profile:v", "high",
                "-crf", "23",
                "-maxrate", "4000k",
                "-bufsize", "4000k",
                "-c:v", "libx264",
                "-c:a", "aac", "-b:a", "192k",
                temp_video
            ]

            p = subprocess.Popen(pargs)
            p.wait() 

        else:
            print("\tfile needs video copying, audio transcoding")
            pargs = [args.ffmpeg]
            pargs += [
                "-i", file, 
                "-movflags", "faststart",
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k",
                temp_video
            ]

            p = subprocess.Popen(pargs)
            p.wait() 

        print("finished transcoding, final file size: %d\n\toriginal size: %d" % (
            os.path.getsize(temp_video),
            os.path.getsize(file)
        ))
        time.sleep(10)

        try:
            shutil.move(temp_video, output_name)

            if args.delete:
                shutil.rm(file)
        except:
            add_to_blacklist(file, "unable to move output file, does not exist because transcode failed")

        shutil.rmtree(temp_location)

    print("done.")

    if args.interval >= 0:
        time.sleep(args.interval)
    else:
        break 
