import argparse 
import os 
import subprocess 
import time
from difflib import SequenceMatcher
import shutil 
import time
parser = argparse.ArgumentParser(description='Running post-processing on media files')
parser.add_argument('download_dir', help="the location of the media files")
parser.add_argument('output_dir', help="the location of the media files")
parser.add_argument('-minimum_free_space', default=40, type=int, help="the minimum amount of free space in gigabytes to reserve on the disk")
args = parser.parse_args()

print("\n\n\n\n\n\n\n\nBEGINNING INJESTION OF NEW DOWNLOADS: " + time.strftime("%Y-%m-%d %H:%M"))

script_location = os.path.dirname(__file__)

process_directories = {
    "movies": ["fixsubs", "rename", "clear"],
    "tv": ["fixsubs", "rename", "clear"],
    "radarr": ["fixsubs", "rename", "clear"],
    "tv-sonarr": ["fixsubs", "rename", "clear"],
    "anime": ["fixsubs", "rename", "clear"],
    "other": ["archive"],
}

# get all the files in a given directory
def scan_directory(directory):
    files = []
    for file in os.listdir(directory):
        if file == "." or file == "..": continue 
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path):
            yield file_path
        else:
            yield from scan_directory(file_path)

print("reading a tree of all files before running, this acts as a 'checkpoint'")
files_before = set(scan_directory(args.download_dir))

def run_op_rename(inputdir, outputdir):

    env = os.environ.copy()
    env["INPUT"] = inputdir
    env["OUTPUT"] = outputdir
    p = subprocess.Popen(["sh", os.path.join(script_location, "run-filebot.sh")], env=env)
    p.wait()

    return p.returncode 

def run_op_archive(dir_path):
    for file in scan_directory(dir_path):
        print("moving %s to the 'Other' folder since it is not a media file" % file)
        common_base = os.path.commonprefix([file, args.download_dir])
        move_to_location = os.path.join(args.output_dir, "Other", os.path.relpath(file, common_base))
        os.makedirs(move_to_location, exist_ok=True)
        shutil.move(file, move_to_location)

def run_op_clear(dir_path):
    global files_before 
    
    print("removing files in '%s' that were here before filebot ran" % dir_path)
    curtime = time.time()
    for file in scan_directory(args.download_dir):
        file_age = curtime - os.path.getmtime(file) 
        # we don't remove files that are less than an hour old
        # or files that were added before filebot started
        if file in files_before and file_age >= 20 * 60: 
            print("\tremoving %s" % file)
            os.remove(file)
        else:
            print("\tskipping %s, it was not here when filebot started" % file)

def fix_subtitle_naming(media_path): 
    print("Finding SRT files for %s" % media_path)

    # takes the location of some media file
    dirname = os.path.dirname(media_path)
    basename = os.path.splitext(media_path)[0]

    # the set of files in the directory
    files = list(scan_directory(dirname))

    # take only english srt's if languages are added to the srt's 
    srt_files = list(file for file in files if file.endswith(".srt"))
    srt_files_english = list(file for file in srt_files if (".en" in file) or ("eng" in file.lower()))

    if len(srt_files) == 0: 
        print("No srt files found, early return")
        return 

    if len(srt_files_english) > 0:
        srt_files = srt_files_english 
        print("Found an 'english' specific SRT so we will only check these from now on")

    print("SRT options are: " + str(srt_files))
    _, srt_name = max((SequenceMatcher(None, os.path.splitext(media_path)[0]+".english.srt", file).ratio(), file) for file in srt_files)
    print("best match SRT was %s for movie %s" % (srt_name, media_path))

    if srt_name != basename + ".en.srt":
        shutil.copyfile(srt_name, basename + ".en.srt")

def run_op_fixsubs(dir_path):
    print("Fixing subtitles for directory: %s" % dir_path)
    for file in scan_directory(dir_path):
        if file.endswith(".mp4") or file.endswith(".mkv"):
            fix_subtitle_naming(file)

def flood_remove_completed():
    usage = shutil.disk_usage(args.download_dir)
    print("\tdisk use: %d/%d" % (usage.used, usage.total))
    if usage.free > args.minimum_free_space * 1000000000:
        print("\tleaving completed downloads as they are, usage.free not less than the minimum free space")
        return 
    p = subprocess.Popen(["sh", os.path.join(script_location, "flood-remove-completed.sh")])
    p.wait()
    return p.returncode

print("first, having flood remove all downloads with status completed")
flood_remove_completed()

print("processing all directories in the download dir: %s, dirs: %s" % (args.download_dir, str(os.listdir(args.download_dir))))
for top_level_dir in os.listdir(args.download_dir):
    if top_level_dir == "." or top_level_dir == "..": continue 
    dir_path = os.path.join(args.download_dir, top_level_dir)
    if not os.path.isdir(dir_path): continue 
    operations = process_directories.get(top_level_dir.lower())
    
    if operations == None: 
        operations = process_directories["other"]

    # determine if the directory should be processed 
    print("processing top level directory: " + dir_path)
    print("\tdirectory operations: " + str(operations))

    for op in operations:
        if op == "rename": 
            run_op_rename(dir_path, args.output_dir)
        elif op == "clear": 
            run_op_clear(dir_path)
        elif op == "archive":
            run_op_archive(dir_path)
        elif op == "fixsubs":
            run_op_fixsubs(dir_path)
        else:
            print("UNRECOGNIZED OPERATION!!! BADNESS")

def remove_empty_dirs(rootdir):
    count = 0
    for file in os.listdir(rootdir):
        if file == "." or file == "..": continue 
        file_path = os.path.join(rootdir, file)
        if os.path.isdir(file_path):
            count += remove_empty_dirs(file_path)
        else:
            count += 1

    if count == 0 and rootdir != args.download_dir:
        print("\tremoving empty directory %s" % rootdir)
        os.rmdir(rootdir)
    
    return count 

print("removing empty directories in the downloads dir")
remove_empty_dirs(args.download_dir)
# replace with this: find /path/to/uploadcache -type d -empty -delete
