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
        timer.timer_start_time = time.time()

    def print(instr):
        if timer.timer_start_time is None:
            timer.start()
            print("Started timer")
            return
        now = time.time()
        diff = (now - timer.timer_start_time) * 1000
        timer.timer_start_time = now
        print(f"{instr}: ms{diff:.4f}")
        return diff

    def reset():
        timer.timer_start_time = time.time()


timer.reset()


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        timer.print("Starting")
        self.setWindowTitle("TurnH264")
        self.resize(320, 260)
        self.setMinimumSize(320, 260)
        # force column 0 to fit content
        self.addwidgets()
        self.slider_changed()  # to update ratio

    def addwidgets(self):
        global widget_layout, widget_buttons, widget_boxes
        widget_layout = {
            "input_dialog":         ["Label", "Input video:",                         "Center", "YE_HIDE", (1, 0, 1, 1)],
            "output_dialog":        ["Label", "Output:",                              "Center", "YE_HIDE", (2, 0, 1, 1)],
            "v_bitrate_dialog_1":   ["Label", "Video bitrate:",                       "Center", "YE_HIDE", (3, 0, 1, 1)],
            "v_bitrate_dialog_2":   ["Label", "kb/s",                                 "Center", "YE_HIDE", (3, 3, 1, 2)],
            "a_bitrate_dialog_1":   ["Label", "Audio bitrate:",                       "Center", "YE_HIDE", (4, 0, 1, 1)],
            "threads_dialog":       ["Label", "Threads:",                             "Center", "YE_HIDE", (5, 0, 1, 1)],
            "threads_dialog_ratio": ["Label", "",                                     "Center", "YE_HIDE", (5, 3, 1, 2)],
            "speed_dialog":         ["Label", "Speed:",                               "Center", "YE_HIDE", (6, 0, 1, 1)],
            "status_dialog":        ["Label", "Awaiting input",                       "Center", "NO_HIDE", (7, 0, 1, 5)],

            "video_bitrate":        ["LineEdit", "",                                    "Left", "YE_HIDE", (3, 1, 1, 2)],
            "input_text":           ["LineEdit", "",                                    "Left", "YE_HIDE", (1, 1, 1, 2)],
            "input_file":           ["ToolButton", ". . .",                             "Left", "YE_HIDE", (1, 3, 1, 1)],
            "help_button":          ["ToolButton", "  ?  ",                            "Right", "YE_HIDE", (1, 4, 1, 1)],
            "output_text_input":    ["LineEdit", "",                                    "Left", "YE_HIDE", (2, 1, 1, 2)],
            "output_ext":           ["ComboBox",                                        "Left", "YE_HIDE", (2, 3, 1, 2)],
            "audio_which":          ["ComboBox",                                        "Left", "YE_HIDE", (4, 3, 1, 2)],
            "audio_bitrate_slider": ["Slider",                            "Horizontal", "Left", "YE_HIDE", (4, 1, 1, 2)],
            "audio_bitrate_input":  ["LineEdit", "",                                    "Left", "YE_HIDE", (4, 1, 1, 2)],
            "threads":              ["Slider",                            "Horizontal", "Left", "YE_HIDE", (5, 1, 1, 2)],
            "speed":                ["ComboBox",                                        "Left", "YE_HIDE", (6, 1, 1, 2)],
        }
        widget_buttons = {
            "start_button":         ["PushButton", "Start",                             "Left", "NO_HIDE", (8, 0, 1, 5)],
            "stop_button":          ["PushButton", "Stop",                              "Left", "NO_HIDE", (8, 0, 1, 5)],
            "continue_button":      ["PushButton", "Yes",                               "Left", "NO_HIDE", (8, 0, 1, 3)],
            "cancel_button":        ["PushButton", "Cancel",                            "Left", "NO_HIDE", (8, 3, 1, 2)],
        }
        widget_combined = {**widget_layout, **widget_buttons}

        widget_boxes = {
            "audio_bitrate_slider": [1, 8, 0.75],
            "threads":              [1, os.cpu_count(), 0.75],
            "speed": ["veryslow", "slower", "slow", "medium", "fast", "faster", "veryfast", "ultrafast"],
            "output_ext": ["mp4", "mkv", "avi", "ts", "png"],
            "audio_which": ["copy", "slider", "input"],
        }

        def parse_layout(widgetDict):
            self.layout = QtWidgets.QGridLayout(self)

            for key in widgetDict:
                layout = widgetDict[key][-1]
                val = widgetDict[key]
                given = "self."+key
                exec(f"{given} = QtWidgets.Q{val[0]}()")
                if val[0] in ["Label", "PushButton", "ToolButton"]:  # text
                    exec(f"{given}.setText('{val[1]}')")
                if val[0] in ["Label", "LineEdit"]:  # alignment
                    exec(f"{given}.setAlignment(Qt.Align{val[2]})")
                if val[0] == "ComboBox":  # box items
                    exec(f"{given}.addItems({widget_boxes[key]})")
                if val[0] == "Slider":  # sliders
                    exec(
                        f"{given}.setRange({widget_boxes[key][0]}, {widget_boxes[key][1]})")
                    exec(
                        f"{given}.setValue({widget_boxes[key][1]*widget_boxes[key][2]})")
                    exec(f"{given}.setOrientation(Qt.Orientation.{val[-4]})")
                # apply layout
                exec(f"self.layout.addWidget({given}, {layout[0]}, \
                      {layout[1]}, {layout[2]}, {layout[3]})")

        parse_layout(widget_combined)
        timer.print("Widgets added")
        # exit()
        self.hide_show_widgets(1, 0, 0)
        # if input_text changed, update output_text_input
        self.input_text.textChanged.connect(self.input_text_changed)
        self.input_file.clicked.connect(self.input_file_select_clicked)
        self.output_ext.currentTextChanged.connect(self.output_box_changed)
        self.audio_which.currentTextChanged.connect(self.audio_box_changed)
        self.threads.valueChanged.connect(self.slider_changed)
        self.start_button.clicked.connect(self.start_button_clicked)
        self.stop_button.clicked.connect(self.stop_button_clicked)
        self.continue_button.clicked.connect(self.overwrite_button_clicked)
        self.cancel_button.clicked.connect(self.cancel_button_clicked)
        self.audio_bitrate_input.setToolTip("non-numbers will be stripped.")
        self.video_bitrate.setToolTip("non-numbers will be stripped.")
        self.v_bitrate_dialog_2.setToolTip("1 mb = 1000 kb")
        self.audio_bitrate_input.hide()
        self.audio_bitrate_slider.hide()

    def reset_dialog(self):
        self.status_dialog.setText(widget_layout["status_dialog"][1])
        for key in widget_buttons:
            exec(f"self.{key}.setText('{widget_buttons[key][1]}')")

    def input_text_changed(self):
        if self.input_text.text() == "":
            self.output_text_input.setText("")
        else:
            self.output_text_input.setText("%Input_Path%/"+(self.input_text.text()).split(
                "/")[-1].split(".")[0]+"-converted."+self.output_ext.currentText())

    def input_file_select_clicked(self):
        if sys.platform == "win32":
            self.input_text.setText(QtWidgets.QFileDialog.getOpenFileName(
                self, "Select input file", "c:\\users\\")[0])
        else:
            file = QtWidgets.QFileDialog.getOpenFileName(
                self, "Select a video file", os.path.expanduser("~"))
            self.input_text.setText(file[0])
        print("selected"+self.input_text.text())

    def hide_show_widgets(self, inst_start, int_stop, int_que):
        self.start_button.setHidden(not bool(inst_start))
        self.stop_button.setHidden(not bool(int_stop))
        self.continue_button.setHidden(not bool(int_que))
        self.cancel_button.setHidden(not bool(int_que))

    def output_box_changed(self):
        extension = "."+self.output_ext.currentText()
        if self.output_ext.currentText() == "png":
            extension = "/%06d.png"
        self.output_text_input.setText("%Input_Path%/"+(self.input_text.text()).split(
            "/")[-1].split(".")[0]+"-converted"+extension)

    def audio_box_changed(self):
        audio_dict = {"copy": [True, True], "slider": [False, True],
                      "input": [True, False]}
        for i in audio_dict:
            if self.audio_which.currentText() == i:
                self.audio_bitrate_input.setVisible(audio_dict[i][0])
                self.audio_bitrate_slider.setVisible(audio_dict[i][1])

    def slider_changed(self):
        self.threads_dialog_ratio.setText(
            f"{str(self.threads.value()).zfill(len(str(os.cpu_count())))} / {os.cpu_count()}")
        self.threads_dialog_ratio.update()

    def enable_disable_widgets(self, inint):
        '''inint = 0: disable, inint = 1: enable'''
        for i in widget_layout:
            if widget_layout[i][-2] == "YE_HIDE":
                exec(f"self.{i}.setEnabled(bool({inint}))")

    def modify_status(self, text):
        self.status_dialog.setText(text)
        self.status_dialog.update()

    def get_output_file(self):
        return self.output_text_input.text().replace("%Input_Path%", os.path.dirname(self.input_text.text()))

    def start_button_clicked(self):
        self.input = self.input_text.text()
        if not os.path.exists(self.input):
            self.status_dialog.setText("Input file does not exist.")
            self.status_dialog.update()
            return
        ffmpeg_output = self.get_output_file()
        if os.path.exists(ffmpeg_output):
            print(ffmpeg_output, "already exists.")
            self.status_dialog.setText("Output already exists, overwrite?")
            self.hide_show_widgets(0, 0, 1)
            self.enable_disable_widgets(False)
            # self.overwrite_button_clicked()
        else:
            print("output does not exist.")
            self.overwrite_button_clicked()

    def overwrite_button_clicked(self):
        self.hide_show_widgets(1, 1, 0)
        self.modify_status("Converting...")
        self.enable_disable_widgets(0)
        self.run_ffmpeg()

    def cancel_button_clicked(self):
        self.reset_dialog()
        self.hide_show_widgets(1, 0, 0)
        self.enable_disable_widgets(1)

    def stop_button_clicked(self):
        self.hide_show_widgets(1, 0, 0)
        self.enable_disable_widgets(0)
        self.modify_status("Conversion stopped. delete unfinished video?")
        self.hide_show_widgets(0, 0, 1)
        self.continue_button.setText("Yes")
        self.cancel_button.setText("No")
        self.continue_button.clicked.disconnect()
        self.continue_button.clicked.connect(self.delete_mp4)

    def delete_mp4(self):
        if not self.output_text_input.text().split("/")[0] == "%Input_Path%":
            ffmpeg_output = self.output_text_input.text()
        else:
            ffmpeg_output = os.path.dirname(self.input_text.text()) \
                + "/" + self.output_text_input.text().split("/")[-1]
        if os.path.exists(ffmpeg_output):
            os.remove(ffmpeg_output)
            print(f"removed {self.output_text_input.text()}")
        self.enable_disable_widgets(1)
        self.continue_button.clicked.disconnect()
        self.continue_button.clicked.connect(self.overwrite_button_clicked)
        self.cancel_button_clicked()

    def run_ffmpeg(self):
        timer.reset()
        ffmpeg_input_file = self.input_text.text()
        ffmpeg_video_bitrate = "".join(
            [val for val in self.video_bitrate.text() if val.isnumeric()]) + "k"
        ffmpeg_audio_bitrate = ""
        if self.audio_which.currentText() == "slider":
            ffmpeg_audio_bitrate = str(
                self.audio_bitrate_slider.value()*32) + "k"
        elif self.audio_which.currentText() == "input":
            ffmpeg_audio_bitrate = str(self.audio_bitrate_input.text()) + "k"

        ffmpeg_output = self.get_output_file()
        if self.output_ext.currentText() == "png":
            if not os.path.exists(os.path.dirname(ffmpeg_output)):
                os.makedirs(os.path.dirname(ffmpeg_output))
        local_ffmpeg = os.path.dirname(os.path.realpath(__file__)) + "/ffmpeg"
        ffmpeg_path = local_ffmpeg if os.path.exists(
            local_ffmpeg) else "ffmpeg"
        print("using:", ffmpeg_path)
        command = [ffmpeg_path]  # get ffmpeg path
        command.extend(['-y'])
        command.extend(['-i', ffmpeg_input_file])
        command.extend(['-threads', str(self.threads.value())])
        command.extend(['-preset', self.speed.currentText()])
        if self.output_ext.currentText() != "png":
            command.extend(['-c:v', 'libx264'])
            command.extend(['-b:v', ffmpeg_video_bitrate]
                           if self.video_bitrate.text() != "" else ["-q:v", "0"])
            command.extend(
                ['-c:a', 'copy'] if self.audio_which.currentText() == "copy" else ["aac"])
            command.extend(['-b:a', ffmpeg_audio_bitrate]
                           if ffmpeg_audio_bitrate != "" else ["-q:a", "0"])
            command.extend(['-map', '0:v:?', '-map', '0:a:?'])
        command.extend([ffmpeg_output])
        print(command)
        # run ffmpeg in a separate thread
        ffmpeg_thread_main = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        timer.print("ffmpeg initalized")

        def kill_function():
            print("killing ffmpeg")
            if sys.platform == "win32":  # windows doesn't use SIGINT for some reason
                while ffmpeg_thread_main.poll() is None:
                    os.kill(ffmpeg_thread_main.pid, signal.CTRL_C_EVENT)
                    time.sleep(3)
            else:
                while ffmpeg_thread_main.poll() is None:
                    ffmpeg_thread_main.send_signal(signal.SIGINT)
                    time.sleep(2.8)
            print("\nkilled ffmpeg")

        def ffmpeg_waiting():
            print("waiting for ffmpeg to finish")
            errors = ffmpeg_thread_main.communicate()
            ffmpeg_thread_main.wait()
            if ffmpeg_thread_main.returncode != 0:
                if not self.continue_button.isVisible():
                    print("ffmpeg failed")
                    self.hide_show_widgets(1, 0, 0)
                    self.enable_disable_widgets(1)
                    errors = "\n".join(
                        errors[-1].decode("utf-8").rsplit("\n", 4)[-3:])
                    self.resize(self.width()+50, self.height())
                    self.status_dialog.setText(str(errors))
                    print(errors)
                    # if errors contains "invalid argument",
                    if "invalid argument" in errors[-1]:
                        self.status_dialog.setText(
                            "Invalid argument, Please check your input.")
                    return errors
            print("\nffmpeg finished")
            if not self.continue_button.isVisible():
                self.status_dialog.setText("Conversion complete!")
                self.hide_show_widgets(1, 0, 0)
                self.enable_disable_widgets(1)

        self.stop_button.clicked.connect(kill_function)
        ffmpeg_thread_wait = threading.Thread(target=ffmpeg_waiting)
        ffmpeg_thread_wait.start()


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    main_app_window = MainWindow()
    main_app_window.show()
    sys.exit(app.exec())
