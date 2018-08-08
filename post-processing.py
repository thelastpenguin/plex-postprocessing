"""
    must git submodule init and git submodule update -r 

    also watch out for: https://github.com/mdhiggins/sickbeard_mp4_automator/issues/643

"""

import argparse 
import os 
import subprocess 

parser = argparse.ArgumentParser(description='Running post-processing on media files')
parser.add_argument('media_dir', help="the location of the media files")
args = parser.parse_args()

script_location = os.path.dirname(__file__)

def scan_directory(directory):
    files = []
    for file in os.listdir(directory):
        if file == "." or file == "..": continue 
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path):
            yield file_path 
        else:
            yield from scan_directory(file_path)

os.nice(19)

print("running post-processing.py")

print("scanning files...")
files = list(scan_directory(args.media_dir))
file_set = set(files)
print("built directory list... now transcoding if needed.")
print(files)

for file in files:
    basename, ext = os.path.splitext(file)

    if ext != ".mkv": continue 
    output_name = basename + ".mp4"
    if output_name in file_set: continue 
    
    print("found file %s which needs processing" % file)

    args = ["python"]
    args += [os.path.join(script_location, "./sickbeard_mp4_automator/manual.py")]
    args += ["--input", file]
    args += ["--config", os.path.join(script_location, "autoProcess.ini")]
    args += ["--nodelete", "--moveto", output_name]
    args += ["--auto"]

    p = subprocess.Popen(args)
    p.wait()

print("done.")