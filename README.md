# To H264

## A simple GUI program that converts a video into H264 using FFmpeg. 
##### When in doubt, turn to H264.
---
### How to run the executable (Windows):
Download the package from releases
Place `ffmpeg.exe` alongside `TurnH264.exe` or `TurnH264.py`
FFmpeg builds are available at https://www.ffmpeg.org/download.html


### How to run from source (Linux):
  
  Install PySide6: `pip install PySide6`

if it's not globally installed, Place an `ffmpeg` executable in the same directory as `TurnH264.py`

FFmpeg builds are available at https://www.ffmpeg.org/download.html
Everything should work as intended.

### MacOS:
Please do note that this program is untested for macOS as neither me nor any of my friends have Apple hardware.

---
Todo:
- [x] Video bitrate choice
- [x] Audio bitrate choice
- [x] Graphical file browsing
- [x] Amount of threads to use
- [ ] Add a progress bar
- [ ] NVENC and VCE
 --- 
My fork was developed alongside this master branch during pre-release hence the differences in code.
