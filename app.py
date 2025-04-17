import contextlib
import io
import pathlib
import shutil

import oh_sched
from flask import Flask, request, send_file, render_template

app = Flask(__name__)

UPLOAD_FOLDER = pathlib.Path('uploads')
OUTPUT_FOLDER = pathlib.Path('outputs')
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)


def oh_sched_wrapped(f_csv, f_yaml=None):
    if f_yaml is None:
        # default config if no yaml passed
        print('no config yaml passed, using default config file')
        config = oh_sched.Config()
    else:
        config = oh_sched.Config.from_yaml(f_yaml)

    # config, output is always output_folder / 'office_hours.ics'
    config.f_out = OUTPUT_FOLDER / 'office_hours.ics'

    oh_sched.main(f_csv, config)

    # print a copy of config used to outputs
    f_yaml = OUTPUT_FOLDER / 'config.yaml'
    config.to_yaml(f_yaml)

    return [config.f_out, f_yaml]


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        csv_file = request.files['csv_file']
        yaml_file = request.files.get('yaml_file')

        csv_path = UPLOAD_FOLDER / csv_file.filename
        csv_file.save(csv_path)

        if yaml_file.content_length:
            yaml_path = UPLOAD_FOLDER / yaml_file.filename
            yaml_file.save(yaml_path)
        else:
            yaml_path = None

        # # Run your CLI logic here
        # capture stdout and print to output
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        with (contextlib.redirect_stdout(stdout_buffer),
              contextlib.redirect_stderr(stderr_buffer)):
            output_paths = oh_sched_wrapped(csv_path, yaml_path)

        section_dict = dict()
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
    return send_file(OUTPUT_FOLDER / filename, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)
