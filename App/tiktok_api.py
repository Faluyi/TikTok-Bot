import os
import sys
sys.path.append('../')

from tiktok_uploader_2.upload import upload_video, upload_videos, waste_time
from tiktok_uploader_2.auth import AuthBackend

# waste time
waste_time(0, 100,
			search_terms=['genshin', 'honkai impact', 'hoyomix'],
            cookies='../cookies/adscow99@gmail.com.cookie',
			sample_comments=['nice', 'cool', 'wow', 'amazing', 'great', 'awesoome']
)

exit()
# print(os.path.isfile('../Videos/1.mp4'))
# exit()
upload_video('../Videos/Eula banner.mp4',
            description='Eula is love\n\n#fyp This is a test video',
            cookies='../cookies/adscow99@gmail.com.cookie',
			audio="hello world",
			waste_time_before=10,
			waste_time_after=15,
			)


App_ID=7310504467749832709
Client_key='awk8njc4p853qebj'

Client_secret='Zppr9yIiEESwWVQeUpxJL1amTSXDjOcL'
