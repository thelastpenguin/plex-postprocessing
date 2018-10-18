import argparse 
import os 
import subprocess 
import time
import difflib


parser = argparse.ArgumentParser(description='Running post-processing on media files')
parser.add_argument('download_dir', help="the location of the media files")
parser.add_argument('output_dir', help="the location of the media files")
args = parser.parse_args()

print("beginning injestion of new downloads")

script_location = os.path.dirname(__file__)

process_directories = [
    "movies",
    "tv",
    "radarr",
    "tv-sonarr",
]

def should_process(filepath):
    filepath = filepath.lower()
    for key in process_directories:
        if key in filepath: return True 
    return False 

def scan_directory(directory):
    files = []
    for file in os.listdir(directory):
        if file == "." or file == "..": continue 
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path):
            yield file_path
        else:
            yield from scan_directory(file_path)

def run_filebot(inputdir, outputdir):
    env = os.environ.copy()
    env["INPUT"] = inputdir
    env["OUTPUT"] = outputdir
    p = subprocess.Popen(["sh", os.path.join(script_location, "run-filebot.sh")], env=env)
    p.wait()
    return p.returncode

def flood_remove_completed():
    p = subprocess.Popen(["sh", os.path.join(script_location, "flood-remove-completed.sh")])
    p.wait()
    return p.returncode

print("finally, having flood remove all downloads with status completed")
flood_remove_completed()

print("reading directory tree before filebot runs")
files_before = set(scan_directory(args.download_dir))

print("running filebot")

# TODO: finish this...
# def rename_bad_subtitles(dir):
#     listing = os.listdir(dir)
#     files = [f for f in listing if os.path.isfile(f)]
#     dirs = [f for f in listing if os.path.isdir(f) and f != "." and f != ".."]
#     movies = list(filter(lambda x: x.endswith(".mkv") or x.endswith(".mp4"), listing))
#     srts = list(filter(lambda x: x.endswith(".srt") or x.endswith(".srt"), listing))
#     if len(movies) == 1:
#         movie_base = os.path.basename(movies[0])
#         for srt in srts:
#             SequenceMatcher(None, "abcd", "bcde")
#     for dir in dirs:
#         rename_bad_subtitles(dir)

filebot_returncode = run_filebot(args.download_dir, args.output_dir)

if filebot_returncode == 0:
    print("removing files that were here before filebot ran UNLESS THEY ARE IN WHITELIST")
    curtime = time.time()
    for file in scan_directory(args.download_dir):
        if not should_process(file):
            print("moving %s to the 'Other' folder since it is not a media file")
            common_base = os.path.commonprefix([file, args.download_dir])
            move_to_location = os.path.join(args.output_dir, "Other", os.path.relpath(file, common_base))
            os.renames(file, move_to_location)
        else:
            file_age = curtime - os.path.getmtime(file) 
            # we don't remove files that are less than an hour old
            # or files that were added before filebot started
            if file in files_before and file_age >= 20 * 60: 
                print("\tremoving %s" % file)
                os.remove(file)
            else:
                print("\tskipping %s, it was not here when filebot started" % file)
else:
    print("WARNING!!! FILEBOT DID NOT EXIT WITH GOOD STATUS. REQUIRES MANUAL INTERVENTION")

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
