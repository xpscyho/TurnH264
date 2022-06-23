import os
import signal
import subprocess
import sys
import threading
import time

# these are used, but run in exec so they are shown as unused
from PySide6 import QtWidgets
from PySide6.QtCore import Qt


class timer:  # timer setup ####
    def start():
        '''start the timer'''
        timer.timer_start_time = time.time()

    def print(instr):
        '''print and restart the timer'''
        if timer.timer_start_time is None:
            timer.start()
            print("Started timer")
            return
        now = time.time()
        diff = (now - timer.timer_start_time) * 1000
        timer.timer_start_time = now
        print(f"{instr}: ms{diff:.4f}")
        return diff

    def poll(instr):
        '''print without restarting the timer'''
        now = time.time()
        print(f"{instr}: ms{(now - timer.timer_start_time) * 1000:.4f}")

    def reset():
        '''restart the timer'''
        timer.timer_start_time = time.time()


timer.reset()
widget_layout = {
    "input_dialog":         ["Label", "Input video:",   "Center", "YE_HIDE", (1, 0, 1, 1)],
    "input_text":           ["LineEdit",                  "Left", "YE_HIDE", (1, 1, 1, 2)],
    "input_button":         ["ToolButton", ". . .",       "Left", "YE_HIDE", (1, 3, 1, 1)],
    "help_button":          ["ToolButton", "  ?  ",      "Right", "YE_HIDE", (1, 4, 1, 1)],
    "output_dialog":        ["Label", "Output:",        "Center", "YE_HIDE", (2, 0, 1, 1)],
    "output_text_input":    ["LineEdit",                  "Left", "YE_HIDE", (2, 1, 1, 2)],
    "outputDrop":           ["ComboBox",                  "Left", "YE_HIDE", (2, 3, 1, 2)],

    "v_bitrate_dialog":     ["Label", "Video bitrate:", "Center", "YE_HIDE", (3, 0, 1, 1)],
    "video_bitrate":        ["LineEdit",                  "Left", "YE_HIDE", (3, 1, 1, 2)],
    "videoDrop":            ["ComboBox",                  "Left", "YE_HIDE", (3, 3, 1, 2)],
    "a_bitrate_dialog":     ["Label", "Audio bitrate:", "Center", "YE_HIDE", (4, 0, 1, 1)],
    "audio_bitrate_slider": ["Slider",      "Horizontal", "Left", "YE_HIDE", (4, 1, 1, 2)],
    "audio_bitrate_input":  ["LineEdit",                  "Left", "YE_HIDE", (4, 1, 1, 2)],
    "audioDrop":            ["ComboBox",                  "Left", "YE_HIDE", (4, 3, 1, 2)],
    "threads_dialog":       ["Label", "Threads:",       "Center", "YE_HIDE", (5, 0, 1, 1)],
    "thread":               ["Slider",      "Horizontal", "Left", "YE_HIDE", (5, 1, 1, 2)],
    "threads_dialog_ratio": ["Label", "",               "Center", "YE_HIDE", (5, 3, 1, 2)],
    "speed_dialog":         ["Label", "Speed:",         "Center", "YE_HIDE", (6, 0, 1, 1)],
    "speed":                ["ComboBox",                  "Left", "YE_HIDE", (6, 1, 1, 2)],
    "fps_dialog":           ["Label", "fps:",           "Center", "YE_HIDE", (7, 0, 1, 1)],
    "fps":                  ["LineEdit",                  "Left", "YE_HIDE", (7, 1, 1, 2)],

    "status_dialog":        ["Label", "Awaiting input", "Center", "NO_HIDE", (8, 0, 1, 5)],
    "work_button":          ["PushButton", "Start",       "Left", "NO_HIDE", (9, 0, 1, 5)],
    "yes_button":           ["PushButton", "Continue",    "Left", "NO_HIDE", (9, 0, 1, 3)],
    "no_button":            ["PushButton", "Cancel",      "Left", "NO_HIDE", (9, 3, 1, 2)]
}
widget_boxes = {
    "audio_bitrate_slider": [1, 8, 0.75],
    "thread":               [1, os.cpu_count(), 0.75],
    "speed":                ["veryslow", "slower", "slow",
                             "medium",   "fast",   "faster",
                             "veryfast", "ultrafast"],
    "outputDrop":           ["mp4", "mkv", "avi", "ts", "png"],
    "videoDrop":            ["kb/s", "crf", "q:v"],
    "audioDrop":            ["copy", "slider", "input", "none"],
}


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        timer.print("Starting")
        self.setWindowTitle("TurnH264")
        self.resize(320, 260)
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
        self.thread.valueChanged.connect(self.threadChanged)
        self.work_button.clicked.connect(self.workClicked)
        self.yes_button.clicked.connect(self.yesClicked)
        self.no_button.clicked.connect(self.noClicked)
        timer.print("widgets connected")
        self.inputChanged()
        self.audioDropChanged()
        self.threadChanged()
    # def addButtons(self):

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
        self.output_text_input.setText(
            "" if self.input_text.text() == "" else
            "%Input_Path%/"  # input path
            + (self.input_text.text()).split("/")[-1].split(".")[0]
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

    def startFfmpeg(self):
        timer.reset()
        local_ffmpeg = os.path.dirname(os.path.realpath(__file__)) + "/ffmpeg"
        vindex = self.videoDrop.currentIndex()
        aindex = self.audioDrop.currentIndex()
        ffargs = {
            "path": local_ffmpeg if os.path.exists(local_ffmpeg) else "ffmpeg",
            "input": self.input_text.text(),
            "output": self.realOutput(),
            "vidbr": "".join([val for val in self.video_bitrate.text() if val.isnumeric()]),
            "audbr_s": str(self.audio_bitrate_slider.value()*32)+"k",
            "audbr_i": self.audio_bitrate_input.text(),
            "threads": str(self.thread.value()),
            "speed": self.speed.currentText(),
            "fps": "".join([val for val in self.fps.text() if val.isnumeric()])
        }
        command = sum([[ffargs['path'], '-y'],
                       ['-i', ffargs['input'], '-c:v', 'libx264'],
                       ['-threads', ffargs['threads']],
                       ['-b:v', ffargs['vidbr'] + "k"] if vindex == 0 and ffargs['vidbr'] != "" else
                       ['-crf', ffargs['vidbr']] if vindex == 1 else
                       ['-q:v', ffargs['vidbr'] if ffargs['vidbr'] != "" else "0"],
                       ['-c:a', 'copy'] if aindex == 0 else [],
                       ['-b:a', ffargs['audbr_s']] if aindex == 1 else [],
                       ['-b:a', ffargs['aidbr_i']] if aindex == 2 else [],
                       ['-an'] if aindex == 3 else [],
                       ['-r', ffargs['fps']] if ffargs['fps'] != "" else [],
                       ['-map', '0:v:?', '-map', '0:a:?'],
                       [ffargs['output']]], [])
        ffmpegThread = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        timer.print("ffmpeg initialized")

        def ffmpegCancel():
            timer.print("killing ffmpeg")
            if sys.platform == "win32":  # windows doesn't use SIGINT for some reason
                while ffmpeg_thread_main.poll() is None:
                    os.kill(ffmpeg_thread_main.pid, signal.CTRL_C_EVENT)
                    time.sleep(3)
            else:
                while ffmpegThread.poll() is None:
                    ffmpegThread.send_signal(signal.SIGINT)
                    time.sleep(2.8)
            timer.print("\nkilled ffmpeg")
            self.work_button.clicked.disconnect()
            self.work_button.clicked.connect(self.workClicked)
            self.status_dialog.setText(
                "Conversion stopped. delete unfinished video?")
            self.changeButtons(2)
            self.stopped_preemptively = True

        def ffmpegWait():
            errors = ffmpegThread.communicate()
            ffmpegThread.wait()
            if ffmpegThread.returncode not in [0, 255]:
                timer.poll(f"({ffmpegThread.returncode}): ffmpeg failed")
                errors = "\n".join(errors[-1].
                                   decode("utf-8").
                                   rsplit("\n", 4)[-2:])
                self.status_dialog.setText(errors)
                print(errors)
                return errors
            else:
                self.status_dialog.setText("Conversion complete!")
            self.work_button.clicked.disconnect()
            self.work_button.clicked.connect(self.workClicked)
            self.changeButtons(0)
            self.WidgetsEditable(1)
            timer.print("\nffmpeg finished")
        self.status_dialog.setText("Converting...")
        self.changeButtons(1)
        self.WidgetsEditable(0)
        self.work_button.clicked.disconnect()
        self.work_button.clicked.connect(ffmpegCancel)
        self.ffmpegWaitThread = threading.Thread(target=ffmpegWait)
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
