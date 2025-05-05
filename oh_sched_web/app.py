import hashlib
import logging
import os
import pathlib
import shutil
import uuid
from datetime import datetime

import boto3
import oh_sched
import yaml
from dotenv import load_dotenv
from flask import Flask, send_from_directory, render_template
from flask import request

import oh_sched_web
from oh_sched_web.constants import OUTPUT_FOLDER, HASH_LEN, LOG_PREFIX, \
    UPLOAD_FOLDER
from oh_sched_web.std_tools import add_stdout_stderr, error_to_stdout

app = Flask(__name__)

# loads aws credentials (if .env found locally, else these params given to
# render explicitly)
load_dotenv()

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        with GetDeleteInputs() as (config, csv_path):
            section_dict, download_links = oh_sched_main(config, csv_path)

        # fix path for downloads
        download_links = [f'/download/{p.name}' for p in download_links]
        return render_template('results.html',
                               download_links=download_links,
                               section_dict=section_dict)

    return render_template('index.html')


@app.route('/download/<filename>')
def download_file(filename):
    if filename == 'oh_prefs_toy.csv':
        folder = pathlib.Path(oh_sched_web.__file__).parents[1]
    else:
        folder = OUTPUT_FOLDER

    if not (folder / filename).exists():
        return f'File {folder / filename} not found', 404

    return send_from_directory(folder, filename, as_attachment=True)


@add_stdout_stderr
@error_to_stdout
def oh_sched_main(config, csv_path):
    """ runs oh_sched.main & logs output"""
    oh_sched.main(csv_path, config)

    # print a copy of config used to outputs
    f_yaml = OUTPUT_FOLDER / 'config.yaml'
    config.to_yaml(f_yaml)

    # send usage line to aws
    now = datetime.now()
    s_now = now.strftime('%Y-%m-%d %H:%M:%S.%f')
    email_list = [hashlib.sha256(s.encode()).hexdigest()[:HASH_LEN]
                  for s in oh_sched.extract_csv(csv_path)[1]]
    s = ','.join([s_now] + email_list)
    app.logger.info(LOG_PREFIX + s)

    # upload
    s3 = boto3.client('s3')
    s3.put_object(Bucket=os.environ.get('AWS_BUCKET'),
                  Key=str(uuid.uuid4())[:5],
                  Body=s)

    section_dict = {'config.yaml': yaml.dump(config.to_dict())}
    download_links = [config.f_out, f_yaml]

    return section_dict, download_links


class GetDeleteInputs:
    """ loads / uploads inputs from webform, deletes files after use"""

    def __enter__(self):
        f_csv = request.files['csv_file']

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

        csv_path = UPLOAD_FOLDER / f_csv.filename
        f_csv.save(csv_path)

        return config, csv_path

    def __exit__(self, exc_type, exc_val, exc_tb):
        for item in UPLOAD_FOLDER.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        return False
