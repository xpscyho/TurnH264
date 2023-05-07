import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
import zipfile

import wget



class Timer:
    def __init__(self, timestamp: int | None = None):
        self.time = timestamp or time.perf_counter()

    def print(self, msg: str = ""):
        '''print and resets time'''
        return self.poll(msg).reset()

    def poll(self, msg: str = ""):
        '''print without resetting time'''
        print(f"{time.perf_counter() - self.time}: {msg}")
        return self

    def reset(self):
        '''resets time'''
        self.time = time.perf_counter()
        return self.time

    def __str__(self): return self.__repr__()

    def __repr__(self): return str((time.perf_counter()) - self.time)


# custom progress bar (slightly modified) [https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console]
def progress_bar(iteration: int, total: int, length: int = max(os.get_terminal_size()[0]//6, 10),
                Print=False, fill="#", nullp="-", corner="[]", color=True,
                end="\r", pref='', suff=''):
    color1, color2 = "\033[93m", "\033[92m"
    filledLength = length * iteration // total

    #    [############################# --------------------------------]
    bar = (fill*length)[:filledLength] + (nullp*(length - filledLength))
    command = f"\033[K{color2}{corner[0]}{color1}{bar}{color2}{corner[1]}\033[0m" if color else f"{corner[0]}{bar}{corner[1]}"
    command = pref+command+suff
    return command


class ffmpeg_utils():
    def dirname(path):
        return path.rsplit(os.sep, 1)[0]

    def get_ffmpeg(force=False):
        if force: return
        name = {"linux": ["ffmpeg", "ffprobe"],
                "win32": ["ffmpeg.exe", "ffprobe.exe"]}
        origin = ffmpeg_utils.dirname(os.path.realpath(__file__))
        cwd = os.getcwd()
        os.chdir(origin)
        locFfmpeg = os.path.join(origin, name[sys.platform][0])
        locFfprob = os.path.join(origin, name[sys.platform][1])
        #* comment this out to test download() if not on PATH ###############
        locFfmpeg = locFfmpeg if os.path.exists(locFfmpeg) else name[sys.platform][0]
        locFfprob = locFfprob if os.path.exists(locFfprob) else name[sys.platform][1]
        #*###################################################################
        ffmpeg_paths = [locFfmpeg, locFfprob]
        try:  # check if ffmpeg is accessible to subprocess
            subprocess.Popen([locFfmpeg, "-version"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.Popen([locFfprob, "-version"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except:
            return
        os.chdir(cwd)
        return ffmpeg_paths

    def download():
        ffdl = {'linux': ["ffmpeg-master-latest-linux64-gpl", ".tar.xz", "ffmpeg",     "ffprobe",     tarfile.open],
                'win32': ["ffmpeg-master-latest-win64-gpl",   ".zip",    "ffmpeg.exe", "ffprobe.exe", zipfile.ZipFile]}
        link = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
        assert sys.platform in ffdl.keys(), "Your platform isn't available yet, please raise an issue on GitHub"
        path, pkgExt, ffmpeg, ffprobe, method = ffdl[sys.platform]
        Timer.print("   downloading...")
        wget.download(link+path+pkgExt, ffmpeg+pkgExt)
        Timer.print("\n   extracting...")
        with method(ffmpeg+pkgExt) as f:
            f.extract(path+"/bin/"+ffmpeg)
            shutil.move(path+"/bin/"+ffmpeg, ffmpeg)
            f.extract(path+"/bin/"+ffprobe)
            shutil.move(path+"/bin/"+ffprobe, ffprobe)
        shutil.rmtree(path)
        os.remove(ffmpeg+pkgExt)
        Timer.print(f"   installed in ./{ffmpeg}, ./{ffprobe}.\033[0m")
        return ["./"+ffmpeg, "./"+ffprobe]

if __name__ == "__main__":
    Timer.start()
    print(ffmpeg_utils.get_ffmpeg(force=True))
    ffmpeg_utils.download()
    
