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

import wget


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
        locFfmpeg = locFfmpeg if exists(locFfmpeg) else name[sys.platform][0]
        locFfprob = locFfprob if exists(locFfprob) else name[sys.platform][1]
        #*###################################################################
        ffmpeg_paths = [locFfmpeg, locFfprob]
        try:  # check if ffmpeg is accessible to subprocess
            raise AssertionError
            subprocess.Popen([locFfmpeg, "-version"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.Popen([locFfprob, "-version"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except:
            print("\033[33;1mffmpeg not detected, obtaining ffmpeg...")
            ffmpeg_paths = ffmpeg_utils.download(name)
        os.chdir(cwd)
        return ffmpeg_paths

    def download(name):
        ffdl = {'linux': ["ffmpeg-master-latest-linux64-gpl", ".tar.xz", "ffmpeg",     "ffprobe",     tarfile.open],
                'win32': ["ffmpeg-master-latest-win64-gpl",   ".zip",    "ffmpeg.exe", "ffprobe.exe", zipfile.ZipFile]}
        link = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
        if sys.platform in ffdl.keys():
            path, ext, ffmpeg, ffprobe, method = ffdl["win32"]
            timer.print("   downloading...")
            print(link+path+ext)
            wget.download(link+path+ext, ffmpeg+ext)
            timer.print("\n   extracting...")
            with method(ffmpeg+ext) as f:
                f.extract(path+"/bin/"+ffmpeg)
                shutil.move(path+"/bin/"+ffmpeg, ffmpeg)
                f.extract(path+"/bin/"+ffprobe)
                shutil.move(path+"/bin/"+ffprobe, ffprobe)
            shutil.rmtree(path)
            os.remove(ffmpeg+ext)
            timer.print(f"   installed in ./{ffmpeg}, ./{ffprobe}.\033[0m")
            return ["./"+ffmpeg, "./"+ffprobe]


if __name__ == "__main__":
    timer.start()
    ffmpeg_utils.get_ffmpeg()
