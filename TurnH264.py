# coding: utf-8
import math
import os
import signal
import subprocess
import sys
import threading
import time

from PySide6 import QtGui, QtWidgets
# this is used, but run in exec so they are shown as unused (at least in MY IDE)
from PySide6.QtCore import Qt


class timer:  # timer setup ####
    def start():
        '''start the timer'''
        timer.timer_start_time = time.time()

    def print(instr, end='\n'):
        '''print and restart the timer'''
        if timer.timer_start_time is None:
            timer.start()
            print("Started timer")
            return
        now = time.time()
        diff = (now - timer.timer_start_time) * 1000
        timer.timer_start_time = now
        print(f"{instr}: ms{diff:.4f}", end=end)
        return diff

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
    # color1="\033[93m", color2="\033[92m"
    color1 = "\033[93m"
    color2 = "\033[92m"
    filledLength = int(length * iteration // total)
    # doing this allows for multi-character fill
    fill = (fill*length)[:filledLength]
    nullp = (nullp*(length - filledLength))
    bar = fill + nullp
    # like this: <!i!i!i!i!i!.......................................>
    command = f"{color2}<{color1}{bar}{color2}>\033[0m" if color else f"<{bar}>"
    if printing:
        print(command, end=end)
    # Print New Line on Complete
    if iteration == total:
        print()
    return command


timer.reset()
widget_layout = {
    "input_dialog":         ["Label", "Input video:",    "Center", "YE_HIDE", (1, 0, 1, 1)],
    "input_text":           ["LineEdit",                   "Left", "YE_HIDE", (1, 1, 1, 2)],
    "input_button":         ["ToolButton", ". . .",        "Left", "YE_HIDE", (1, 3, 1, 1)],
    "help_button":          ["ToolButton", "  ?  ",       "Right", "YE_HIDE", (1, 4, 1, 1)],
    "output_dialog":        ["Label", "Output:",         "Center", "YE_HIDE", (2, 0, 1, 1)],
    "output_text_input":    ["LineEdit",                   "Left", "YE_HIDE", (2, 1, 1, 2)],
    "outputDrop":           ["ComboBox",                   "Left", "YE_HIDE", (2, 3, 1, 2)],

    "v_bitrate_dialog":     ["Label", "Video bitrate:",  "Center", "YE_HIDE", (3, 0, 1, 1)],
    "video_bitrate":        ["LineEdit",                   "Left", "YE_HIDE", (3, 1, 1, 2)],
    "videoDrop":            ["ComboBox",                   "Left", "YE_HIDE", (3, 3, 1, 2)],
    "a_bitrate_dialog":     ["Label", "Audio bitrate:",  "Center", "YE_HIDE", (4, 0, 1, 1)],
    "audio_bitrate_slider": ["Slider",      "Horizontal",  "Left", "YE_HIDE", (4, 1, 1, 2)],
    "audio_bitrate_input":  ["LineEdit",                   "Left", "YE_HIDE", (4, 1, 1, 2)],
    "audioDrop":            ["ComboBox",                   "Left", "YE_HIDE", (4, 3, 1, 2)],
    "threads_dialog":       ["Label", "Threads:",        "Center", "YE_HIDE", (5, 0, 1, 1)],
    "thread":               ["Slider",      "Horizontal",  "Left", "YE_HIDE", (5, 1, 1, 2)],
    "threads_dialog_ratio": ["Label", "",                "Center", "YE_HIDE", (5, 3, 1, 2)],
    "speed_dialog":         ["Label", "Speed:",          "Center", "YE_HIDE", (6, 0, 1, 1)],
    "speedDrop":                ["ComboBox",                   "Left", "YE_HIDE", (6, 1, 1, 2)],
    "fps_dialog":           ["Label", "fps:",            "Center", "YE_HIDE", (7, 0, 1, 1)],
    "fps":                  ["LineEdit",                   "Left", "YE_HIDE", (7, 1, 1, 2)],
    "res_dialog":           ["Label", "resolution:",        "Left", "YE_HIDE", (8, 0, 1, 1)],
    "res_line":             ["LineEdit",                   "Left", "YE_HIDE", (8, 1, 1, 2)],
    "resDrop":              ["ComboBox",                   "Left", "YE_HIDE", (8, 3, 1, 2)],

    "status_dialog":        ["Label", "Awaiting input",  "Center", "NO_HIDE", (9, 0, 1, 5)],
    "work_button":          ["PushButton", "Start",        "Left", "NO_HIDE", (10, 0, 1, 5)],
    "yes_button":           ["PushButton", "Continue",     "Left", "NO_HIDE", (10, 0, 1, 3)],
    "no_button":            ["PushButton", "Cancel",       "Left", "NO_HIDE", (10, 3, 1, 2)]
}
widget_boxes = {
    "audio_bitrate_slider": [1, 8, 0.75],
    "thread":               [1, os.cpu_count(), 0.75],
    "speedDrop":            ["veryslow", "slower", "slow",
                             "medium",   "fast",   "faster",
                             "veryfast", "ultrafast"],
    "outputDrop":           ["mp4", "mkv", "avi", "ts", "png"],
    "videoDrop":            ["kb/s", "crf"],
    "audioDrop":            ["copy", "slider", "input", "none"],
    "resDrop":              ["copy", "max", "min"],
}


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        timer.print("Starting")
        self.setWindowTitle("TurnH264")
        self.resize(320, 340)
        self.setMinimumSize(320, 260)
        self.addWidgets()
        self.stopped_preemptively = False

    def addWidgets(self):
        timer.reset()

        def parse_layout(widgetDictionary):
            self.layout = QtWidgets.QGridLayout(self)
            for key in widgetDictionary:
                layout = widgetDictionary[key][-1]
                vals = widgetDictionary[key]
                given = "self."+key
                exec(f"{given} = QtWidgets.Q{vals[0]}()")
                if vals[0] in ["Label", "PushButton", "ToolButton"]:  # text
                    exec(f"{given}.setText('{vals[1]}')")
                if vals[0] in ["Label", "LineEdit"]:  # alignment
                    exec(f"{given}.setAlignment(Qt.Align{vals[-3]})")
                if vals[0] == "ComboBox":  # box items
                    exec(f"{given}.addItems({widget_boxes[key]})")
                if vals[0] == "Slider":  # sliders
                    exec(f"{given}.setRange({widget_boxes[key][0]}, \
                                            {widget_boxes[key][1]})")
                    exec(f"{given}.setValue({widget_boxes[key][1]} * \
                                            {widget_boxes[key][2]})")
                    exec(f"{given}.setOrientation(Qt.Orientation.{vals[1]})")
                exec(f"self.layout.addWidget({given}, {layout[0]}, \
                      {layout[1]}, {layout[2]}, {layout[3]})")  # apply layout
        parse_layout(widget_layout)

        timer.print("Widgets created")
        self.changeButtons(0)
        self.input_text.textChanged.connect(self.inputChanged)
        self.input_button.clicked.connect(self.inputButtonClicked)
        self.outputDrop.currentTextChanged.connect(self.inputChanged)
        self.audioDrop.currentTextChanged.connect(self.audioDropChanged)
        self.resDrop.currentTextChanged.connect(self.resDropChanged)
        self.thread.valueChanged.connect(self.threadChanged)
        self.work_button.clicked.connect(self.workClicked)
        self.yes_button.clicked.connect(self.yesClicked)
        self.no_button.clicked.connect(self.noClicked)
        timer.print("widgets connected")
        self.speedDrop.setCurrentIndex(3)
        self.inputChanged()
        self.audioDropChanged()
        self.threadChanged()
        self.resDropChanged()

    def changeButtons(self, num):
        '''0 = Start, 1 = Stop, 2 = Yes/No dialog'''
        self.work_button.setVisible(True)
        self.yes_button.setVisible(False)
        self.no_button.setVisible(False)
        if num == 0:
            self.work_button.setText("Start")
        if num == 1:
            self.work_button.setText("Stop")
        if num == 2:
            self.work_button.setVisible(False)
            self.no_button.setVisible(True)
            self.yes_button.setVisible(True)

    def realOutput(self):
        return self.output_text_input.text().replace("%Input_Path%", os.path.dirname(self.input_text.text()))

    def WidgetsEditable(self, num):
        for i in widget_layout:
            if widget_layout[i][-2] == "YE_HIDE":
                exec(f"self.{i}.setEnabled(bool({num}))")

    def inputChanged(self):
        now_extension = self.outputDrop.currentText()
        extension = "/%06d.png" if now_extension == "png" else now_extension
        self.input_text.setText(self.input_text.text().replace("\"", ""))
        self.output_text_input.setText(
            "" if self.input_text.text() == "" else
            "%Input_Path%/"  # input path
            + os.path.basename(self.input_text.text()).split(".")[0]
            + "-converted." + extension)  # suffix
        self.output_text_input.update()

    def inputButtonClicked(self):
        home = str("c:\\users\\" if sys.platform == "win32" else
                   os.path.expanduser("~"))
        file = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select input file", home)[0]
        self.input_text.setText(file)

    def audioDropChanged(self):
        """ copy = 0, slider = 1, input = 2"""
        index = self.audioDrop.currentIndex()
        audio_dict = ([False, False], [False, True],
                      [True, False], [False, False])
        self.audio_bitrate_input.setVisible(audio_dict[index][0])
        self.audio_bitrate_slider.setVisible(audio_dict[index][1])

    def resDropChanged(self):
        index = self.resDrop.currentIndex()
        self.res_line.setVisible(bool(index))

    def threadChanged(self):
        self.threads_dialog_ratio.setText(
            f"{str(self.thread.value()).zfill(len(str(os.cpu_count())))} / {os.cpu_count()}")
        self.threads_dialog_ratio.update()

    def noClicked(self):
        self.status_dialog.setText("Awaiting input")
        self.work_button.setText("Start")
        self.WidgetsEditable(1)
        self.changeButtons(0)

    def yesClicked(self):
        if self.stopped_preemptively == True:
            os.remove(self.realOutput())
            self.noClicked()
            self.stopped_preemptively = False
            return
        self.startFfmpeg()

    def byteFormat(self, size, suffix="B"):
        '''modified version of: https://stackoverflow.com/a/1094933'''
        size = int(size)
        for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti']:
            if abs(size) < 2**10:
                return f"{size:3.1f}{unit}{suffix}"
            size /= 2**10
        return f"{size:3.1f}{unit}{suffix}"

    def startFfmpeg(self):
        self.status_dialog.setText("Converting...")
        timer.reset()
        local_ffmpeg = os.path.dirname(os.path.realpath(__file__)) + "/ffmpeg"
        vindex = self.videoDrop.currentIndex()
        aindex = self.audioDrop.currentIndex()
        rindex = self.resDrop.currentIndex()
    # handle resolutions
        reses = {}
        reses['input_res'] = [int(val.split("=")[1]) for val in subprocess.check_output(
                             ['ffprobe', '-v', 'error', '-show_entries', 'stream=width,height',
                              '-of', 'default=noprint_wrappers=1', self.input_text.text()]).
                              decode("utf-8").split("\n")[:-1]]
        reses['res_line'] = int(self.res_line.text()
                                if self.res_line.text() != "" else 0)
        reses['restio'] = (reses['res_line']/max(reses['input_res']) if rindex ==
                           1 else reses['res_line']/min(reses['input_res']) if rindex == 2 else 1)
        reses['new_res'] = [val*reses['restio'] for val in reses['input_res']]
        timer.print(reses['input_res'])
        if type(reses['new_res'][0]) != int:
            if not reses['new_res'][0].is_integer() or not reses['new_res'][1].is_integer():
                self.status_dialog.setText(
                    "Warning: the specified resolution is not an int.\nresult may be imprecise")
                timer.print(f"{reses['new_res']} is imprecise, flooring...")
        reses['new_res'] = [math.floor(val)-(math.floor(val)%2) for val in reses['new_res']]
        ffargs = {"path": local_ffmpeg if os.path.exists(local_ffmpeg) else "ffmpeg",
                  "input":   ['-i', self.input_text.text()],
                  "output":  self.realOutput(),
                  "vidbr":   "".join([val for val in self.video_bitrate.text() if val.isnumeric()]),
                  "audbr_s": str(self.audio_bitrate_slider.value()*32)+"k",
                  "audbr_i": self.audio_bitrate_input.text(),
                  "threads": ['-threads', str(self.thread.value())],
                  "speedDrop":   ['-preset', self.speedDrop.currentText()],
                  "fps":     "".join([val for val in self.fps.text() if val.isnumeric()])}

        # tmpdir for progress bar
        tmpdir = os.path.dirname(os.path.realpath(__file__)) + "/.TurnH264.tmp"
        if os.path.exists(tmpdir):
            os.remove(tmpdir)
        tmpfile = open(tmpdir, "w")

        self.command = sum([[ffargs['path'], '-y'],
                            ffargs['input'],
                            ['-map', '0:v:?', '-map', '0:a:?'],
                            ['-c:v', 'libx264'],
                            ffargs['threads'],
                            ffargs['speedDrop'],
                            ['-b:v', ffargs['vidbr'] + "k"] if vindex == 0 and ffargs['vidbr'] != "" else
                            ['-crf', ffargs['vidbr']] if vindex == 1 and ffargs['vidbr'] != "" else
                            ['-q:v', '0'],
                            ['-c:a', 'copy'] if aindex == 0 else
                            ['-b:a', ffargs['audbr_s']] if aindex == 1 else
                            ['-b:a', ffargs['aidbr_i']] if aindex == 2 else ['-an'],
                            ['-r', ffargs['fps']] if ffargs['fps'] != "" else [],
                            ['-vf', f'scale={reses["new_res"][0]}:{reses["new_res"][1]}'] if
                            rindex != 0 and reses['input_res'] != reses['new_res'] else [],
                            ['-progress', '-', '-nostats'],
                            [ffargs['output']]], [])
        print(" ".join(self.command))
        # return
        ffmpegThread = subprocess.Popen(
            self.command, stdout=tmpfile, stderr=tmpfile)
        timer.print("ffmpeg initialized")

        def ffmpegCancel():
            timer.print("killing ffmpeg")
            if sys.platform == "win32":  # windows doesn't use SIGINT for some reason
                while ffmpegThread.poll() is None:
                    os.kill(ffmpegThread.pid, signal.CTRL_C_EVENT)
                    time.sleep(3)
            else:
                while ffmpegThread.poll() is None:
                    ffmpegThread.send_signal(signal.SIGINT)
                    time.sleep(2.8)
            timer.print("\nkilled ffmpeg")
            self.stopped_preemptively = True
            self.status_dialog.setText(
                "Conversion stopped. delete unfinished video?")
            self.changeButtons(2)

        def ffmpegWait():
            ffmpegThread.wait()
            with open(tmpdir, "r") as file:
                lines = file.readlines()
                timer.print("".join(lines[-12:]))
            self.status_dialog.setText("Conversion complete!")
            self.work_button.clicked.disconnect()
            self.work_button.clicked.connect(self.workClicked)
            self.changeButtons(0)
            self.WidgetsEditable(1)
            timer.print("\nffmpeg finished")
            self.stopped_preemptively = False
            os.remove(tmpdir)

        def ffmpegWatch():
            time.sleep(2)  # so the lastline stuff doesnt get tripped
            # get the frame count of the video for progress bar
            # ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 input.mp4
            video_frame = subprocess.check_output([
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-count_frames", "-show_entries", "stream=nb_read_frames",
                "-print_format", "csv", "-i", self.input_text.text()])

            video_frame_total = video_frame.decode("utf-8").strip()
            video_frame_total = int(
                "".join([val for val in video_frame_total if val.isnumeric()]))
            #  "".join([val for val in self.video_bitrate.text() if val.isnumeric()])
            print("\n"*4)
            while os.path.exists(tmpdir):
                file = open(tmpdir, "r")
                lines = file.readlines()
                if len(lines) > 0:
                    last_line = [i.strip().split("=") for i in lines[-12:]]
                    try:
                        line_dict = {data[0]: data[1] for data in last_line}
                    except:
                        continue
                    used_list = [
                        "frame: "+line_dict['frame'] +
                        " / "+str(video_frame_total),
                        line_dict['fps']+" fps",
                        "speed: " + line_dict['speed'],
                        "\n"+printProgressBar(printing=False, total=video_frame_total, length=50,
                                              iteration=int(line_dict['frame']), color=False, nullp=".", fill="!", end=""),
                        str(round(
                            (int(line_dict['frame'])
                             / video_frame_total)*100, 2))+"%",
                        "\nbitrate: " + line_dict['bitrate'],
                        "size: " + self.byteFormat(line_dict['total_size']),
                    ]
                    for i in line_dict:
                        print(i)
                    # timer.poll(("\033[A\r\033[K"*4)+", ".join(used_list)+"\n")
                    self.status_dialog.setText(", ".join(used_list))
                file.close()
                time.sleep(0.5)

        self.changeButtons(1)
        self.WidgetsEditable(0)
        self.work_button.clicked.disconnect()
        self.work_button.clicked.connect(ffmpegCancel)

        self.ffmpegWaitThread = threading.Thread(target=ffmpegWait)
        self.ffmpegWatchThread = threading.Thread(target=ffmpegWatch)
        self.ffmpegWatchThread.start()
        self.ffmpegWaitThread.start()

    def workClicked(self):
        input_file = self.input_text.text()
        work_step = self.work_button.text()
        if work_step == "Start":
            if not os.path.exists(input_file):
                self.status_dialog.setText("Input file does not exist.")
                print("File not found")
                return
        ffmpeg_output = self.realOutput()
        if os.path.exists(ffmpeg_output):
            print(ffmpeg_output, "already exists.")
            self.status_dialog.setText("Output already exists, overwrite?")
            self.changeButtons(2)
            self.WidgetsEditable(0)
        else:
            print("running...")
            self.startFfmpeg()


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    main_app_window = MainWindow()
    main_app_window.show()
    sys.exit(app.exec())
