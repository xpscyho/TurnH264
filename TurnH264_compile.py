import os
import shutil
import subprocess
try:
    subprocess.check_output(["pyinstaller", "--version"])
except:
    subprocess.check_output(['pip', 'install', 'pyinstaller'])
# import the script TurnH264.py

subprocess.check_output(["pyinstaller",
                         '--windowed',
			 '--onefile',
                         "TurnH264.py"])
shutil.rmtree("build")
os.remove("TurnH264.spec")
# copy dist/build/TurnH264 to TurnH264-build
if os.path.exists("TurnH264-build"):
    shutil.rmtree("TurnH264-build")
shutil.copytree("dist/TurnH264", "TurnH264-build")
shutil.rmtree("dist")
