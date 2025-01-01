import os, re, time, shutil, random, datetime, csv, traceback, sys
import hashlib
import threading
from threading import Thread
from concurrent.futures import ThreadPoolExecutor, as_completed

from pytz import timezone

from print_text3 import xprint

from pyroDB import PickleTable

from tiktok_uploader_2.upload import upload_video, upload_videos, waste_time, get_authentic_driver, follow_back_all, delete_low_videos
from tiktok_uploader_2.auth import InsufficientAuth

os.makedirs('../data/tmp', exist_ok=True)
os.makedirs('../data/csv', exist_ok=True)


MAX_THREADS = 10



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


all_users = PickleTable('../data/users.pdb')
all_user_names = all_users.get_column('TT_username')

all_user_names = [name for name in all_user_names if name is not None]

users = PickleTable('../data/bot_users.pdb')
users.add_column('email', exist_ok=True)
users.add_column('cookies', exist_ok=True)

class UserHandler:
	def __init__(self):
		self.users = users
		self.failed = []

		self.update_cookies()
		self.user_dbs = {}
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
	
	def get_user(self, email):
		if email not in self.user_dbs:
			self.user_dbs[email] = User(email)
		return self.user_dbs[email]
	
	

handler = UserHandler()

class User:
	def __init__(self, email):
		self.email = email
		self.cookies:str = handler.cookie(email)
		self.driver = None

		self.db = PickleTable('../data/'+email+'.pdb')
		self.db.add_column('video', 'post_date', exist_ok=True)

		self.db.to_csv('../data/csv/'+self.email+'.csv')



		self.tdb = PickleTable('../data/'+email+'_time.pdb')
		self.tdb.add_column('login', 'active_time', exist_ok=True)

		self.tdb.to_csv('../data/csv/'+self.email+'_time.csv')

		self.active_videos = PickleTable('../data/'+email+'_active_vid.pdb')
		self.active_videos.add_column('video', exist_ok=True)


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

		xprint(f'>> /c/[{self.email}]/=/ stat: /c/active_5_days:/=/ {self.is_active_5_days()}, /c/warmed_up:/=/ {self.is_warmed_up()}, /c/active_time_today:/=/ {self.active_time_today()/60:.2f} minutes', '/=/')

	def is_active_5_days(self):
		# check if user has already logged in for 5 days
		logins = self.tdb.get_column('login')
		days = []
		for login in logins:
			day = login.split(' ')[0] # get date
			if day not in days:
				days.append(day)
			if len(days) >= 5:
				return True
			
		return False
	

	def is_warmed_up(self):
		"""
		Check if user has already spent 4 hours on tiktok
		"""
		# time_spent = sum(self.tdb.get_column('active_time'))
		# return time_spent > 4*60*60

		time_spent = 0
		for cell in self.tdb.get_column('active_time'):
			time_spent += cell
			if time_spent > 4*60*60:
				return True and self.is_active_5_days()
		return False

			


	def active_time_today(self):
		"""
		Time spent today
		"""
		time_spent = 0
		for row in self.tdb.rows():
			time_spent += row['active_time'] if row['login'].split(' ')[0] == dt_now().split(' ')[0] else 0

		return time_spent





	def warm_up(self):
		if self.is_warmed_up():
			xprint(f'>> /g/[{self.email}]/=/ Already warmed up', '/=/')
			return None
		
		
		# check usage today (if user has already spent .5 hours today)
		time_spent = 0
		for row in self.tdb.rows():
			time_spent += row['active_time'] if row['login'].split(' ')[0] == dt_now().split(' ')[0] else 0

		if time_spent > 0.8 * 3600:
			return None

		
		# personal_delay = random.random() * 20 * 60

		# xprint(f">> /ph/{self.email}/=/ is /ph/sleeping/=/ for /ph/{personal_delay//60:.2f} minutes/=/")
		# time.sleep(personal_delay)


		to_waste_scroll = 30 #(random.randint(15, 20) + random.random()) * 60
		to_waste_search = 30  #(random.randint(20, 25) + random.random()) * 60

		to_waste = to_waste_scroll + to_waste_search

		xprint('/y/', f'[{self.email}] Warming up for {to_waste/60:.2f} minutes', '/=/')
		
		search_terms = random.sample(self.search_terms, random.randint(3,7))

		row = self.tdb.add_row({'login':dt_now(), 'active_time':0})

		self.tdb.to_csv('../data/csv/'+self.email+'_time.csv')

		waste_time_start = time.time()
		
		try:
			waste_time(to_waste_scroll, to_waste_search, 
						cookies=self.cookies, 
						search_terms=search_terms, 
						sample_comments=self.comment_terms,
						driver=self.get_dedicated_driver(),
						ignore_users=all_user_names
						)
						
						
		except:
			xprint('/rh/', traceback.format_exc(), '/=/')
		
		row.update({'active_time':time.time() - waste_time_start})
		self.tdb.to_csv('../data/csv/'+self.email+'_time.csv')



		xprint('>> /y/', f'[{self.email}] Warmed up for {row["active_time"]/60:.2f} minutes', '/=/')
		
		xprint(f'>> /y/[{self.email}] Total active time /gh/**today**/=/: /i/{self.active_time_today()/60:.2f} minutes/=/')

	def light_warm_up(self):
		"""runs for 15-25 minutes if the user has already uploaded 3 videos today and not active for 1.5hours today"""
		
		# check usage today
		time_spent = self.active_time_today()
		if time_spent > 1.5*3600:
			return None

		to_waste_scroll = 30 #(random.randint(10, 15) + random.random()) * 60
		to_waste_search = 30 #(random.randint(10, 15) + random.random()) * 60

		to_waste = to_waste_scroll + to_waste_search

		xprint('>> /y/', f'[{self.email}]/=/ Light Warming up for /y/{to_waste/60:.2f} minutes', '/=/')

		row = self.tdb.add_row({'login':dt_now(), 'active_time':0})

		self.tdb.to_csv('../data/csv/'+self.email+'_time.csv')
		
		search_terms = random.sample(self.search_terms, random.randint(3,7))


		time_waste_start = time.time()
		
		try:
			waste_time(to_waste_scroll, to_waste_search,
						cookies=self.cookies, 
						search_terms=search_terms, 
						sample_comments=self.comment_terms,
						driver=self.get_dedicated_driver(),
						ignore_users=all_user_names
						)
						
		except:
			xprint('/rh/', traceback.format_exc(), '/=/')
		
			
		
		row.update({'active_time':time.time() - time_waste_start})

		self.tdb.to_csv('../data/csv/'+self.email+'_time.csv')

		xprint('>> /y/', f'[{self.email}]/=/ Light Warmed up for /y/{row["active_time"]/60:.2f} minutes', '/=/')
		
		xprint(f'>> /y/[{self.email}]/=/ Total active time /gh/today/=/: /i/{self.active_time_today()/60:.2f} minutes/=/')

	def upload(self, video, description):
		vid_name = video.replace("\\", "/").rsplit("/", 1)[-1]
		xprint('>> /y/', f'[{self.email}]/=/ Uploading /gh/{vid_name}', '/=/')

		row = { }

		waste_before = 30 ##(random.randint(10, 15) + random.random()) * 60
		waste_after = 30 #(random.randint(5, 10) + random.random()) * 60

		tdr = self.tdb.add_row({'login':dt_now(), 'active_time':0})

		self.tdb.to_csv('../data/csv/'+self.email+'_time.csv')
		
		upload_time_start = time.time()

		try:
			upload_video(video, 
						description, 
						audio=True, # trending audio
						cookies=self.cookies,
						waste_time_before=waste_before,
						waste_time_after=waste_after,
						driver=self.get_dedicated_driver(),
						)
						
			row = self.db.add_row({'video':video, 'post_date': dt_now()})

			vid_row = self.active_videos.add_row({'video':video})

			self.db.to_csv('../data/csv/'+self.email+'.csv')
		except InsufficientAuth:
			xprint('/rh/', f'[{self.email}] InsufficientAuth\n\tPlease login to TikTok and save the cookies as cookies/{self.email}.cookie', "/=/")

			toast(header='Auth Failed', msg=f'[{self.email}] InsufficientAuth\n\tPlease login to TikTok and save the cookies as cookies/{self.email}.cookie', duration=10)
			
		except:
			xprint(f'/rh/{self.email}\n\n', traceback.format_exc(), '/=/')
		
		tdr.update({'active_time':time.time() - upload_time_start})

		self.tdb.to_csv('../data/csv/'+self.email+'_time.csv')

		xprint('/y/', f'[{self.email}] Uploaded {video}', '/=/')

		xprint(f'/y/[{self.email}] Total active time /gh/**today**/=/: /i/{self.active_time_today()/60:.2f} minutes/=/')

		return row
	
	
	def upload_random(self):
		if not self.is_warmed_up():
			xprint(f'>> /y/[{self.email}]/=/ is not warmed up', '/=/')
			return None
		
		
		# check if today is sunday or wednesday
		if datetime.datetime.today().weekday() in [6]:
			xprint(f'>> /y/[{self.email}]/=/ Today is Sunday or Wednesday (Just doing light warm up)', '/=/')
			self.light_warm_up()
			return None
		
		# check if time is between 1PM EST - 7PM EST
		# Fix time zone
		# tz = timezone('EST')
		# time_now = datetime.datetime.now(tz) 
		# if time_now.hour <= 11 or time_now.hour >= 19:
		# 	xprint(f'>> /y/[{self.email}]/=/ Time is not between 1PM EST - 7PM EST (Just doing light warm up)', '/=/')
		# 	self.light_warm_up()
		# 	return None
		
		
		# check if 3 videos have been uploaded today
		uploaded_today = 0
		if self.db.height >= 3:
			for i in range(1,4):
				if self.db.row(i*-1)['post_date'].split(' ')[0] != dt_now().split(' ')[0]:
					break
				uploaded_today += 1
			else:
				xprint(f'>> /g/[{self.email}]/=/ Todays Upload limit reached (today {uploaded_today}) 	(total {self.db.height} done)', '/=/')
				self.light_warm_up()
				return None

		# xprint(f'>> /y/[{self.email}]/=/ Uploading Random Video (today {uploaded_today}) (total {self.db.height} done)', '/=/')
		
		# personal_delay = random.random() * 15 * 60
		
		# xprint(f">> /ph/{self.email}/=/ is /ph/sleeping/=/ for /ph/{personal_delay//60:.2f} minutes/=/")
		# time.sleep(personal_delay)
		xprint(f'>> /y/[{self.email}]/=/ Waking up', '/=/')
		


		videos = [f.path for f in os.scandir('../Videos') if f.is_file()]
		copy_videos = videos[:]



		# remove already uploaded videos
		for row in self.active_videos.rows():
			if row['video'] in copy_videos:
				copy_videos.remove(row['video'])

		if len(copy_videos) == 0:
			copy_videos = videos[:]
			self.active_videos.clear()

		video = random.choice(copy_videos)

		description = " ".join(random.sample(self.search_terms, random.randint(33,33)))
		description = description

		print(video, description)

		self.upload(video, description)

	def _warm_up_and_upload_thread(self, user, semaphore): 
		with semaphore:
			user.warm_up_and_upload()
 

	def warm_up_and_upload(self):
		self.warm_up()
		self.upload_random()
		self.delete_low_views()
		self.follow_back()
		self.kill_driver()


	def follow_back(self, force=False):
		"""
		Follow back all followers on Wednesday
		"""
		if not force and datetime.datetime.today().weekday() != 2:
			return None
		
		follow_back_all(self.get_dedicated_driver())

	def delete_low_views(self, force=False):
		"""
		Delete videos with less than 100 views only on Sunday
		"""

		if not force and datetime.datetime.today().weekday() != 6:
			return None
		
		delete_low_videos(self.get_dedicated_driver(), 100)




	def get_dedicated_driver(self): # UPDATED
		if self.driver is None:
			self.driver = get_authentic_driver(cookies=self.cookies)
		else:
			try:
				# Try to get the current URL to check if the driver is alive
				self.driver.current_url
			except Exception:
				# If an exception is thrown, the driver is not alive
				try:
					self.driver.quit() # Quit the driver
				except Exception:
					pass
				self.driver = get_authentic_driver(cookies=self.cookies)
		self.driver.maximize_window()
		return self.driver



	def kill_driver(self): 
		try:
			if self.driver is not None:
				# Close any open browser windows
				for window_handle in self.driver.window_handles:
					self.driver.switch_to.window(window_handle)
					self.driver.close()

				# Quit the webdriver
				self.driver.quit()
		except Exception as e:
			print(f"Error during driver cleanup: {e}")
		finally:
			self.driver = None




class TikTokUploader:
	def __init__(self) -> None:
		pass

	def warm_up(self):
		xprint("/y/", "Warming up", "/=/")
		future = []
		with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
			for email in handler.emails():
				user = handler.get_user(email)
				
				# check user logs to check if user has already logged in for 5 days and has spent 5 hours

				# # check if user has already logged in for 5 days

				# otherwise warm up
				future.append(executor.submit(user.warm_up))

				time.sleep(2) # to avoid all threads starting at the same time

		for f in as_completed(future):
			pass

	def upload(self):
		xprint("/y/", "Uploading", "/=/")
		future = []

		with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
			for email in handler.emails():
				time.sleep(random.random()) # to avoid all threads starting at the same time
				user:User = handler.get_user(email)
				future.append(executor.submit(user.upload_random))

				time.sleep(2) # to avoid all threads starting at the same time

		for _ in as_completed(future):
			pass


	def follow_back(self, force=False):
		xprint("/y/", "Following back", "/=/")
		future = []

		with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
			for email in handler.emails():
				time.sleep(random.random())
				user:User = handler.get_user(email)
				future.append(executor.submit(user.follow_back, force=force))

				time.sleep(2) # to avoid all threads starting at the same time

				if force:
					break

		for _ in as_completed(future):
			pass

	def delete_low_views(self, force=False):
		xprint("/y/", "Deleting low views", "/=/")
		future = []

		with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
			for email in handler.emails():
				time.sleep(random.random())
				user:User = handler.get_user(email)
				future.append(executor.submit(user.delete_low_views, force=force))

				time.sleep(2)

				if force:
					break

		for _ in as_completed(future):
			pass


	def warm_up_and_upload(self):
		xprint("/y/", "Warming up and Uploading", "/=/")
		future = []

		with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
      
			semaphore = threading.Semaphore(10)
   
			for email in handler.emails():
				time.sleep(random.random()) # to avoid all threads starting at the same time
				user:User = handler.get_user(email)
				future.append(executor.submit(user._warm_up_and_upload_thread, user, semaphore))

				time.sleep(2) # to avoid all threads starting at the same time

    
		for _ in as_completed(future):
			pass



	def run(self):
		while True:
			handler.update_cookies()
			self.warm_up_and_upload()
			wait_time = (random.randint(20, 30)+ random.random()) * 60
			xprint('/ph/', f'Waiting for {wait_time/60:.2f} minutes to start again', '/=/')
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
	# ttu.delete_low_views(force=True)
			
if __name__ == '__main__':
	main()