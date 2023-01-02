import sys
from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need fine tuning.
# "packages": ["os"] is used as example only
build_exe_options = {"packages": ["pydofus2", "thrift"], "excludes": []}

# base="Win32GUI" should be used only for Windows GUI app
base = None
# if sys.platform == "win32":
#     base = "Win32GUI"

setup(
    name="pyd2bot",
    version="1.0.0",
    description="pyd2bot",
    options={"build_exe": build_exe_options},
    executables=[Executable("pyd2bot.py", base=base)],
)