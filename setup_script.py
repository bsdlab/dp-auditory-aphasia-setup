import shutil
import subprocess
import sys
from pathlib import Path

# ----------------------------------------------------------------------------
# Install requirements
# ----------------------------------------------------------------------------

requirements = ["GitPython", "toml"]

for req in requirements:
    try:
        __import__(req)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", req])

import toml
from git import Repo

# ----------------------------------------------------------------------------
# Set up
# ----------------------------------------------------------------------------

# The name of the folder that is to be created to store all the modules
SETUP_FOLDER_NAME = "auditory_aphasia_env"
BRANCH_NAME = SETUP_FOLDER_NAME  # used within each module

CONTROL_ROOM_URL = "https://github.com/bsdlab/dp-control-room.git"
PARADIGM_URL = ""  # Currently hosted on gitlab, and private -> copy into the SETUP_FOLDER_NAME folder
DECODER_URL = ""
LSL_URL = "https://github.com/bsdlab/dp-lsl-recording.git"
BV_URL = "https://github.com/bsdlab/dp-brainvision-control"

# ----------------------------------------------------------------------------
# Grab the git repositories
# ----------------------------------------------------------------------------

root_dir = Path(SETUP_FOLDER_NAME)
try:
    root_dir.mkdir(exist_ok=False)
except FileExistsError:
    print(f"Directory `{root_dir}` already exists. Exiting.")
    q = input("Do you want to overwrite it? [y/N] ")
    if q == "y":
        shutil.rmtree(root_dir)
        root_dir.mkdir()
    else:
        exit(1)

# SSH ide via the Repo.clone_from did not work -> use manual subprocess calls
repos = []
repo_dirs = {
    "dp-control-room": CONTROL_ROOM_URL,
    # "dp-auditory-aphasia-paradigm": PARADIGM_URL,      # <--- for now use the `auditoryaphasia-refactoring` and rename to `dp-auditory-aphasia-paradigm`
    # "dp-auditory-aphasia-decoder": DECODER_URL,
    "dp-brainvision-control": BV_URL,
    "dp-lsl-recording": LSL_URL,
}
for repo_dir, url in repo_dirs.items():
    cmd = f"git clone -v -- {url} {SETUP_FOLDER_NAME}/{repo_dir}"
    subprocess.run(cmd, shell=True)
    repos.append(Repo(root_dir / repo_dir))

# for each repo -> create a branch for the experiment
# Keep a branch for the local setup to separate local specific changes
# from general bugfixes and features (which would then be merged back to `main`)
for repo in repos:
    branch = repo.create_head(BRANCH_NAME)
    branch.checkout()

# ----------------------------------------------------------------------------
# Derived paths
# ----------------------------------------------------------------------------

# Data directory relative to SETUP_FOLDER_NAME
DATA_DIR = root_dir.joinpath("./data").resolve()

# ----------------------------------------------------------------------------
# Create configs
# ----------------------------------------------------------------------------

#
# >>> for dp-control-room
#

control_room_cfg = f"""

[python]
modules_root = '../'                                                            


# -------------------- Paradigm  ---------------------------------------
[python.modules.dp-auditory-aphasia-paradigm]                                        
    type = 'paradigm'
    port = 8083
    ip = '127.0.0.1'

# -------------------- BV control  ----------------------------------------- 
[python.modules.dp-brainvision-control]                                     
    type = 'recording'
    port = 8084
    ip = '127.0.0.1'

# -------------------- LSL recording -----------------------------------------
[python.modules.dp-lsl-recording]                                      
    type = 'recording'
    port = 8082                                                                 
    ip = '127.0.0.1'


[macros]

[macros.run_6d]
    name = 'RUN TRAINING'
    description = 'Start the recording of training data'
[macros.run_6d.default_json]
    fname = 'sub-P001_ses-S001_run-001_task-training'
    data_root = '{str(DATA_DIR.resolve())}'
    delay_s = 0.5                  # delay inbetween commands -> time for LSL recorder to respond
[macros.run_6d.cmds]
    # [<target_module>, <PCOMM>, <kwarg_name1 (optional)>, <kwarg_name2 (optional)>]
    com1 = ['dp-lsl-recording', 'UPDATE']
    com2 = ['dp-lsl-recording', 'SELECT_ALL']
    com3 = ['dp-lsl-recording', 'SET_SAVE_PATH', 'fname=fname', 'data_root=data_root']
    com4 = ['dp-brainvision-control', 'SET_SAVE_PATH', 'rec_dir=data_root']
    com5 = ['dp-lsl-recording', 'RECORD']
    com6 = ['dp-brainvision-control', 'START_SAVE', 'fname=fname']

[macros.stop_recording]
    name = 'STOP LSL RECORDING'
    description = 'Stop the recording'
[macros.stop_recording.cmds]
    com1 = ['dp-lsl-recording', 'STOPRECORD']
    com2 = ['dp-brainvision-control', 'STOP_SAVE']

"""

control_room_cfg_pth = root_dir.joinpath(
    "dp-control-room/configs/auditory_aphasia.toml"
)
with open(control_room_cfg_pth, "w") as f:
    f.write(control_room_cfg)


# ----------------------------------------------------------------------------
# Create single run script in the control room
# ----------------------------------------------------------------------------

platform = sys.platform
suffix = ".ps1" if platform == "win32" else ".sh"

script_file = (
    root_dir.resolve() / "dp-control-room" / f"run_auditory_aphasia_experiment{suffix}"
)

with open(script_file, "w") as f:
    f.write(
        f'python -m control_room.main --setup_cfg_path="{control_room_cfg_pth.resolve()}"'
    )
