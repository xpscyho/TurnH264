import json
import os
import shutil
import subprocess
import sys
import tarfile
import threading
import time
import zipfile

import requests


class timer:  # timer setup ####
    def start():
        '''start the timer'''
        timer.timer_start_time = time.time()

    def print(instr, end='\n'):
        '''print and restart the timer'''

        now = time.time()
        try:
            diff = (now - timer.timer_start_time) * 1000
            timer.timer_start_time = now
            print(f"{instr}: ms{diff:.4f}", end=end)
            return diff
        except:
            timer.start()
            print(instr, end=end)

    def poll(instr, end='\n'):
        '''print without restarting the timer'''
        now = time.time()
        print(f"{instr}: ms{(now - timer.timer_start_time) * 1000:.4f}", end=end)

    def reset():
        '''restart the timer'''
        timer.timer_start_time = time.time()


# custom progress bar (slightly modified) [https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console]
def printProgressBar(
    printing=True, iteration=0, total=1000, length=100, fill="#", nullp="-", color=True, end="\r"
):
    """
    iteration   - Required  : current iteration (Int)
    total       - Required  : total iterations (Int)
    length      - Optional  : character length of bar (Int)
    fill        - Optional  : bar fill character (Str)
    """
    color1 = "\033[93m"
    color2 = "\033[92m"
    filledLength = int(length * iteration // total)
    # doing this allows for multi-character fill
    # like this: <!i!i!i!i!i!.......................................>
    fill = (fill*length)[:filledLength]
    nullp = (nullp*(length - filledLength))
    bar = fill + nullp
    command = f"{color2}<{color1}{bar}{color2}>\033[0m" if color else f"<{bar}>"
    if printing:
        print(command, end=end)
    if iteration == total:
        print()
    return command


class ffmpeg_utils():
    def get_ffmpeg():
        name = {"linux": ["ffmpeg", "ffprobe"],
                "win32": ["ffmpeg.exe", "ffprobe.exe"]}
        local_ffmpeg = os.path.dirname(os.path.realpath(
            __file__)) + "/"+name[sys.platform][0]
        local_ffprobe = os.path.dirname(
            os.path.realpath(__file__)) + "/"+name[sys.platform][1]
        local_ffmpeg = local_ffmpeg if os.path.exists(
        local_ffmpeg) else name[sys.platform][0]
        local_ffprobe = local_ffprobe if os.path.exists(
            local_ffprobe) else name[sys.platform][1]
        ffmpeg_paths = [local_ffmpeg, local_ffprobe]
        try:
            ffmptest = subprocess.Popen([local_ffmpeg, "-version"],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            ffprtest = subprocess.Popen([local_ffprobe, "-version"],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except:
            return 1
            timer.print("ffmpeg not detected, obtaining ffmpeg...")
            ffmpeg_paths_thread = threading.Thread(
                target=ffmpeg_utils.download)
            ffmpeg_paths_thread.start()
        return ffmpeg_paths

    def download():
        ffmpeg_links = {"linux": ["curl", "-s", "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest"],
                        "win32": ["curl", "-s", "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest"],
                        # "macos": ["curl", "-s", "https://evermeet.cx/ffmpeg/info/ffprobe/snapshot"]
                        }
        ffdl = {}

        if sys.platform == "linux":
            ffdl['out'] = subprocess.check_output(ffmpeg_links['linux'])
            ffdl['json'] = json.loads(ffdl['out'])
            ffdl['url'] = ffdl['json']['assets'][1]['browser_download_url']
            timer.poll("  downloading...")
            ffdl['data'] = requests.get(ffdl['url'])
            open("ffmpeg.tar.xz", "wb").write(ffdl['data'].content)
            timer.poll("  extracting...")
            with tarfile.open('ffmpeg.tar.xz') as f:
                f.extract("ffmpeg-master-latest-linux64-gpl/bin/ffmpeg")
                f.extract("ffmpeg-master-latest-linux64-gpl/bin/ffprobe")
                timer.poll("  moving...")
                shutil.move("ffmpeg-master-latest-linux64-gpl/bin/ffmpeg",
                            "ffmpeg")
                shutil.move("ffmpeg-master-latest-linux64-gpl/bin/ffprobe",
                            "ffprobe")
                shutil.rmtree("ffmpeg-master-latest-linux64-gpl")
                os.remove("ffmpeg.tar.xz")
            del ffdl
            return ["./ffmpeg", "./ffprobe"]
        if sys.platform == "win32":
            ffdl['out'] = subprocess.check_output(ffmpeg_links['win32'])
            ffdl['json'] = json.loads(ffdl['out'])
            ffdl['url'] = ffdl['json']['assets'][5]['browser_download_url']
            timer.poll("downloading...")
            ffdl['data'] = requests.get(ffdl['url'])
            open("ffmpeg.zip", "wb").write(ffdl['data'].content)
            timer.poll("extracting...")
            with zipfile.ZipFile('ffmpeg.zip', 'r') as f:
                f.extract("ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe")
                f.extract("ffmpeg-master-latest-win64-gpl/bin/ffprobe.exe")
                shutil.move("ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe",
                            "ffmpeg.exe")
                shutil.move("ffmpeg-master-latest-win64-gpl/bin/ffprobe.exe",
                            "ffprobe.exe")
                shutil.rmtree("ffmpeg-master-latest-win64-gpl")
                os.remove("ffmpeg.zip")
            del ffdl
            return ["./ffmpeg.exe", ".ffprobe.exe"]
