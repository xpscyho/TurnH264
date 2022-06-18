import os
import shutil
import subprocess
import argparse
parser = argparse.ArgumentParser(description='Compile the project')
parser.add_argument('--onefile', action='store_true',
                    help='Compile to one file', required=False)
args = parser.parse_args()

try:
    subprocess.check_output(["pyinstaller", "--version"])
except:
    subprocess.check_output(['pip', 'install', 'pyinstaller'])
# import the script TurnH264.py
if os.path.exists("TurnH264-build"):
    print("Build already exists, continue?")
    answer = input("y/n: ")
    if not answer == "y":
        exit()

subprocess.check_output(["pyinstaller",
                         '--onefile' if args.onefile else "",
                         "TurnH264.py"])
shutil.rmtree("build")
os.remove("TurnH264.spec")
# copy dist/build/TurnH264 to TurnH264-build
shutil.rmtree("TurnH264-build")
shutil.copytree("dist/TurnH264", "TurnH264-build")
shutil.rmtree("dist")
