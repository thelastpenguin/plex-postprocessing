"""
    must git submodule init and git submodule update -r 

    also watch out for: https://github.com/mdhiggins/sickbeard_mp4_automator/issues/643

    recommend installing and using pip install https://github.com/althonos/ffpb/archive/master.zip
    if you want progress for ffmpeg

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

# function for scanning a directory
def scan_directory(directory):
    files = []
    for file in os.listdir(directory):
        if file == "." or file == "..": continue 
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path):
            yield file_path 
        else:
            yield from scan_directory(file_path)

# create temporary directory and blacklist files
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

# transcoding helpers
def ffmpeg_list_subtitles(file):
    pargs = [
        args.ffprobe,
        "-loglevel", "error",
        "-select_streams", "s",
        "-show_entries", "stream=index:stream_tags=language",
        "-of", "csv=p=0",
        file
    ]

    p = subprocess.Popen(pargs, stdout=subprocess.PIPE)
    p.wait()
    if p.returncode != 0:
        raise Exception("ffprobe failed to extract subtitle list")
    return [tuple(y.strip() for y in row.split(",")) for row in p.stdout.read().decode("ascii").split("\n") if row != '']

def ffmpeg_get_vcodec(file):
    pargs = [args.ffprobe]
    pargs += [
        "-v", "error", 
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name",
        file 
    ]

    p = subprocess.Popen(pargs, stdout=subprocess.PIPE)
    p.wait()

    if p.returncode != 0:
        raise Exception("ffprobe failed to get video codec")
    return p.stdout.read().decode('ascii').strip().split("\n")[1]

def extract_embedded_subs(file, stream_idx, srt_out):
    pargs = [
        args.ffmpeg,
        "-i", file,
        "-map", "0:%s" % (str(stream_idx)),
        srt_out
    ]

    p = subprocess.Popen(pargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.wait()
    if p.returncode != 0:
        raise Exception("failed to rip subtitles at index: %s" % (str(stream_idx)))
    return True

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

    for filepath in files:

        file_dirname = os.path.dirname(filepath)
        filename = os.path.basename(filepath)
        basicname, ext = os.path.splitext(filename)

        if ext not in extensions_to_transcode: continue 
        output_name = os.path.join(file_dirname, basicname + ".mp4")
        if output_name in file_set: continue 
            
        if filepath in blacklist: 
            print("skipping %s because it is BLACKLISTED" % filepath)
            continue 

        print("processing file: " + filepath)
        temp_location = get_temp_dir()

        try:
            temp_video = os.path.join(temp_location, basicname + ".mp4")
            print("\ttemp video file name: " + temp_video)


            video_codec = ffmpeg_get_vcodec(filepath)
            subtitle_languages = ffmpeg_list_subtitles(filepath)
            # NOTE: subtitles must be named mediafile.language code.srt
            print("\t" + video_codec)
            print("\tsubtitle languages: " + str(subtitle_languages))

            # extracting subtitles
            eng_sub_index = None
            should_hardcode = False
            if len(subtitle_languages) > 0:
                print("ripping subtitles into separate files...")

                for idx, lang in subtitle_languages:
                    if lang == "eng":
                        eng_sub_index = idx 
                    try:
                        srt_path = os.path.join(temp_location, "%s.%s.srt" % (basicname, lang))
                        extract_embedded_subs(filepath, idx, srt_path)
                        print("\textracted language: " + str(lang) + " -> " + srt_path)
                    except:
                        print("\tfailed to extract subtitles: " + str(lang) + " it might be an image based format")
                        should_hardcode = True # try to hard code if available, maybe that will work?

            # transcoding if necessary
            if "h264" not in video_codec or should_hardcode:
                print("\tfile needs transcoding from non-streamable codec")
                pargs = [args.ffmpeg]
                pargs += [
                    "-i", filepath, 
                    "-movflags", "faststart",
                    "-preset", "fast",
                    "-profile:v", "high", "-level", "4.1",
                    "-crf", "23",
                    "-maxrate", "4000k",
                    "-bufsize", "4000k",
                    # "-c:s", "mov_text", # subtitles
                    "-c:v", "libx264",
                    "-c:a", "aac", "-b:a", "192k",
                    "-pix_fmt", "yuv420p",
                    "-t", "60",
                ]

            else:
                print("\tfile needs video copying, audio transcoding")
                pargs = [args.ffmpeg]
                pargs += [
                    "-i", filepath, 
                    "-movflags", "faststart",
                    "-c:s", "mov_text", # subtitles
                    "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "256k",
                ]


            if eng_sub_index != None and should_hardcode:
                pargs += ["-filter_complex", "[0:v][0:%s]overlay[v]" % eng_sub_index, "-map", "[v]"]

            pargs += [temp_video]

            p = subprocess.Popen(pargs)
            p.wait() 
            if p.returncode != 0:
                raise Exception("transcode failed.")

            time.sleep(1)

            print("moving files back to source directory:")
            for f in os.listdir(temp_location):
                if f == "." or f == "..": continue 
                dst = os.path.join(file_dirname, f)
                src = os.path.join(temp_location, f)
                if not os.path.exists(dst):
                    print("\t\t%s -> %s" % (src, dst))
                    shutil.move(src, dst)
            
            if args.delete:
                shutil.rm(filepath)
        except Exception as e:
            add_to_blacklist(file, str(e))
        finally:
            shutil.rmtree(temp_location)

    print("done.")

    if args.interval >= 0:
        time.sleep(args.interval)
    else:
        break 
