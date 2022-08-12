
import json
import os
import shutil
import subprocess
import sys
import tarfile
import threading
import time
import zipfile
from os.path import exists

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
def progressBar(iteration: int, total: int, length: int = max(os.get_terminal_size()[0]//6, 10),
                Print=False, fill="#", nullp="-", corner="[]", color=True,
                end="\r", pref='', suff=''):
    color1, color2 = "\033[93m", "\033[92m"
    filledLength = length * iteration // total

    #    [############################# --------------------------------]
    bar = (fill*length)[:filledLength] + (nullp*(length - filledLength))
    command = f"\033[K{color2}{corner[0]}{color1}{bar}{color2}{corner[1]}\033[0m" if color else f"{corner[0]}{bar}{corner[1]}"
    command = pref+command+suff
    if Print:
        print(command, end=end)
    return command


class ffmpeg_utils():
    def basename(path):
        return path.rsplit(os.sep, 1)[-1]

    def dirname(path):
        return path.rsplit(os.sep, 1)[0]

    def extension(path):
        return path.rsplit(".", 1)[-1]

    def get_ffmpeg():
        name = {"linux": ["ffmpeg", "ffprobe"],
                "win32": ["ffmpeg.exe", "ffprobe.exe"]}
        origin = ffmpeg_utils.dirname(os.path.realpath(__file__))
        cwd = os.getcwd()
        os.chdir(origin)
        locFfmpeg = os.path.join(origin, name[sys.platform][0])
        locFfprob = os.path.join(origin, name[sys.platform][1])

        #* comment this out to test download() if not on PATH ###############
        # locFfmpeg = locFfmpeg if exists(locFfmpeg) else name[sys.platform][0]
        # locFfprob = locFfprob if exists(locFfprob) else name[sys.platform][1]
        #*###################################################################

        ffmpeg_paths = [locFfmpeg, locFfprob]

        # check if ffmpeg is accessible to subprocess
        try:
            subprocess.Popen([locFfmpeg, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.Popen([locFfprob, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except:
            print("\033[33;1mffmpeg not detected, obtaining ffmpeg...")
            # ffmpeg_paths_thread = threading.Thread(
            #     target=ffmpeg_utils.download)
            # ffmpeg_paths_thread.start()
            ffmpeg_paths = ffmpeg_utils.download()
        os.chdir(cwd)
        
        return ffmpeg_paths

    def download():
        ffmpeg_links = {"linux": ["curl", "-s", "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest"],
                        "win32": ["curl", "-s", "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest"]}
        #               "macos": ["curl", "-s", "https://evermeet.cx/ffmpeg/info/ffprobe/snapshot"]
        ffdl = {}

        if sys.platform == "linux":
            timer.print("  getting JSON...")
            ffdl['out'] = subprocess.check_output(ffmpeg_links['linux'])
            ffdl['json'] = json.loads(ffdl['out'])
            ffdl['url'] = ffdl['json']['assets'][1]['browser_download_url']
            timer.print("  downloading...")
            ffdl['data'] = requests.get(ffdl['url'])
            open("ffmpeg.tar.xz", "wb").write(ffdl['data'].content)
            timer.print("  extracting...")
            with tarfile.open('ffmpeg.tar.xz') as f:
                f.extract("ffmpeg-master-latest-linux64-gpl/bin/ffmpeg")
                f.extract("ffmpeg-master-latest-linux64-gpl/bin/ffprobe")
                timer.print("  moving...")
                shutil.move("ffmpeg-master-latest-linux64-gpl/bin/ffmpeg",
                            "ffmpeg")
                shutil.move("ffmpeg-master-latest-linux64-gpl/bin/ffprobe",
                            "ffprobe")
                shutil.rmtree("ffmpeg-master-latest-linux64-gpl")
                os.remove("ffmpeg.tar.xz")
            del ffdl
            print("\033[0m", end="")
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


if __name__ == "__main__":
    ffmpeg_utils.get_ffmpeg()
