import contextlib
import functools
import io
import traceback

from oh_sched_web.app import OUTPUT_FOLDER


def error_to_stdout(fnc):
    """ sends all errors to stdout """
    @functools.wraps(fnc)
    def wrapped(*args, **kwargs):
        try:
            section_dict, download_links = fnc(*args, **kwargs)
        except BaseException as e:
            # print exception
            traceback.print_exc()
            section_dict = dict()
            download_links = list()

        return section_dict, download_links

    return wrapped


def add_stdout_stderr(fnc):
    """ adds stdout to section_dict & download_links """
    @functools.wraps(fnc)
    def wrapped(*args, **kwargs):
        # capture stdout and print to output
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        with (contextlib.redirect_stdout(stdout_buffer),
              contextlib.redirect_stderr(stderr_buffer)):
            section_dict, download_links = fnc(*args, **kwargs)

        # add stdout & stderr as needed
        for buffer, file in [(stderr_buffer, 'error.txt'),
                             (stdout_buffer, 'output.txt')]:
            s = buffer.getvalue()
            if not s:
                # no output generated
                continue

            f_out = OUTPUT_FOLDER / file
            with open(f_out, 'w') as f:
                print(s, file=f)

            download_links.append(f_out)
            section_dict[file] = s

        return section_dict, download_links

    return wrapped
