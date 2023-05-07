#!/usr/bin/python
from __future__ import annotations

import os
# import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from pprint import pprint

import ffmpeg
from cfg_argparser import CfgDict
from PySide6 import QtGui, QtWidgets
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFrame, QLabel, QLineEdit,
                               QProgressBar, QPushButton, QSlider, QToolButton,
                               QWidget)

from utilities import Timer, ffmpeg_utils

CPU_COUNT = os.cpu_count()


def byteFormat(size, suffix="B"):
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


@dataclass
class Widget:
    #              (x-pos, height, width)
    position: tuple[int,   int,    int]
    name: str
    widget: QFrame
    # data dictating how the assembler will configure the widget
    data: dict[str, str | bool]
    # Still iffy about this one
    hideable: bool = True


class StatusLabel(QLabel):
    def __init__(self):
        super().__init__()

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value
        self.setText(self._status)

    @status.deleter
    def status(self):
        del self._status


autosave_bar = (
    Widget((1, 1, 1), "autosave", QCheckBox, {"text": "Autosave"}),
    Widget((0, 1, 1), "save", QPushButton, {"text": "save"}),
    Widget((2, 1, 2), "status", StatusLabel, {})  # {"text": "Ready!!!!!!!!!!!!!!!!!!!!!!!!!!"})
)

input_bar = (
    Widget((0, 1, 1), "dialog", QLabel, {"align": "Center", "text": "Input:", }),
    Widget((1, 1, 2), "text", QLineEdit, {"align": "Right", }),
    Widget((3, 1, 1), "button", QPushButton, {"text": " . . . "}),
)

output_bar = (
    Widget((0, 1, 1), "dialog", QLabel, {"align": "Center", "text": "Output:", }),
    Widget((1, 1, 2), "text", QLineEdit, {"align": "Right", }),
    Widget((3, 1, 1), "dropdown", QComboBox, {"items": ["mp4", "mkv", "avi", "ts", "png"]}),
)

video_bar = (
    Widget((0, 1, 1), "dialog", QLabel, {"align": "Center", "text": "Video bitrate:"}),
    Widget((1, 1, 2), "bitrate", QLineEdit, {"align": "Left"}),
    Widget((3, 1, 1), "dropdown", QComboBox, {"items": ["KB/s", "MB/s", "crf"]}),
)

audio_bar = (
    Widget((0, 1, 1), "dialog", QLabel, {"align": "Center", "text": "Audio bitrate:"}),
    Widget((1, 1, 2), "bitrate", QLineEdit, {"align": "Left"}),
    Widget((1, 1, 2), "slider", QSlider, {"orientation": "Horizontal",
                                          "range": (1, 8),
                                          "value": 6}),
    Widget((3, 1, 1), "dropdown", QComboBox, {"items": ["copy", "slider", "input", "none"]}),
)

threads_bar = (
    Widget((0, 1, 1), "dialog", QLabel, {"align": "Center", "text": "Threads:"}),
    Widget((1, 1, 2), "slider", QSlider, {"orientation": "Horizontal",
                                          "range": (1, CPU_COUNT)}),
    Widget((3, 1, 1), "label", QLabel, {"align": "Center", "text": "NaN"}),
)

speed_bar = (
    Widget((0, 1, 1), "dialog", QLabel, {"align": "Center", "text": "Speed:"}),
    Widget((1, 1, 2), "dropdown", QComboBox, {"items": ["veryslow", "slower", "slow",
                                                        "medium",   "fast",   "faster",
                                                        "veryfast", "ultrafast"]}),
)
fps_bar = (
    Widget((0, 1, 1), "dialog", QLabel, {"align": "Center", "text": "fps:"}),
    Widget((1, 1, 2), "fps", QLineEdit, {"align": "Left", }),
)

res_bar = (
    Widget((0, 1, 1), "dialog", QLabel, {"align": "Center", "text": "resolution:"}),
    Widget((1, 1, 2), "line", QLineEdit, {"align": "Left", }),
    Widget((3, 1, 1), "dropdown", QComboBox, {"items": ["copy", "max", "min"]}),
)

stat_dialog = (
    Widget((0, 1, 4), "stats", StatusLabel, {"align": "Center",
                                             "text": "Awaiting input"}, hideable=False),
)

progress_bar = (
    Widget((0, 1, 4), "progress_bar", QProgressBar,  {}, hideable=False),
)

control_bar = (
    Widget((0, 1, 4), "start_button", QPushButton, {"text": "Start"}),
    # Widget((3, 1, 1), "auto_detect", QPushButton, {"text": "auto-detect"}),
    Widget((0, 1, 4), "stop_button", QPushButton, {"text": "Stop"}),
    Widget((0, 1, 3), "yes_button", QPushButton, {"text": "Continue"}),
    Widget((3, 1, 1), "no_button", QPushButton, {"text": "Cancel"})
)


class WidgetGroup:
    def __init__(self, lst: Iterable[Widget], widgets):
        assert len(lst) == len(widgets)
        for data, widget in zip(lst, widgets):
            setattr(self, data.name, widget)

    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): pass


class Status(Enum):
    READY = 0
    RUNNING = 1
    OVERWRITE = 2
    CONFIRM_CLOSE = 3


class Mode(Enum):
    START = 0
    STOP = 1
    YES_NO = 2


class MainWindow(QtWidgets.QWidget):
    def __init__(self, t: Timer, defaults: CfgDict):
        super(MainWindow, self).__init__()
        t.print("Starting")
        self.config = defaults
        self.setWindowTitle("TurnH264")
        self.resize(400, 450)
        self.setMinimumSize(320, 300)

        self.layout = QtWidgets.QGridLayout(self)
        self.barnum = 0

        def add_bar(bar, idx=None):
            if not idx:
                idx = self.barnum
            self.barnum += 1
            return MainWindow.widget_list_to_attrs(idx, bar, self.layout)
        self.save_bar = add_bar(autosave_bar)
        self.input_bar = add_bar(input_bar)
        self.output_bar = add_bar(output_bar)
        self.video_bar = add_bar(video_bar)
        self.audio_bar = add_bar(audio_bar)
        self.res_bar = add_bar(res_bar)
        self.threads_bar = add_bar(threads_bar)
        self.speed_bar = add_bar(speed_bar)
        self.fps_bar = add_bar(fps_bar)
        self.progress_bar: QProgressBar = add_bar(progress_bar).progress_bar
        self.stat_dialog: StatusLabel = add_bar(stat_dialog).stats
        self.control_bar = add_bar(control_bar)

        t.print("Created widgets")

        self.control_mode = Mode.START  # control_mode is a property with a setter method
        self.status = Status.READY

        # saving row
        with self.save_bar as sbar:
            self.add_to_config({'autosave': True},
                               sbar.autosave.setCheckState,
                               sbar.autosave.stateChanged,
                               widget_type=lambda b: {True: Qt.CheckState.Checked,
                                                      False: Qt.CheckState.Unchecked}.get(b, Qt.CheckState.Unchecked),
                               config_type=lambda state: {Qt.CheckState.Checked: True,  # why the hell does stateChanged return an int
                                                          Qt.CheckState.Unchecked: False}.get(sbar.autosave.checkState(), False)
                               )
            # sbar.autosave.stateChanged.connect(self.checkstate_to_bool)
            sbar.autosave.stateChanged.connect(self.autosave_changed)
            sbar.autosave.stateChanged.emit(sbar.autosave.checkState())
            sbar.save.clicked.connect(self.save_clicked)

        # input row
        with self.input_bar as ibar:
            self.add_to_config({'input': ''}, ibar.text.setText, ibar.text.textChanged)
            ibar.button.clicked.connect(self.input_button_clicked)
            ibar.text.textChanged.connect(self.input_changed)
            # ibar.text.textChanged.connect(
            #     lambda txt: self.control_bar.auto_detect.setEnabled(bool(txt)))
            self.input_changed(ibar.text.text())

        # output row
        with self.output_bar as obar:
            self.add_to_config({'output': ''}, obar.text.setText, obar.text.textChanged)
            self.add_to_config({'extension': 'mp4'}, obar.dropdown.setCurrentText, obar.dropdown.currentTextChanged)
            obar.dropdown.currentTextChanged.connect(self.ping_input_change)
            # obar.dropdown.currentIndexChanged.connect(self.ping_input_change)

        # video row
        with self.video_bar as vbar:
            vbar.bitrate.setValidator(QtGui.QIntValidator())
            self.add_to_config({'video_dropdown': 'crf'}, vbar.dropdown.setCurrentText,
                               vbar.dropdown.currentTextChanged)
            self.add_to_config({'video_bitrate': 16}, vbar.bitrate.setText, vbar.bitrate.textChanged,
                               config_type=int, widget_type=str)

        # audio row
        with self.audio_bar as abar:
            abar.bitrate.setValidator(QtGui.QIntValidator())  # Only accepts numbers
            self.add_to_config({'audio_dropdown': 'copy'}, abar.dropdown.setCurrentText,
                               abar.dropdown.currentTextChanged)
            abar.dropdown.currentIndexChanged.connect(self.audio_dropdown_changed)
            # update self.audio_bitrate
            self.add_to_config({'audio_bitrate': 192}, abar.bitrate.setText, abar.bitrate.textChanged,
                               config_type=int,
                               widget_type=str)
            self.add_to_config({'audio_bitrate': 192}, abar.slider.setValue, abar.slider.valueChanged,
                               config_type=lambda x: x * 32,
                               widget_type=lambda x: x // 32)
            abar.dropdown.currentIndexChanged.emit(abar.dropdown.currentIndex())

        # thread row
        with self.threads_bar as tbar:
            self.add_to_config({'threads': CPU_COUNT * 0.75}, tbar.slider.setValue, tbar.slider.valueChanged)
            tbar.slider.valueChanged.connect(lambda val: tbar.label.setText(f"{val}/{CPU_COUNT}"))
            tbar.slider.valueChanged.emit(self.config['threads'])

        # speed row
        with self.speed_bar as sbar:
            self.add_to_config({'speed': 'slow'}, sbar.dropdown.setCurrentText, sbar.dropdown.currentTextChanged)

        # fps row
        with self.fps_bar as fbar:
            self.add_to_config({'fps': 0}, fbar.fps.setText, fbar.fps.textChanged,
                               config_type=float, widget_type=str)
            fbar.fps.setValidator(QtGui.QDoubleValidator())  # Only accepts numbers
            fbar.fps.textChanged.connect(self.ping_input_change)
        # resolution row
        with self.res_bar as rbar:
            self.add_to_config({'res_dropdown': 'copy'}, rbar.dropdown.setCurrentText, rbar.dropdown.currentTextChanged)
            self.add_to_config({'resolution': 0}, rbar.line.setText, rbar.line.textChanged,
                               config_type=int, widget_type=str)
            rbar.line.setValidator(QtGui.QIntValidator())
            rbar.dropdown.currentIndexChanged.connect(self.res_dropdown_changed)
            rbar.dropdown.currentIndexChanged.emit(rbar.dropdown.currentIndex())

        with self.control_bar as cbar:
            cbar.start_button.clicked.connect(self.start_clicked)
            # cbar.auto_detect.clicked.connect(self.detect_clicked)
            cbar.stop_button.clicked.connect(self.stop_clicked)
            cbar.yes_button.clicked.connect(self.yes_clicked)
            cbar.no_button.clicked.connect(self.no_clicked)

            self.ffmpeg_thread = FfmpegThread(self)
            self.ffmpeg_thread.config = self.config  # bind the thread configs
            self.ffmpeg_thread.progress.connect(self.progress_bar.setValue)
            self.ffmpeg_thread.finished.connect(self.ffmpeg_finished)
            self.ffmpeg_thread.status.connect(lambda s: setattr(self.stat_dialog, "status", s))
            # self.ffmpeg_thread.probed.connect(self.retrieve_auto_detected_settings)

        t.print("Configured and connected widgets")

        pass

    def closeEvent(self, event):

        if self.status in (Status.RUNNING,):
            self.stat_dialog.status = "Are you sure? ffmpeg is still running."
            self.control_mode = Mode.YES_NO
            self.status = Status.CONFIRM_CLOSE
            event.ignore()
        else:
            event.accept()

    def add_to_config(self, name_and_default: dict,
                      setter_method: Callable, trigger_signal: Signal,
                      config_type: type | Callable = None,
                      widget_type: type | Callable = None,
                      default_fallback=lambda x: not x):
        '''A helper method to add widgets to the config file.

        Parameters
        ----------
        name_and_default : dict
            a {key: value} to add in the config file.
        setter_method : Callable
            the method that sets the proper value in the gui.
        trigger_signal : Signal
            the signal that emits when to update the key.
        config_type : type | Callable, optional
            a method/type that is called to convert the widget type to the config type, by default None
        widget_type : type | Callable, optional
            a method/type that is called to convert the config type to the widget type, by default None
        default_fallback : Callable, optional
            A condition in which to fall back to default, by default lambdax:x
        '''
        name, default = (*name_and_default.items(),)[0]
        if name not in self.config:
            self.config.update(name_and_default)

        if config_type is not None:  # convert incoming types to config type
            def conv_incoming(val): return config_type(val) if not default_fallback(val) else default
        else:
            def conv_incoming(val): return val if not default_fallback(val) else default

        def update_dict(val):
            try:
                self.save_bar.status.status = ""
                self.config.update({name: conv_incoming(val)})
                self.config.save()
            except Exception as e:
                err = f"updating key '{name}' failed: {e}"
                self.save_bar.status.status = err
                print(err)

        if widget_type is None:
            def conv_outcoming(): return self.config[name]
        else:
            def conv_outcoming(): return widget_type(self.config[name])

        setter_method(conv_outcoming())
        trigger_signal.connect(update_dict)

    @staticmethod
    def widget_list_to_attrs(idx: int, lst: Iterable[Widget], layout: QtWidgets.QLayout) -> WidgetGroup:
        new_attrs = []
        for widget in lst:
            # rprint(f"adding: {widget} ")
            new_widget = widget.widget()

            new_widget.hideable = widget.hideable

            # parse attributes
            MainWindow.parse_widget_attributes(new_widget, widget.data)
            new_attrs.append(new_widget)

            layout.addWidget(new_widget, idx, *widget.position)

        return WidgetGroup(lst, new_attrs)

    @staticmethod
    def parse_widget_attributes(widget: QWidget, data: dict):
        widget_methods = {
            "text": lambda w, data: w.setText(data),
            "align": lambda w, data: w.setAlignment(getattr(Qt, f"Align{data}")),
            "items": lambda w, data: w.addItems(data),
            # "default_index": lambda w, data: w.setCurrentIndex(data),
            "orientation": lambda w, data: w.setOrientation(getattr(Qt.Orientation, data)),
            "range": lambda w, data: w.setRange(*data),
            "value": lambda w, data: w.setValue(data)
        }
        for data_type in widget_methods:
            if data_type in data:
                widget_methods[data_type](widget, data[data_type])
                # rprint(f" ran {data_type}: {data[data_type]}")

    def autosave_changed(self):
        state = self.save_bar.autosave.checkState()
        self.config.save_on_change = {Qt.CheckState.Unchecked: False, Qt.CheckState.Checked: True}.get(state, False)
        self.config['autosave'] = self.config.save_on_change

    @Slot()
    def save_clicked(self):
        self.config.save()
        self.stat_dialog.status = "Config saved."

    @Slot()
    def input_button_clicked(self):
        """Makes a new window to get a file from the user"""
        home = str(Path("~").expanduser())
        file = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select input file", home
        )[0]
        if file:
            self.input_bar.text.setText(file)

    @Slot(str)
    def input_changed(self, value: str):
        if '"' in self.input_bar.text.text():
            self.input_bar.text.setText(value.replace("\"", ""))
        if self.input_bar.text.text():
            path = Path(self.input_bar.text.text())
            path = path.with_stem(f"{path.stem}-converted")
            if self.config['fps'] != 0:
                if self.config['fps'] % 1 == 0:
                    path = path.with_stem(f"{path.stem}-{int(self.config['fps'])}fps")
                else:
                    path = path.with_stem(f"{path.stem}-{self.config['fps']}fps")

            if self.config['extension'] == "png":
                path = path.with_stem(f"{path.stem}-%06d")
            path = path.with_suffix(f".{self.config['extension']}")
            self.output_bar.text.setText(str(path))
        else:
            self.output_bar.text.setText("")

    @Slot()
    def ping_input_change(self):
        self.input_changed(self.input_bar.text.text())

    @Slot(int)
    def audio_dropdown_changed(self, value: int):
        self.audio_bar.bitrate.setVisible({2: True}.get(value, False))
        self.audio_bar.slider.setVisible({1: True}.get(value, False))
        self.audio_bar.bitrate.setText(str(self.config['audio_bitrate']))
        self.audio_bar.slider.setValue(self.config['audio_bitrate'] // 32)

    @Slot(int)
    def res_dropdown_changed(self, value: int):
        self.res_bar.line.setVisible({0: False}.get(value, True))

    @Slot()
    def detect_clicked(self):
        # update the thread args
        self.ffmpeg_thread.path = self.config['input']
        # start the thread
        self.ffmpeg_thread.get_metadata()

    # @Slot(dict)
    # def retrieve_auto_detected_settings(self, dct: dict):
    #     CfgDict('tmp.json', dct).save()
    #     self.metadata = dct

    @Slot()
    def execute_ffmpeg(self):
        self.running()
        self.ffmpeg_thread.path = self.config['input']
        self.ffmpeg_thread.start()

        pass

    def running(self):
        self.status = Status.RUNNING
        self.control_mode = Mode.STOP
        self.stat_dialog.status = "Running..."

    @Slot()
    def ffmpeg_finished(self):
        self.control_mode = Mode.START
        self.status = Status.READY

    @Slot()
    def start_clicked(self):
        self.stat_dialog.status = "Start clicked."

        if not os.path.exists(self.config['input']):
            self.stat_dialog.status = "Input does not exist."
            return

        print(self.output_bar.text.text())
        if os.path.exists(self.output_bar.text.text()):
            # trigger confirmation
            self.status = Status.OVERWRITE
            self.stat_dialog.status = "Output exists. Overwrite?"
            self.control_mode = Mode.YES_NO  # Yes may run execute_ffmpeg
        else:
            self.execute_ffmpeg()

    @Slot()
    def yes_clicked(self):
        {
            Status.OVERWRITE: self.execute_ffmpeg,
            Status.CONFIRM_CLOSE: lambda: (self.stop_clicked(), self.close())
        }.get(self.status)()
        pass

    @Slot()
    def no_clicked(self):
        {
            Status.OVERWRITE: self.reset,
            Status.CONFIRM_CLOSE: self.running
        }.get(self.status)()
        pass

    @Slot()
    def stop_clicked(self):
        if self.status == Status.READY:
            raise NotImplementedError
        elif self.status == Status.RUNNING:
            self.reset()

        self.control_mode = Mode.START
        self.status = Status.READY
        self.ffmpeg_thread.terminate()
        self.progress_bar.setValue(0)
        self.stat_dialog.status = "Ffmpeg stopped."
        print("Thread stopped")
        pass

    def reset(self):
        self.stat_dialog.status = "Awaiting input"
        self.status = Status.READY
        self.control_mode = Mode.START

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value: Status):
        self._status = value

    @property
    def control_mode(self):
        return self._control_mode

    @control_mode.setter
    def control_mode(self, value: Mode):
        '''0 = Start, 1 = Stop, 2 = Yes/No'''
        # Start
        self.control_bar.start_button.setVisible({Mode.START: True}.get(value, False))
        # self.control_bar.auto_detect.setVisible({Mode.START: True}.get(value, False))
        # Stop
        self.control_bar.stop_button.setVisible({Mode.STOP: True}.get(value, False))
        # Yes / No
        self.control_bar.yes_button.setVisible({Mode.YES_NO: True}.get(value, False))
        self.control_bar.no_button.setVisible({Mode.YES_NO: True}.get(value, False))
        self._control_mode = value


class FfmpegThread(QThread):
    progress = Signal(int)
    status = Signal(str)
    probed = Signal(dict)
    metadata: dict
    config: dict
    path: str

    def run(self):
        self.metadata = self._get_metadata()
        video_stream = [stream for stream in self.metadata['streams'] if stream['codec_type'] == 'video'][0]
        duration = float(self.metadata['format']['duration'])
        framerate = eval(video_stream['r_frame_rate'])
        frame_count = int(duration * framerate)

        # self.status.emit()
        self.status.emit("Gathered metadata.")

        if self.config['fps']:
            frame_count = int(self.config['fps'] * duration)

        out: subprocess.Popen = self.get_ffmpeg_stream(video_stream).run_async(pipe_stdout=True)
        self.status.emit("configured ffmpeg.")

        while not out.poll():
            dct = {}
            line = ""
            while not 'progress' in line:
                line = out.stdout.readline().decode('utf-8').strip()
                time.sleep(0.01)
                k, v = line.split('=')
                dct[k] = v

            progress = int(dct['frame'])
            print(dct)
            dlg = [
                "Converting",
                f"%{int(dct['frame']) * 100/frame_count:.2f}   [{dct['frame']} / {frame_count}]",
                f"Total size: {byteFormat(dct['total_size'])}",
                f"speed: {dct['speed']}, fps: {dct['fps']}",
                f"bitrate: {dct['bitrate']}",
            ]
            if int(dct['drop_frames']):
                dlg.append(f"dropped frames: {dct['drop_frames']}")
            if int(dct['dup_frames']):
                dlg.append(f"duped framed: {dct['dup_frames']}")

            self.status.emit("\n".join(dlg))
            self.progress.emit(100 * (progress / frame_count))

            if line == 'progress=end':
                print("process ended")
                print(f"{self.config['output']} has been created")
                self.progress.emit(100)
                break

        # for line in out.stdout.readable():

        # print(out)
        # for i in range(10, 100, 2):
        #     time.sleep(0.1)
        #     self.send_progress(i)
        # self.send_progress(100)

    def get_ffmpeg_stream(self, video_data):
        video = ffmpeg.input(self.config['input'])
        kwargs = {}

        # video
        kwargs.update({
            "crf":  {'crf': self.config['video_bitrate']},
            "KB/s": {'video_bitrate': f"{self.config['video_bitrate']}K"},
            "MB/s": {'video_bitrate': f"{self.config['video_bitrate']}M"}
        }.get(self.config['video_dropdown']))

        # audio
        if self.config['audio_dropdown'] != "copy":
            kwargs.update({'audio_bitrate': f"{self.config['audio_bitrate']}k"})

        # threads, speed
        kwargs.update({
            'threads': self.config['threads'],
            'preset': self.config['speed']
        })

        # resolution
        if self.config['res_dropdown'] != "copy" and self.config['resolution'] > 0:
            dims = video_data['width'], video_data['height']
            scales = {
                'max': self.config['resolution'] / max(dims),
                'min': self.config['resolution'] / min(dims)
            }.get(self.config['res_dropdown'])
            dims = dims[0] * scales, dims[1] * scales

            if any(dim % 1 != 0 for dim in dims):
                self.status.emit(f"Warning: predicted resolution: {dims} is not pixel perfect")
                time.sleep(3)

            video = video.filter('scale', f"{int(dims[0])}x{int(dims[1])}")

        # fps
        if self.config['fps']:
            kwargs['r'] = self.config['fps']

        # misc args
        kwargs.update({
            'progress': '-',
            'loglevel': 'error'
        })
        video = (
            video
            .output(self.config['output'], **kwargs)
            .overwrite_output()
            .global_args('-nostats',
                         '-hide_banner')
        )
        print(video.get_args())
        return video

    def get_metadata(self):
        self.probed.emit(self._get_metadata())

    def _get_metadata(self):
        return ffmpeg.probe(self.path)

    def send_progress(self, i: int):
        self.progress.emit(i)


if __name__ == "__main__":
    t = Timer()
    app = QtWidgets.QApplication([])

    defaults = CfgDict('config.json', save_on_change=False,
                       sort_on_save=True)
    main_app_window = MainWindow(t, defaults)
    main_app_window.show()
    code = app.exec()
    # defaults.save()
    sys.exit(code)

    # def startFfmpeg(self):
    #     self.ffmpeg_path = ffmpeg_utils.get_ffmpeg()
    #     self.statDlg.setText("Converting...")
    #     # Timer.start()

    #     vindex = self.vDrop.currentIndex()
    #     aindex = self.audioDrop.currentIndex()
    #     rindex = self.resDrop.currentIndex()
    # # handle resolutions
    #     reses = {}
    #     reses['input_res'] = [int(val.split("=")[1]) for val in subprocess.check_output(
    #                          [self.ffmpeg_path[1], '-v', 'error', '-show_entries', 'stream=width,height',
    #                           '-of', 'default=noprint_wrappers=1', self.inputText.text()]).
    #                           decode("utf-8").split("\n")[:-1]]
    #     reses['resLine'] = int(self.resLine.text()
    #                            if self.resLine.text() != "" else 0)
    #     reses['restio'] = (reses['resLine']/max(reses['input_res']) if rindex ==
    #                        1 else reses['resLine']/min(reses['input_res']) if rindex == 2 else 1)
    #     reses['new_res'] = [val*reses['restio'] for val in reses['input_res']]
    #     Timer.print(reses['input_res'])
    #     if type(reses['new_res'][0]) != int:
    #         if not reses['new_res'][0].is_integer() or not reses['new_res'][1].is_integer():
    #             self.statDlg.setText(
    #                 "Warning: the specified resolution is not an int.\nresult may be imprecise")
    #             Timer.print(f"{reses['new_res']} is imprecise, flooring...")
    #     reses['new_res'] = [math.floor(val)-(math.floor(val) % 2)
    #                         for val in reses['new_res']]
    #     ffargs = {"path": self.ffmpeg_path[0],
    #               "input":   ['-i', self.inputText.text()],
    #               "output":  self.realOutput(),
    #               "extension": self.outputDrop.currentText(),
    #               "vidbr":   "".join([val for val in self.vBitrate.text() if val.isnumeric()]),
    #               "audbr_s": str(self.aBitrateSlider.value()*32)+"k",
    #               "audbr_i": self.aBitrateInput.text(),
    #               "threads": ['-threads', str(self.threads.value())],
    #               "speedDrop":   ['-preset', self.speedDrop.currentText()],
    #               "fps":     "".join([val for val in self.fps.text() if val.isnumeric()]),
    #               "scale":      f"{reses['new_res'][0]}:{reses['new_res'][1]}"
    #               }
    #     print(ffargs)
    #     if self.outputDrop.currentText() == "png":
    #         if not os.path.exists(os.path.dirname(ffargs['output'])):
    #             os.mkdir(os.path.dirname(ffargs['output']))
    #     # tmpdir for progress bar
    #     tmpdir = self.inputText.text() + '.tmp'
    #     if os.path.exists(tmpdir):
    #         os.remove(tmpdir)
    #     tmpfile = open(tmpdir, "w")

    #     command = sum([[ffargs['path'], '-y'],
    #                    ffargs['input'],
    #                    ffargs['threads'],
    #                    ffargs['speedDrop'],
    #                    ['-progress', '-', '-nostats'],
    #                    ['-r', ffargs['fps']] if ffargs['fps'] != "" else [],
    #                    ], [])
    #     if self.outputDrop.currentText() != "png":
    #         command += sum([['-c:v', 'libx264'],
    #                         ['-map', '0:v:?', '-map',
    #                          '0:a:?', '-map_metadata', "0"],
    #                         ['-b:v', ffargs['vidbr'] + "k"] if vindex == 0 and ffargs['vidbr'] != "" else
    #                         ['-b:v', ffargs['vidbr']*1000] if vindex == 1 and ffargs['vidbr'] != "" else
    #                         ['-crf', ffargs['vidbr']] if vindex == 2 and ffargs['vidbr'] != "" else
    #                         ['-q:v', '0'],
    #                         ['-c:a', 'copy'] if aindex == 0 else
    #                         ['-b:a', ffargs['audbr_s']] if aindex == 1 else
    #                         ['-b:a', ffargs['aidbr_i']
    #                          ] if aindex == 2 else ['-an']
    #                         ], [])
    #     command += sum([['-vf', f'scale={ffargs["scale"]}'] if rindex != 0 and reses['input_res'] != reses['new_res'] else [],
    #                     [ffargs['output']],
    #                     ], [])
    #     # return
    #     ffmpegThread = subprocess.Popen(command,
    #                                     stdout=tmpfile, stderr=tmpfile)
    #     Timer.print("ffmpeg initialized")

    #     self.changeButtons(1)
    #     self.WidgetsEditable(0)
    #     self.workButton.clicked.disconnect()
    #     self.workButton.clicked.connect(ffmpegCancel)
    #     self.ffmpegWaitThread = threading.Thread(target=ffmpegWait)
    #     self.ffmpegWatchThread = threading.Thread(target=ffmpegWatch)
    #     self.ffmpegWatchThread.start()
    #     self.ffmpegWaitThread.start()

    # def workClicked(self):
    #     input_file = self.inputText.text()
    #     if input_file.startswith("file://"):
    #         self.inputText.setText(input_file.replace("file://", ""))
    #         input_file = self.inputText.text()
    #     work_step = self.workButton.text()
    #     if self.statDlg.text() == "Awaiting input":
    #         self.stopped_preemptively = False
    #     if work_step == "Start":
    #         if not os.path.exists(input_file):
    #             self.statDlg.setText("Input file does not exist.")
    #             print("File not found")
    #             return
    #     ffmpeg_output = self.realOutput()
    #     if os.path.exists(ffmpeg_output):
    #         print(ffmpeg_output, "already exists.")
    #         self.statDlg.setText("Output already exists, overwrite?")
    #         self.changeButtons(2)
    #         self.WidgetsEditable(0)
    #     else:
    #         print("running...")
    #         self.startFfmpeg()
