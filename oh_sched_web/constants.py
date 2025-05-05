import pathlib

import oh_sched_web

HASH_LEN = 8

# setup paths
FOLDER = pathlib.Path(oh_sched_web.__file__).parents[1]
UPLOAD_FOLDER = FOLDER / pathlib.Path('uploads')
OUTPUT_FOLDER = FOLDER / pathlib.Path('outputs')

LOG_PREFIX = 'OH_SCHED RUNNING:'

UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)
