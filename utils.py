import logging
import magic
import sys

from os import listdir
from os.path import isfile, join, split

import requests
from boto3.s3.transfer import TransferConfig
from ffmpeg_streaming import S3

BASE_URL = "http://localhost:8000/get_path/"


def upload_monitor(upload_element_number, max_upload_element_counts, file):
    per = round(upload_element_number / max_upload_element_counts * 100)
    sys.stdout.write("\rUploading...(%s%%) File: %s" % (per, file))
    sys.stdout.flush()


def get_dirname_from_url(url) -> (bool, str):
    response = requests.get(BASE_URL + "?url=" + url)
    if response.status_code == 404:
        return False, "Not Found"
    elif response.status_code == 400:
        return False, "\n".join(response.json().get("message", "Not Found"))
    elif response.status_code == 500:
        return False
    return True, response.json()['result']


def check_file_mime_type(file_path: str) -> bool:
    supported_types = ['video/mp4', 'video/x-matroska', 'video/quicktime', 'video/x-ms-wmv',
                       'video/webm']

    file_mime = magic.from_file(file_path, mime=True)
    if file_mime in supported_types:
        return True
    return False


class CustomS3(S3):
    def __init__(self, **options):
        super().__init__(**options)

    def upload_directory(self, directory, **options):
        bucket_name = options.get('bucket_name', None)
        folder = options.get('folder', '')
        if bucket_name is None:
            raise ValueError('You should pass a bucket name')

        files = [f for f in listdir(directory) if isfile(join(directory, f))]
        files_count = len(files)
        uploading_files = self.get_not_uploaded_files(files, **options)
        if len(uploading_files) == 0:
            sys.stdout.write("\rAll files uploaded successfully! Don't repeat upload")
            input("\nPlease ENTER to exit now.")
        try:
            for num, file in enumerate(uploading_files):
                upload_monitor(num + 1, files_count, file)
                config = TransferConfig(use_threads=False)
                self.s3.upload_file(join(directory, file), bucket_name, join(folder, file).replace("\\", "/"),
                                    Config=config
                                    )

        except self.err as e:
            logging.error(e)
            raise RuntimeError(e)

        logging.info("The {} directory was uploaded to Amazon S3 successfully".format(directory))

    def get_all_files(self, **options):
        bucket_name = options.pop('bucket_name', None)
        folder = options.pop('folder', '')
        if bucket_name is None:
            raise ValueError('You should pass a bucket name')
        s3_files_list = self.s3.list_objects(Bucket=bucket_name, Prefix=folder, Delimiter='/')
        return s3_files_list.get('Contents', [])

    def get_not_uploaded_files(self, uploading_files_list, **options):
        set_list = set(uploading_files_list)
        s3_files_list = self.get_all_files(**options)
        uploaded_files = set([split(a['Key'])[1] for a in s3_files_list])
        return set_list - uploaded_files

