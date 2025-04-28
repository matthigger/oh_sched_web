import os
import pathlib
import tempfile
import uuid

import boto3


def download_s3_files(bucket, folder=None):
    """ Downloads all files from a S3 bucket to a specified local folder

    Args:
        bucket (str): The name of the S3 bucket.
        folder (str): The local folder where files will be downloaded

    Returns:
        folder (str): path to output folder
    """
    if folder is None:
        folder = tempfile.gettempdir()
        folder = pathlib.Path(folder) / str(uuid.uuid4())[:5]

    # Create an S3 client
    s3 = boto3.client('s3')

    # Check if the provided download folder exists, create if not
    if not os.path.exists(folder):
        os.makedirs(folder)

    # List all files in the S3 bucket
    pagination = True
    next_token = None

    while pagination:
        list_params = {'Bucket': bucket}
        if next_token:
            list_params['ContinuationToken'] = next_token

        objects = s3.list_objects_v2(**list_params)

        if 'Contents' in objects:
            # Iterate over each object in the S3 bucket
            for obj in objects['Contents']:
                # Get the file name
                file_name = obj['Key']

                # Construct the local file path in the download folder
                local_file_path = os.path.join(folder, file_name)

                # Ensure the directory exists for each file (in case of nested folders in S3)
                os.makedirs(os.path.dirname(local_file_path),
                            exist_ok=True)

                # Download the file from S3 to the local folder
                s3.download_file(bucket, file_name, local_file_path)

        # Check if there are more files to download (pagination)
        next_token = objects.get('NextContinuationToken')
        pagination = next_token is not None

    return folder


if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()
    folder = download_s3_files('oh-sched-web')
    print(folder)
