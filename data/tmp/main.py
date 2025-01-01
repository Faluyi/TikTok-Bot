import os, re, time, shutil, random, datetime, csv, traceback, sys
import hashlib
from threading import Thread
from concurrent.futures import ThreadPoolExecutor, as_completed

from pytz import timezone

#for path in sys.path:
#	print(path)

from print_text3 import xprint

from pyroDB import PickleTable

from tiktok_uploader_2.upload import upload_video, upload_videos, waste_time, get_authentic_driver
from tiktok_uploader_2.auth import InsufficientAuth

os.makedirs('../data/tmp', exist_ok=True)

def toast(*args, header="Notification Test", msg='TikTok Uploader is running in the background', duration=0,app_title='TikTok Uploader', icon_path="tiktok_icon.ico", **kwargs):
	if os.name == 'nt':
		from plyer import notification

		notification.notify(
			title=header,
			message=msg,
			app_name=app_title,
			app_icon=icon_path,
			timeout=duration,
		)
	else:
		print(*args, **kwargs)

# toast()

def dt_now():
	return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def dt_to_timestamp(dt):
	return datetime.datetime.strptime(dt, "%Y-%m-%d %H:%M:%S").timestamp()

users = PickleTable('../data/Users.pdb')
users.add_column('email', exist_ok=True)
users.add_column('cookies', exist_ok=True)

class UserHandler:
	def __init__(self):
		self.users = users
		self.failed = []

		self.update_cookies()
	def update_cookies(self):
		for file in os.listdir('../cookies'):
			if file.endswith('.cookie'):
				email = file.rsplit('.', 1)[0]
				if email in self.users.get_column('email'):
					continue
				cookies = '../cookies/'+file
				self.users.add_row({'email':email, "cookies":cookies})

	def cookie(self, email):
		cell = self.users.find_1st(email, 'email')

		return cell.row_obj()['cookies'] if cell else None
	
	def emails(self):
		return self.users.get_column('email')
	
	

handler = UserHandler()

class User:
	def __init__(self, email):
		self.email = email
		self.cookies:str = handler.cookie(email)
		self.driver = None

		self.db = PickleTable('../data/'+email+'.pdb')
		self.db.add_column('video', 'post_date', exist_ok=True)
		self.tdb = PickleTable('../data/'+email+'_time.pdb')
		self.tdb.add_column('login', 'active_time', exist_ok=True)


		self.search_terms = []
		with open('../Assets/search_terms.csv', 'r', newline='') as file:
			reader = csv.reader(file)
			for row in reader:
				self.search_terms.append(row[0])

		self.comment_terms = []
		with open('../Assets/comment_terms.csv', 'r', newline='') as file:
			reader = csv.reader(file)
			for row in reader:
				self.comment_terms.append(row[0])

	def is_warmed_up(self):
		time_spent = sum([a_time for a_time in self.tdb.get_column('active_time')])
		if time_spent < 5*60*60:
			return False

		# check if user has already logged in for 5 days
		logins = self.tdb.get_column('login')
		if len(logins) >= 5:
			last_login = logins[-1]
			first_login = logins[0]
			# convert datetime to timestamp
			last_login = dt_to_timestamp(last_login)
			first_login = dt_to_timestamp(first_login)

			if (last_login - first_login) > 5*24*60*60:
				return True
			
		return False





	def warm_up(self):
		if self.is_warmed_up():
			return None
		
		personal_delay = random.random() * 60 * 60
		time.sleep(personal_delay)


		to_waste = (random.randint(10, 30) + random.random()) * 60

		xprint('/y/', f'[{self.email}] Warming up for {to_waste/60} minutes')
		
		search_terms = random.sample(self.search_terms, random.randint(3,7))

		row = self.tdb.add_row({'login':dt_now(), 'active_time':0})

		waste_time_start = time.time()
		
		try:
			waste_time(to_waste, 
						cookies=self.cookies, 
						search_terms=search_terms, 
						sample_comments=self.comment_terms
						)
						
						
		except:
			xprint('/rh/', traceback.format_exc(), '/=/')
		
		row.update({'active_time':time.time() - waste_time_start})

		xprint('/y/', f'[{self.email}] Warmed up for {row["active_time"]/60} minutes')

	def light_warm_up(self):
		"""runs for 15-25 minutes if the user has already uploaded 3 videos today and not active for 1.5hours today"""

		# check usage today
		time_spent = 0
		for row in self.tdb.rows():
			time_spent += row['active_time'] if row['login'].split(' ')[0] == dt_now().split(' ')[0] else 0

		if time_spent > 1.5*3600:
			return None

		to_waste = (random.randint(15, 25) + random.random()) * 60

		xprint('/y/', f'[{self.email}] Warming up for {to_waste/60} minutes')

		row = self.tdb.add_row({'login':dt_now(), 'active_time':0})
		
		search_terms = random.sample(self.search_terms, random.randint(3,7))


		time_waste_start = time.time()
		
		try:
			waste_time(to_waste, 
						cookies=self.cookies, 
						search_terms=search_terms, 
						sample_comments=self.comment_terms
						)
						
		except:
			xprint('/rh/', traceback.format_exc(), '/=/')
		
			
		
		row.update({'active_time':time.time() - time_waste_start})

		xprint('/y/', f'[{self.email}] Warmed up for {row["active_time"]/60} minutes')

	def upload(self, video, description):
		if not self.is_warmed_up():
			return None
		

		xprint('/y/', f'[{self.email}] Uploading {video}')

		row = { }

		waste_before = (random.randint(10, 15) + random.random()) * 60
		waste_after = (random.randint(5, 10) + random.random()) * 60

		tdr = self.tdb.add_row({'login':dt_now(), 'active_time':0})
		
		upload_time_start = time.time()

		try:
			upload_video(video, 
						description, 
						audio=True, # trending audio
						cookies=self.cookies,
						waste_time_before=waste_before,
						waste_time_after=waste_after,
						)
						
			row = self.db.add_row({'video':video, 'post_date': dt_now()})
		except InsufficientAuth:
			xprint('/rh/', f'[{self.email}] InsufficientAuth\n\tPlease login to TikTok and save the cookies as cookies/{self.email}.cookie', "/=/")

			toast(header='Auth Failed', msg=f'[{self.email}] InsufficientAuth\n\tPlease login to TikTok and save the cookies as cookies/{self.email}.cookie', duration=10)
			
		except:
			xprint('/rh/', traceback.format_exc(), '/=/')
		
		tdr.update({'active_time':time.time() - upload_time_start})

		xprint('/y/', f'[{self.email}] Uploaded {video}')

		return row
	
	
	def upload_random(self):
		if not self.is_warmed_up():
			return None
		
		
		personal_delay = random.random() * 60 * 60
		time.sleep(personal_delay)
		
		# check if 3 videos have been uploaded today
		if self.db.height >= 3:
			for i in range(1,4):
				if self.db.rows(i*-1)['post_date'].split(' ')[0] != dt_now().split(' ')[0]:
					break
			else:
				self.light_warm_up()
				return None



		videos = [f for f in os.scandir('../Video') if f.is_file()]
		copy_videos = videos[:]


		# remove already uploaded videos
		for row in self.db.rows():
			if row['video'] in copy_videos:
				copy_videos.remove(row['video'])

		if len(copy_videos) == 0:
			copy_videos = videos[:]
			self.db.clear()

		video = random.choice(copy_videos)
		description = " ".join(random.sample(self.comment_terms, random.randint(3,7)))

		self.upload(video, description)




	
	def get_dedicated_driver(self):
		if self.driver is None:
			self.driver = get_authentic_driver(cookies=self.cookies)
		return self.driver
	
	def kill_driver(self):
		if self.driver is not None:
			self.driver.quit()
			self.driver = None





class TikTokUploader:
	def __init__(self) -> None:
		pass

	def warm_up(self):
		future = []
		with ThreadPoolExecutor(max_workers=5) as executor:
			for email in handler.emails():
				user = User(email)
				
				# check user logs to check if user has already logged in for 5 days and has spent 5 hours

				# # check if user has already logged in for 5 days

				# otherwise warm up
				future.append(executor.submit(user.warm_up))

		for f in as_completed(future):
			pass

	def upload(self):
		future = []
		# check if today is sunday or wednesday
		if datetime.datetime.today().weekday() not in [2, 6]:
			return None
		
		# check if time is between 1PM EST - 7PM EST
		# Fix time zone
		tz = timezone('EST')
		time_now = datetime.datetime.now(tz) 
		if time_now.hour <= 13 or time_now.hour >= 19:
			return None
		
		with ThreadPoolExecutor(max_workers=5) as executor:
			for email in handler.emails():
				user = User(email)
				future.append(executor.submit(user.upload_random))

		for _ in as_completed(future):
			pass

	def run(self):
		while True:
			self.warm_up()
			self.upload()
			wait_time = (random.randint(1, 2)+ random.random()) * 60 * 60
			time.sleep(wait_time)


# # convert datetime to timestamp
# last_login = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
# print(last_login)
# print(time.time())
# # last_login = "2023-12-16 18:24:13"
# last_login = datetime.datetime.strptime(last_login, "%Y-%m-%d %H:%M:%S").timestamp()

# print(last_login)
			
def main():
	ttu = TikTokUploader()
	ttu.run()
			
if __name__ == '__main__':
	main()