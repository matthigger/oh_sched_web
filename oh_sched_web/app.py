import contextlib
import hashlib
import io
import logging
import pathlib
import shutil
import os
import uuid
from datetime import datetime

import boto3
import oh_sched
import yaml
from flask import Flask, request, send_from_directory, render_template
from dotenv import load_dotenv


import oh_sched_web

app = Flask(__name__)

# loads aws credentials (if .env found locally, else these params given to
# render explicitly)
load_dotenv()

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

HASH_LEN = 8

# setup paths
FOLDER = pathlib.Path(oh_sched_web.__file__).parents[1]
UPLOAD_FOLDER = FOLDER / pathlib.Path('uploads')
OUTPUT_FOLDER = FOLDER / pathlib.Path('outputs')
f_usage = FOLDER / 'usage.csv'

LOG_PREFIX = 'OH_SCHED RUNNING:'

UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)


def oh_sched_wrapped(f_csv, config):
    oh_sched.main(f_csv, config)

    # print a copy of config used to outputs
    f_yaml = OUTPUT_FOLDER / 'config.yaml'
    config.to_yaml(f_yaml)

    # send usage line to aws
    now = datetime.now()
    s_now = now.strftime('%Y-%m-%d %H:%M:%S.%f')
    email_list = [hashlib.sha256(s.encode()).hexdigest()[:HASH_LEN]
                  for s in oh_sched.extract_csv(f_csv)[1]]
    s = ','.join([s_now] + email_list)
    app.logger.info(LOG_PREFIX + s)

    # upload
    s3 = boto3.client('s3')
    s3.put_object(Bucket=os.environ.get('AWS_BUCKET'),
                  Key=str(uuid.uuid4())[:5],
                  Body=s)

    return [config.f_out, f_yaml]


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # capture stdout and print to output
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        with (contextlib.redirect_stdout(stdout_buffer),
              contextlib.redirect_stderr(stderr_buffer)):

            csv_file = request.files['csv_file']

            # load config
            config_params = ['oh_per_ta', 'max_ta_per_oh', 'date_start',
                             'date_end', 'scale_dict', 'tz']
            config = {s: request.form.get(s) for s in config_params}
            config = {k: None if v == '' else v
                      for k, v in config.items()}
            # web users always want ics
            config['f_out'] = OUTPUT_FOLDER / 'office_hours.ics'

            if config['scale_dict'] is not None:
                s_scale = config['scale_dict']
                config['scale_dict'] = dict()
                for line in s_scale.split(','):
                    s_regex, scale = line.split(':')
                    config['scale_dict'][s_regex] = float(scale)

            config = oh_sched.Config(**config)

            csv_path = UPLOAD_FOLDER / csv_file.filename
            csv_file.save(csv_path)

            output_paths = oh_sched_wrapped(csv_path, config)

        section_dict = {'config.yaml': yaml.dump(config.to_dict())}
        for buffer, file in [(stderr_buffer, 'error.txt'),
                             (stdout_buffer, 'output.txt')]:
            s = buffer.getvalue()
            if not s:
                # no output generated
                continue

            f_out = OUTPUT_FOLDER / file
            with open(f_out, 'w') as f:
                print(s, file=f)

            output_paths.append(f_out)
            section_dict[file] = s

        # delete all uploads
        for item in UPLOAD_FOLDER.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

        # Show download links
        download_links = [f'/download/{p.name}' for p in output_paths]
        return render_template('results.html',
                               download_links=download_links,
                               section_dict=section_dict)

    return render_template('index.html')


@app.route('/download/<filename>')
def download_file(filename):
    if filename == 'oh_prefs_toy.csv':
        folder = pathlib.Path(oh_sched_web.__file__).parents[1]
    elif filename == 'usage.csv':
        folder = FOLDER
    else:
        folder = OUTPUT_FOLDER

    if not (folder / filename).exists():
        return f'File {folder / filename} not found', 404

    return send_from_directory(folder, filename, as_attachment=True)
