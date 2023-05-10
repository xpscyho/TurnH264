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

if __name__ == "__main__":
    Timer.start()