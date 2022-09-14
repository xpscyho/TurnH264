# coding: utf-8
import math
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from pprint import pprint

from PySide6 import QtGui, QtWidgets
from PySide6.QtCore import Qt

from utilities import timer, ffmpeg_utils, progressBar
# print(ffmpeg_path)
timer.start()
widget_layout = {"inputDlg":             ["Label", "Input video:",    "Center", "YE_HIDE", (1, 0, 1, 1)],
                 "outputDlg":            ["Label", "Output:",         "Center", "YE_HIDE", (2, 0, 1, 1)],
                 "fpsDlg":               ["Label", "fps:",            "Center", "YE_HIDE", (7, 0, 1, 1)],
                 "resDlg":               ["Label", "resolution:",     "Center", "YE_HIDE", (8, 0, 1, 1)],
                 "vBitrateDlg":          ["Label", "Video bitrate:",  "Center", "YE_HIDE", (3, 0, 1, 1)],
                 "aBitrateDlg":          ["Label", "Audio bitrate:",  "Center", "YE_HIDE", (4, 0, 1, 1)],
                 "threadsDlg":           ["Label", "Threads:",        "Center", "YE_HIDE", (5, 0, 1, 1)],
                 "threadsDlgRatio":      ["Label", "",                "Center", "YE_HIDE", (5, 3, 1, 2)],
                 "speedDialog":          ["Label", "Speed:",          "Center", "YE_HIDE", (6, 0, 1, 1)],
             
                 "statDlg":              ["Label", "Awaiting input",  "Center", "NO_HIDE", (9, 0, 1, 5)],
                 "inputText":            ["LineEdit",                   "Left", "YE_HIDE", (1, 1, 1, 2)],
                 "vBitrate":             ["LineEdit",                   "Left", "YE_HIDE", (3, 1, 1, 2)],
                 "outputInput":          ["LineEdit",                   "Left", "YE_HIDE", (2, 1, 1, 2)],
                 "vDrop":                ["ComboBox",                   "Left", "YE_HIDE", (3, 3, 1, 2)],
                 "outputDrop":           ["ComboBox",                   "Left", "YE_HIDE", (2, 3, 1, 2)],
                 "aBitrateSlider":       ["Slider",      "Horizontal",  "Left", "YE_HIDE", (4, 1, 1, 2)],
                 "aBitrateInput":        ["LineEdit",                   "Left", "YE_HIDE", (4, 1, 1, 2)],
                 "audioDrop":            ["ComboBox",                   "Left", "YE_HIDE", (4, 3, 1, 2)],
                 "threads":              ["Slider",      "Horizontal",  "Left", "YE_HIDE", (5, 1, 1, 2)],
                 "speedDrop":            ["ComboBox",                   "Left", "YE_HIDE", (6, 1, 1, 2)],
                 "fps":                  ["LineEdit",                   "Left", "YE_HIDE", (7, 1, 1, 2)],
                 "resLine":              ["LineEdit",                   "Left", "YE_HIDE", (8, 1, 1, 2)],
                 "resDrop":              ["ComboBox",                   "Left", "YE_HIDE", (8, 3, 1, 2)],
                 "QProgress":            ["ProgressBar",             "Center", "YE_HIDE", (10, 0, 1, 5)], 
             
                 "inputButton":          ["ToolButton", ". . .",        "Left", "YE_HIDE", (1, 3, 1, 1)],
                 "helpButton":           ["ToolButton", "  ?  ",       "Right", "YE_HIDE", (1, 4, 1, 1)],
                 "workButton":           ["PushButton", "Start",       "Left", "NO_HIDE", (11, 0, 1, 5)],
                 "yesButton":            ["PushButton", "Continue",    "Left", "NO_HIDE", (11, 0, 1, 3)],
                 "noButton":             ["PushButton", "Cancel",      "Left", "NO_HIDE", (11, 3, 1, 2)]}
widget_boxes = {"aBitrateSlider":          [1, 8, 0.75],
                "threads":              [1, os.cpu_count(), 0.75],
                "speedDrop":            ["veryslow", "slower", "slow",
                                         "medium",   "fast",   "faster",
                                         "veryfast", "ultrafast"],
                "outputDrop":           ["mp4", "mkv", "avi", "ts", "png"],
                "vDrop":                ["kb/s", "crf"],
                "audioDrop":            ["copy", "slider", "input", "none"],
                "resDrop":              ["copy", "max", "min"]}


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        timer.print("Starting")
        self.setWindowTitle("TurnH264")
        self.resize(400, 400)
        self.setMinimumSize(320, 260)
        self.addWidgets()
        self.stopped_preemptively = False
        # this is also called every time ffmpeg is run
        self.ffmpeg_path = ffmpeg_utils.get_ffmpeg()
        if self.ffmpeg_path == None:  # ffmpeg wasn't found
            self.workButton.setEnabled(False)
            self.statDlg.setText("ffmpeg not detected, obtaining ffmpeg...")
            self.getFfmpegThread = threading.Thread(
                target=ffmpeg_utils.download)
            self.dlWaitThread = threading.Thread(target=self.dlWait)
            self.getFfmpegThread.start()
            self.dlWaitThread.start()

    def dlWait(self):
        self.getFfmpegThread.join()
        self.workButton.setEnabled(True)
        self.statDlg.setText("ffmpeg download finished.")

    def addWidgets(self):
        timer.start()

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
        self.changeButtons(0)
        self.inputText.textChanged.connect(self.inputChanged)
        self.inputButton.clicked.connect(self.inputButtonClicked)
        self.outputDrop.currentTextChanged.connect(self.inputChanged)
        self.audioDrop.currentTextChanged.connect(self.audioDropChanged)
        self.resDrop.currentTextChanged.connect(self.resDropChanged)
        self.threads.valueChanged.connect(self.threadChanged)
        self.workButton.clicked.connect(self.workClicked)
        self.yesButton.clicked.connect(self.yesClicked)
        self.noButton.clicked.connect(self.noClicked)
        self.fps.textChanged.connect(self.inputChanged)
        timer.print("widgets connected")
        self.speedDrop.setCurrentIndex(3)
        self.QProgress.setValue(0)
        self.QProgress.setMinimum(0)
        self.QProgress.setMaximum(100)
        self.inputChanged()
        self.audioDropChanged()
        self.threadChanged()
        self.resDropChanged()

    def changeButtons(self, num):
        '''0 = Start, 1 = Stop, 2 = Yes/No dialog'''
        self.workButton.setVisible(True)
        self.yesButton.setVisible(False)
        self.noButton.setVisible(False)
        if num == 0:
            self.workButton.setText("Start")
        if num == 1:
            self.workButton.setText("Stop")
        if num == 2:
            self.workButton.setVisible(False)
            self.noButton.setVisible(True)
            self.yesButton.setVisible(True)

    def realOutput(self):
        return self.outputInput.text().replace("%Input_Path%", os.path.dirname(self.inputText.text()))

    def WidgetsEditable(self, num):
        for i in widget_layout:
            if widget_layout[i][-2] == "YE_HIDE":
                exec(f"self.{i}.setEnabled(bool({num}))")

    def inputChanged(self):
        self.inputText.setText(self.inputText.text().replace("\"", ""))
        if self.inputText.text() != "":
            text = "".join([
                "%Input_Path%/",  # input path
                os.path.basename(self.inputText.text()).split(".")[0],
                "-converted",
                (f"-{self.fps.text()}fps" if self.fps.text() != "" else "")
            ])
            now_extension = self.outputDrop.currentText()
            text = os.path.join(
                text, "%06d.png") if now_extension == "png" else text+"."+now_extension
            self.outputInput.setText(text)
        else:
            self.outputInput.setText("")
        self.outputInput.update()

    def inputButtonClicked(self):
        home = str("c:\\users\\" if sys.platform == "win32" else
                   os.path.expanduser("~"))
        file = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select input file", home)[0]
        self.inputText.setText(file)

    def audioDropChanged(self):
        """ copy = 0, slider = 1, input = 2"""
        index = self.audioDrop.currentIndex()
        audio_dict = ([False, False], [False, True],
                      [True, False], [False, False])
        self.aBitrateInput.setVisible(audio_dict[index][0])
        self.aBitrateSlider.setVisible(audio_dict[index][1])

    def resDropChanged(self):
        index = self.resDrop.currentIndex()
        self.resLine.setVisible(bool(index))

    def threadChanged(self):
        self.threadsDlgRatio.setText(
            f"{str(self.threads.value()).zfill(len(str(os.cpu_count())))} / {os.cpu_count()}")
        self.threadsDlgRatio.update()

    def noClicked(self):
        self.statDlg.setText("Awaiting input")
        self.workButton.setText("Start")
        self.WidgetsEditable(1)
        self.changeButtons(0)

    def yesClicked(self):
        if self.stopped_preemptively == True:
            if self.outputDrop.currentText() != "png":
                os.remove(self.realOutput())
            else:
                shutil.rmtree(os.path.dirname(self.realOutput()))
            self.noClicked()
            self.stopped_preemptively = False
            return
        self.startFfmpeg()

    def byteFormat(self, size, suffix="B"):
        '''modified version of: https://stackoverflow.com/a/1094933'''
        size = "".join([val for val in size if val.isnumeric()])
        if size != "":
            size = int(size)
            for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti']:
                if abs(size) < 2**10:
                    return f"{size:3.1f}{unit}{suffix}"
                size /= 2**10
            return f"{size:3.1f}{unit}{suffix}"
        else:
            return f"N/A{suffix}"

    def startFfmpeg(self):
        self.ffmpeg_path = ffmpeg_utils.get_ffmpeg()
        self.statDlg.setText("Converting...")
        timer.start()

        vindex = self.vDrop.currentIndex()
        aindex = self.audioDrop.currentIndex()
        rindex = self.resDrop.currentIndex()
    # handle resolutions
        reses = {}
        reses['input_res'] = [int(val.split("=")[1]) for val in subprocess.check_output(
                             [self.ffmpeg_path[1], '-v', 'error', '-show_entries', 'stream=width,height',
                              '-of', 'default=noprint_wrappers=1', self.inputText.text()]).
                              decode("utf-8").split("\n")[:-1]]
        reses['resLine'] = int(self.resLine.text()
                               if self.resLine.text() != "" else 0)
        reses['restio'] = (reses['resLine']/max(reses['input_res']) if rindex ==
                           1 else reses['resLine']/min(reses['input_res']) if rindex == 2 else 1)
        reses['new_res'] = [val*reses['restio'] for val in reses['input_res']]
        timer.print(reses['input_res'])
        if type(reses['new_res'][0]) != int:
            if not reses['new_res'][0].is_integer() or not reses['new_res'][1].is_integer():
                self.statDlg.setText(
                    "Warning: the specified resolution is not an int.\nresult may be imprecise")
                timer.print(f"{reses['new_res']} is imprecise, flooring...")
        reses['new_res'] = [math.floor(val)-(math.floor(val) % 2)
                            for val in reses['new_res']]
        ffargs = {"path": self.ffmpeg_path[0],
                  "input":   ['-i', self.inputText.text()],
                  "output":  self.realOutput(),
                  "extension": self.outputDrop.currentText(),
                  "vidbr":   "".join([val for val in self.vBitrate.text() if val.isnumeric()]),
                  "audbr_s": str(self.aBitrateSlider.value()*32)+"k",
                  "audbr_i": self.aBitrateInput.text(),
                  "threads": ['-threads', str(self.threads.value())],
                  "speedDrop":   ['-preset', self.speedDrop.currentText()],
                  "fps":     "".join([val for val in self.fps.text() if val.isnumeric()]),
                  "scale":      f"{reses['new_res'][0]}:{reses['new_res'][1]}"
                  }
        print(ffargs)
        if self.outputDrop.currentText() == "png":
            if not os.path.exists(os.path.dirname(ffargs['output'])):
                os.mkdir(os.path.dirname(ffargs['output']))
        # tmpdir for progress bar
        tmpdir = self.inputText.text() + '.tmp'
        if os.path.exists(tmpdir):
            os.remove(tmpdir)
        tmpfile = open(tmpdir, "w")

        command = sum([[ffargs['path'], '-y'],
                        ffargs['input'],
                        ffargs['threads'],
                        ffargs['speedDrop'],
                        ['-progress', '-', '-nostats'],
                        ['-r', ffargs['fps']] if ffargs['fps'] != "" else [],
                        ], [])
        if self.outputDrop.currentText() != "png":
            command += sum([['-c:v', 'libx264'],
                                 ['-map', '0:v:?', '-map',
                                 '0:a:?', '-map_metadata', "0"],
                                 ['-b:v', ffargs['vidbr'] + "k"] if vindex == 0 and ffargs['vidbr'] != "" else
                                 ['-crf', ffargs['vidbr']] if vindex == 1 and ffargs['vidbr'] != "" else
                                 ['-q:v', '0'],
                                 ['-c:a', 'copy'] if aindex == 0 else
                                 ['-b:a', ffargs['audbr_s']] if aindex == 1 else
                                 ['-b:a', ffargs['aidbr_i']
                                  ] if aindex == 2 else ['-an']
                                 ], [])
        command += sum([['-vf', f'scale={ffargs["scale"]}'] if rindex != 0 and reses['input_res'] != reses['new_res'] else [],
                             [ffargs['output']],
                             ], [])
        print(" ".join(command))
        # return
        ffmpegThread = subprocess.Popen(command,
                                        stdout=tmpfile, stderr=tmpfile)
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
            self.WidgetsEditable(0)
            self.statDlg.setText(
                "Conversion stopped. delete unfinished video?")
            self.changeButtons(2)

        def ffmpegWait():
            ffmpegThread.wait()
            with open(tmpdir, "r") as file:
                lines = file.readlines()
                timer.print("".join(lines[-12:]))
            os.remove(tmpdir)
            self.statDlg.setText("Conversion complete!")
            self.workButton.clicked.disconnect()
            self.workButton.clicked.connect(self.workClicked)
            self.changeButtons(0)
            self.WidgetsEditable(1)
            timer.print("\nffmpeg finished")
            self.stopped_preemptively = False

        def ffmpegWatch():
            time.sleep(0.5)
            # ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 input.mp4
            video_frame = subprocess.check_output([
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-count_frames", "-show_entries", "stream=nb_read_frames",
                "-print_format", "csv", self.inputText.text()])

            video_frame_total = video_frame.decode("utf-8").strip()
            self.QProgress.setMaximum(video_frame_total)
            video_frame_total = int(
                "".join([val for val in video_frame_total if val.isnumeric()]))
            print("\n"*4)
            while (ffmpegThread.poll() == None):
                file = open(tmpdir, "r")
                lines = file.readlines()
                file.close()
                if len(lines) > 12:
                    try:
                        last_line = [i.strip().split("=") for i in lines[-12:]]
                        line_dict = {data[0]: data[1] for data in last_line}
                    except:
                        continue
                    progress = progressBar(int(line_dict['frame']), video_frame_total,
                                         length=50, color=False, nullp=".", fill="!", end="")
                    used_list = ["frame: "+line_dict['frame'] +
                        " / "+str(video_frame_total),
                        line_dict['fps']+" fps",
                        "speed: " + line_dict['speed'],
                        "\n"+progress, str(round((int(line_dict['frame']) / video_frame_total)*100, 2))+"%",
                        "\nbitrate: " + line_dict['bitrate'],
                        "size: " + self.byteFormat(line_dict['total_size'])]
                    print(", ".join(used_list))
                    self.QProgress.setValue(line_dict['frame'])
                time.sleep(0.5)

        self.changeButtons(1)
        self.WidgetsEditable(0)
        self.workButton.clicked.disconnect()
        self.workButton.clicked.connect(ffmpegCancel)
        self.ffmpegWaitThread = threading.Thread(target=ffmpegWait)
        self.ffmpegWatchThread = threading.Thread(target=ffmpegWatch)
        self.ffmpegWatchThread.start()
        self.ffmpegWaitThread.start()

    def workClicked(self):
        input_file = self.inputText.text()
        if input_file.startswith("file://"):
            self.inputText.setText(input_file.replace("file://", ""))
            input_file = self.inputText.text()
        work_step = self.workButton.text()
        if self.statDlg.text() == "Awaiting input":
            self.stopped_preemptively = False
        if work_step == "Start":
            if not os.path.exists(input_file):
                self.statDlg.setText("Input file does not exist.")
                print("File not found")
                return
        ffmpeg_output = self.realOutput()
        if os.path.exists(ffmpeg_output):
            print(ffmpeg_output, "already exists.")
            self.statDlg.setText("Output already exists, overwrite?")
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
