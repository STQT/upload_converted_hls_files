import datetime
import traceback
import logging
import sys

import ffmpeg_streaming
from ffmpeg_streaming import CloudManager
from ffmpeg_streaming import Formats, Bitrate, Representation, Size

from configs import AWS_ACCESS_KEY_ID, REGION_NAME, BUCKET_NAME, AWS_SECRET_ACCESS_KEY
from utils import CustomS3, get_dirname_from_url

print("Hello uploading platform\n"
      "If you want get directory from UI then type: 1\n"
      "If console only: 2\n"
      )

using_type = input("Type your type[1]: ")
upload_dir_path = False, ""

if using_type == "":
    using_type = "1"

if using_type == "1":
    from tkinter.filedialog import askopenfilename
    file_name = askopenfilename(initialdir="C:\\",
                                filetypes=(
                                    ("Video files", ("*.mp4", "*.mkv", "*.mov", "*.wmv", "*.webm")),
                                )
                                )
elif using_type == "2":
    file_name = input("Введите абсолютное расположение вашего файла: ")
    upload_dir_path = True, input("Введите название папки на сервере: ")
else:
    raise SystemExit

while True:
    if upload_dir_path[0] is False:
        upload_dir_path = get_dirname_from_url(input("Ctrl+V to paste from clipboard: "))
    else:
        break

_360p = Representation(Size(640, 360), Bitrate(276 * 1024, 128 * 1024))
_480p = Representation(Size(854, 480), Bitrate(750 * 1024, 192 * 1024))


def monitor(ffmpeg, duration, time_, time_left, process):
    """
    Handling proccess.

    Examples:
    1. Logging or printing ffmpeg command
    logging.info(ffmpeg) or print(ffmpeg)

    2. Handling Process object
    if "something happened":
        process.terminate()

    3. Email someone to inform about the time of finishing process
    if time_left > 3600 and not already_send:  # if it takes more than one hour and you have not emailed them already
        ready_time = time_left + time.time()
        Email.send(
            email='someone@somedomain.com',
            subject='Your video will be ready by %s' % datetime.timedelta(seconds=ready_time),
            message='Your video takes more than %s hour(s) ...' % round(time_left / 3600)
        )
       already_send = True

    4. Create a socket connection and show a progress bar(or other parameters) to your users
    Socket.broadcast(
        address=127.0.0.1
        port=5050
        data={
            percentage = per,
            time_left = datetime.timedelta(seconds=int(time_left))
        }
    )

    :param ffmpeg: ffmpeg command line
    :param duration: duration of the video
    :param time_: current time of transcoded video
    :param time_left: seconds left to finish the video process
    :param process: subprocess object
    :return: None
    """
    per = round(time_ / duration * 100)
    sys.stdout.write(
        "\rTranscoding...(%s%%) %s left [%s%s]" %
        (per, datetime.timedelta(seconds=int(time_left)), '#' * per, '-' * (100 - per))
    )
    sys.stdout.flush()


def main():
    s3 = CustomS3(aws_access_key_id=AWS_ACCESS_KEY_ID,
                  aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                  region_name=REGION_NAME)
    save_to_s3 = CloudManager().add(s3, bucket_name=BUCKET_NAME, folder=upload_dir_path[1])

    video = ffmpeg_streaming.input(file_name)
    hls = video.hls(Formats.h264())
    hls.representations(_360p, _480p)
    try:
        hls.output("/home/kairat/test/playlist.m3u8", clouds=save_to_s3, monitor=monitor)
    except Exception as e:
        logging.error(e)
        logging.error(traceback.format_exc())


if __name__ == '__main__':
    main()
