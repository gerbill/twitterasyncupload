"""
This script will upload videos to twitter that are up to 2 minutes long
How to use:

    1. Go to https://apps.twitter.com to get your OAuth keys and enter them here.

    2. Move videos that are up to 2 minutes long to videos folder (or specify a path to folder where you
    store your videos). Titles of these videos will be used as status text for the tweets. Status text
    will be checked to not exceed twitters 140 character limit. In my case I used to name videos with hashtags
    that were separated with underscores thus getting tweet status text to be all hashtags separated by spaces.
"""

import os
import sys
import time
import random
import requests
from requests_oauthlib import OAuth1


# At https://apps.twitter.com you will find these keys so this script may act on behalf of your twitter app.
CONSUMER_KEY = 'consumer_key'
CONSUMER_SECRET = 'consumer_secret'
ACCESS_TOKEN = 'access_token'
ACCESS_TOKEN_SECRET = 'access_token_secret'

# Path to the folder where you store your videos that are up to 2 minutes long.
videosfolder = "videos/"

oauth = OAuth1(CONSUMER_KEY, client_secret=CONSUMER_SECRET,
               resource_owner_key=ACCESS_TOKEN,
               resource_owner_secret=ACCESS_TOKEN_SECRET)

MEDIA_ENDPOINT_URL = 'https://upload.twitter.com/1.1/media/upload.json'
POST_TWEET_URL = 'https://api.twitter.com/1.1/statuses/update.json'


def mystatus(videopath):
    """
    Gets tweet text from video title. In my case videos are named with a set of hashtags
    that best described the video separated by underscores.
    """
    tagslist = videopath.split('/')[-1].split("_")[:-3]
    random.shuffle(tagslist)
    finalstatus = " ".join(tagslist)

    while len(finalstatus) > 139:
        finalstatus = " ".join(finalstatus.split(" ")[:-1])

    return finalstatus


class VideoTweet(object):
    def __init__(self, file_name):
        """
        Defines video tweet properties
        """
        self.video_filename = file_name
        self.total_bytes = os.path.getsize(self.video_filename)
        self.media_id = None
        self.processing_info = None

    def upload_init(self):
        """
        Initializes Upload
        """
        print('INIT')

        request_data = {
            'command': 'INIT',
            'media_type': 'video/mp4',
            'total_bytes': self.total_bytes,
            'media_category': 'tweet_video'
        }

        req = requests.post(url=MEDIA_ENDPOINT_URL, data=request_data, auth=oauth)
        media_id = req.json()['media_id']

        self.media_id = media_id

        print('Media ID: %s' % str(media_id))

    def upload_append(self):
        """
        Uploads media in chunks and appends to chunks uploaded
        """
        segment_id = 0
        bytes_sent = 0
        file = open(self.video_filename, 'rb')

        while bytes_sent < self.total_bytes:
            chunk = file.read(4 * 1024 * 1024)

            print('APPEND')

            request_data = {
                'command': 'APPEND',
                'media_id': self.media_id,
                'segment_index': segment_id
            }

            files = {
                'media': chunk
            }

            req = requests.post(url=MEDIA_ENDPOINT_URL, data=request_data, files=files, auth=oauth)

            if req.status_code < 200 or req.status_code > 299:
                print(req.status_code)
                print(req.text)
                sys.exit(0)

            segment_id += 1
            bytes_sent = file.tell()

            print('%s of %s bytes uploaded' % (str(bytes_sent), str(self.total_bytes)))

        print('Upload chunks complete.')

    def upload_finalize(self):
        """
        Finalizes uploads and starts video processing
        """
        print('FINALIZE')

        request_data = {
            'command': 'FINALIZE',
            'media_id': self.media_id
        }

        req = requests.post(url=MEDIA_ENDPOINT_URL, data=request_data, auth=oauth)
        print(req.json())

        self.processing_info = req.json().get('processing_info', None)
        self.check_status()

    def check_status(self):
        """
        Checks video processing status
        """
        if self.processing_info is None:
            return

        state = self.processing_info['state']

        print('Media processing status is %s ' % state)

        if state == u'succeeded':
            return

        if state == u'failed':
            sys.exit(0)

        check_after_secs = self.processing_info['check_after_secs']

        print('Checking after %s seconds' % str(check_after_secs))
        time.sleep(check_after_secs)

        print('STATUS')

        request_params = {
            'command': 'STATUS',
            'media_id': self.media_id
        }

        req = requests.get(url=MEDIA_ENDPOINT_URL, params=request_params, auth=oauth)

        self.processing_info = req.json().get('processing_info', None)
        self.check_status()

    def tweet(self, videopath):
        """
        Publishes Tweet with attached video
        """
        request_data = {
            'status': mystatus(videopath),
            'media_ids': self.media_id
        }

        req = requests.post(url=POST_TWEET_URL, data=request_data, auth=oauth)
        print(req.json())


if __name__ == '__main__':

    for i in range(len(os.listdir(videosfolder))):
        videopath = videosfolder + random.choice(os.listdir(videosfolder))

        videoTweet = VideoTweet(videopath)
        videoTweet.upload_init()
        videoTweet.upload_append()
        videoTweet.upload_finalize()
        videoTweet.tweet(videopath)

        os.remove(videopath)
        time.sleep(random.randrange(299, 360))
