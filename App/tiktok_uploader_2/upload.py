"""
`tiktok_uploader` module for uploading videos to TikTok

Key Functions
-------------
upload_video : Uploads a single TikTok video
upload_videos : Uploads multiple TikTok videos
"""
from os.path import abspath, exists
from typing import List
import time
import pytz
import datetime
import random
import urllib.parse
import traceback

from selenium.webdriver.common.by import By

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException

from .browsers import get_browser
from .auth import AuthBackend
from . import config, logger
from .utils import bold, green, red, yellow, cyan
from .proxy_auth_extension.proxy_auth_extension import proxy_is_working


def prob(chance):
	"""
	create a random probability range and a function to check if a random number is in that range (fixes timing issues)

	chance: 1 out of chance
	"""
	area = 1/chance
	rand = random.random()

	if rand < .5:
		return lambda x: rand <= x < rand + area

	return lambda x: rand > x >= rand - area

extra_config = {
	'like_chance': prob(20),
	'comment_chance': prob(30),
	'share_chance': prob(30),
	'save_chance': prob(30)
}


def get_authentic_driver(
				auth: AuthBackend = None,
				cookies='',
				username='',
				password='',
				sessionid=None,
				cookies_list=None,
				cookies_str=None,
				proxy: dict = None,
				browser='chrome',
				browser_agent=None,
				headless=False,
				*args, **kwargs):
	"""
	Returns an authenticated driver
	"""

	if not browser_agent: # user-specified browser agent
		logger.debug('Create a %s browser instance %s', browser,
					'in headless mode' if headless else '')
		driver = get_browser(name=browser, headless=headless, proxy=proxy, *args, **kwargs)
	else:
		logger.debug('Using user-defined browser agent')
		driver = browser_agent
	if proxy:
		if proxy_is_working(driver, proxy['host']):
			logger.debug(green('Proxy is working'))
		else:
			logger.error(red('Proxy is not working'))
			driver.quit()
			raise Exception('Proxy is not working')

	if not auth:
		auth = AuthBackend(username=username, password=password, cookies=cookies,
							cookies_list=cookies_list, cookies_str=cookies_str, sessionid=sessionid)

	driver = auth.authenticate_agent(driver)
	driver.maximize_window()
	driver.set_window_size(1920, 1080)
	return driver


def driver_alive(driver) -> bool: # UPDATED
	"""
	Checks if the driver is alive

	Parameters
	----------
	driver : selenium.webdriver
		The selenium webdriver to check

	Returns
	-------
	alive : bool
		Whether or not the driver is alive
	"""
	try:
		driver.current_url
		return True
	except:
		return False


def get_parent(element):
	return element.find_element(By.XPATH, '..' if element.tag_name != 'html' else '.') # if the element is the html tag, return itself

def _get_with_alert(driver, link) -> None:
	try:
		# attempt to refresh the page
		driver.get(link)

		# wait for the alert to appear
		WebDriverWait(driver, config['implicit_wait']).until(EC.alert_is_present())

		logger.debug(green("Alert appeared, accepting"))

		# accept the alert
		driver.switch_to.alert.accept()

		logger.debug(green("Alert accepted"))


		# Wait for the alert to disappear
		WebDriverWait(driver, 10).until(EC.alert_is_present())

		logger.debug(green("Alert disappeared"))
		driver.switch_to.default_content()

		driver.refresh()



		# select body
		_wait_n_find(driver, By.TAG_NAME, 'body').click()

		logger.debug(green("Body clicked"))

	except:
		# if no alert appears, the page is fine
		pass


def _refresh_with_alert(driver) -> None:
	try:
		# attempt to refresh the page
		driver.refresh()

		# wait for the alert to appear
		WebDriverWait(driver, config['implicit_wait']).until(EC.alert_is_present())

		logger.debug(green("Alert appeared, accepting"))

		# accept the alert
		driver.switch_to.alert.accept()

		logger.debug(green("Alert accepted"))

		driver.refresh()


		# Wait for the alert to disappear
		WebDriverWait(driver, 10).until(EC.alert_is_present())

		logger.debug(green("Alert disappeared"))

		driver.switch_to.default_content()
		# select body
		_wait_n_find(driver, By.TAG_NAME, 'body').click()

		logger.debug(green("Body clicked"))



	except:
		# if no alert appears, the page is fine
		pass

def _wait_n_find(driver, selector, pattern, wait=10, multiple=False):
	"""
	Waits for the element to appear and then returns it

	Parameters
	----------
	driver : selenium.webdriver
	selector : By.XPATH or By.CSS_SELECTOR or so on
	pattern : str
		The pattern to search for in the element
	wait : int
		The number of seconds to wait for the element to appear
	"""
	if multiple:
		condition = EC.presence_of_all_elements_located((selector, pattern))
	else:
		condition = EC.presence_of_element_located((selector, pattern))
	element = WebDriverWait(driver, wait).until(condition)
	return element

def _do_comment(driver, comment_text) -> None:
	"""
	Comments on the current video

	Parameters
	----------
	driver : selenium.webdriver
	comment_text : str
		The text to comment
	"""
	if not comment_text:
		return

	logger.debug(green('Commenting'))

	comment_input = _wait_n_find(driver, By.CSS_SELECTOR, config['selectors']['search']['comment_input'], config['implicit_wait'])
	comment_input.click()

	comment_text_ele = _wait_n_find(driver, By.CSS_SELECTOR, config['selectors']['search']['comment_text'], config['implicit_wait'])

	comment_text_ele.send_keys(comment_text)
	comment_text_ele.send_keys(Keys.ENTER)

	logger.debug(green('Commented'))


def _add_audio(driver, audio_title=None) -> None:
	# click the add audio button
	logger.debug(green("Clicking Edit button"))
	button = _wait_n_find(driver, By.CSS_SELECTOR, config['selectors']['upload']['edit_button'], config['implicit_wait'])
	button.click()

	time.sleep(5) # wait for the audio to load

	if type(audio_title) == str:
		logger.debug(green("Searching for audio"))
		# search for the audio
		search_input = _wait_n_find(driver, By.CSS_SELECTOR, config['selectors']['upload']['search_field'], config['implicit_wait'])
		search_input.send_keys(audio_title)
		search_input.send_keys(Keys.ENTER)

		time.sleep(5)

	logger.debug(green("Hovering on the 1st audio"))
	# hover on the 1st audio with actionchains, then click the add button
	audio = _wait_n_find(driver, By.CSS_SELECTOR, config['selectors']['upload']['music_card'], config['implicit_wait'])
	ActionChains(driver).move_to_element(audio).pause(1).perform()

	logger.debug(green("Clicking add button"))
	add_button = _wait_n_find(driver, By.CSS_SELECTOR, config['selectors']['upload']['add_music'], config['implicit_wait'])
	add_button.click()

	time.sleep(5) # wait for the audio to load

	logger.debug(green("Clicking the save button"))
	# click the save button
	save_button = _wait_n_find(driver, By.CSS_SELECTOR, config['selectors']['upload']['save_button'], config['implicit_wait'])
	save_button.click()

	time.sleep(5) # wait for the audio to load

	logger.debug(green("Audio added"))



def search_and_waste_time(driver, search_terms=[], total_waste_time=100, sample_comments=[],ignore_users=[]):
	"""
	Searches and waste time to avoid detection
	"""

	if not search_terms or total_waste_time == 0:
		return 0

	logger.debug(green("Searching and wasting time"))
	wasted = 0

	to_search = random.sample(search_terms, random.randint(1, len(search_terms)))
	logger.debug(green(f"Searching for {to_search}"))
	items = len(to_search)
	divide_time = []
	temp_time = total_waste_time
	for i in range(items):
		if i == items - 1:
			my_time = temp_time

		else:
			my_time = random.randint(1, int(temp_time//items)) + random.random()
		divide_time.append(my_time)
		temp_time -= my_time

	logger.debug(f"Divide time {divide_time}")

	for search_term, my_time in zip(to_search, divide_time):
		# go to main page
		url = 'https://www.tiktok.com/search?q=' + urllib.parse.quote(search_term)
		logger.debug(yellow(f"Searching for {search_term}"))
		_get_with_alert(driver, url)
		logger.debug(yellow("Search Done"))

		my_waste = 0

		time.sleep(10) # wait for the video to load

		try:
			results = driver.find_elements(By.CSS_SELECTOR, config['selectors']['search']['top_item'])
		except:
			results = []


		if not results:
			logger.debug(red("No results found"))
			continue

		random_result = random.choice(results)
		actions = ActionChains(driver)
		actions.move_to_element(random_result).perform()
		random_result.click()

		logger.debug(yellow("Clicking random item"))
		logger.debug(green("Top item clicked"))

		time.sleep(5) # wait for the video to load



		# driver.find_element(By.TAG_NAME, 'body').send_keys('m')

		logger.debug(green("Scrolling and wasting time"))
		while my_waste < my_time:
			_wait_n_find(driver, By.TAG_NAME, 'body').send_keys(Keys.ARROW_DOWN)

			waste = random.randint(1, 20) + random.random()
			time.sleep(waste)
			my_waste += waste


			post_user = _wait_n_find(driver, By.CSS_SELECTOR, config['selectors']['search']['username'], config['implicit_wait'])

			if post_user.text in ignore_users:
				logger.debug(cyan("Post user is in ignore list"))
				continue

			# click the like button
			if extra_config['like_chance'](random.random()):
				time.sleep(1)
				_wait_n_find(driver, By.TAG_NAME, 'body').send_keys('l')
				logger.debug(green("Like button clicked"))
				time.sleep(1)
				my_waste += 2

			if extra_config['comment_chance'](random.random()) and sample_comments:
				time.sleep(1)
				_do_comment(driver, comment_text=random.choice(sample_comments))
				time.sleep(1)
				my_waste += 2

			if extra_config['save_chance'](random.random()):
				time.sleep(1)
				try:
					_btn = get_parent(_wait_n_find(driver, By.CSS_SELECTOR, 'span[data-e2e="undefined-icon"]'))
					actions = ActionChains(driver)
					actions.move_to_element(_btn).perform()
					_btn.click()
					logger.debug(green("Save button clicked"))
					time.sleep(1)
				except:
					logger.debug(red("Save button not found"))
				my_waste += 2

			if extra_config['share_chance'](random.random()):
				time.sleep(1)
				try:
					_btn = _wait_n_find(driver, By.CSS_SELECTOR, 'button[data-e2e="browse-copy"]')
					actions = ActionChains(driver)
					actions.move_to_element(_btn).perform()
					_btn.click()
					logger.debug(green("Share button clicked"))
					time.sleep(1)
				except:
					traceback.print_exc()
					logger.debug(red("Share button not found"))
				my_waste += 2

		wasted += my_waste


	logger.debug(green("Search and waste time done"))
	# refresh the page
	_refresh_with_alert(driver)
	time.sleep(5) # wait for the video to load

	return wasted



def scroll_and_waste_time(driver, total_waste_time=100, sample_comments=[]):
	"""
	Scrolls and waste time to avoid detection
	click down arrow to scroll down
	"""
	if total_waste_time == 0:
		return 0

	logger.debug(green("Scrolling and wasting time"))
	wasted = 0
	# Mute the browser

	# go to main page
	_get_with_alert(driver, config['paths']['main'])

	time.sleep(5) # wait for the video to load

	# driver.find_element(By.TAG_NAME, 'body').send_keys('m')


	while wasted < total_waste_time:
		# _wait_n_find(driver, By.TAG_NAME, 'body').send_keys(Keys.ARROW_DOWN)
		driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ARROW_DOWN)

		waste = random.randint(1, 20) + random.random()
		time.sleep(waste)
		wasted += waste

		# click the like button
		if extra_config['like_chance'](random.random()):
			# _wait_n_find(driver, By.TAG_NAME, 'body').send_keys('l')
			driver.find_element(By.TAG_NAME, 'body').send_keys('l')

			logger.debug(green("Like button clicked"))
			time.sleep(1)
			wasted += 1

		# if random.random() > extra_config['comment_chance'] and sample_comments:
		#     time.sleep(1)
		#     _do_comment(driver, comment_text=random.choice(sample_comments))
		#     time.sleep(1)
		#     wasted += 2


	logger.debug(green("Scroll and waste time done"))

	# refresh the page
	_refresh_with_alert(driver)
	time.sleep(5) # wait for the video to load

	return wasted


def waste_time(waste_scroll_time=100,
				waste_search_time=100,
				search_terms=[],
				sample_comments=[],
				driver=None,
				auth: AuthBackend = None,
				cookies='',
				username='',
				password='',
				sessionid=None,
				cookies_list=None,
				cookies_str=None,
				proxy: dict = None,
				browser='chrome',
				browser_agent=None,
				on_complete=None,
				headless=False,
				ignore_users=[], # users to ignore
				*args, **kwargs):
	"""
	Uploads multiple videos to TikTok

	Parameters
	----------
	proxy: dict
		A dictionary containing the proxy user, pass, host and port
	browser : str
		The browser to use for uploading
	browser_agent : selenium.webdriver
		A selenium webdriver object to use for uploading
	on_complete : function
		A function to call when the upload is complete
	headless : bool
		Whether or not the browser should be run in headless mode
	num_retries : int
		The number of retries to attempt if the upload fails
	options : SeleniumOptions
		The options to pass into the browser -> custom privacy settings, etc.
	*args :
		Additional arguments to pass into the upload function
	**kwargs :
		Additional keyword arguments to pass into the upload function

	Returns
	-------
	failed : list
		A list of videos which failed to upload
	"""

	logger.debug(green(f"Wasting time for {waste_scroll_time} seconds for scrolling and {waste_search_time} seconds for searching"))

	if driver is None or not driver_alive(driver): # UPDATED
		driver = get_authentic_driver(
				auth=auth,
				cookies=cookies,
				username=username,
				password=password,
				sessionid=sessionid,
				cookies_list=cookies_list,
				cookies_str=cookies_str,
				proxy=proxy,
				browser=browser,
				browser_agent=browser_agent,
				headless=headless,
				*args, **kwargs
			)

	try:
		# search 1st to make things more personalized
		search_and_waste_time(driver, search_terms,
							  total_waste_time=waste_search_time,
							  sample_comments=sample_comments,
							  ignore_users=ignore_users
							  )

		scroll_and_waste_time(driver,
							  total_waste_time=waste_scroll_time,
							  sample_comments=sample_comments)
		if on_complete is callable: # calls the user-specified on-complete function
			on_complete(waste_time)

		success = True

	except Exception as exception:
		logger.error(red('Failed to waste time'))
		traceback.print_exc()
		logger.error(exception)

		success = False


	if config['quit_on_end']:
		driver.quit()

	return success


# /html/body/div[1]/div[2]/div[2]/div[1]/div[12]/div/div[2]/div[1]/div/div[1]/div[2]/div/video
# /html/body/div[1]/div[2]/div[2]/div[1]/div[12]/div/div[2]/div[2]/button[1]



def upload_video(filename=None,
				description='',
				audio=None,
				auth: AuthBackend = None,
				cookies='',
				schedule: datetime.datetime = None,
				driver=None,
				username='',
				password='',
				sessionid=None,
				cookies_list=None,
				cookies_str=None,
				proxy=None,
				browser='chrome',
				browser_agent=None,
				on_complete=None,
				headless=False,
				num_retires : int = 1,
				waste_time_before : float = 0,
				waste_time_after : float = 0,
				*args, **kwargs):
	"""
	Uploads a single TikTok video.

	Consider using `upload_videos` if using multiple videos

	Parameters
	----------
	filename : str
		The path to the video to upload
	description : str
		The description to set for the video
	schedule: datetime.datetime
		The datetime to schedule the video, must be naive or aware with UTC timezone, if naive it will be aware with UTC timezone
	cookies : str
		The cookies to use for uploading
	sessionid: str
		The `sessionid` is the only required cookie for uploading,
			but it is recommended to use all cookies to avoid detection
	"""

	return upload_videos(
			videos=[ { 'path': filename, 'description': description, 'schedule': schedule , 'audio': audio} ],
			auth=auth,
			cookies=cookies,
			username=username,
			password=password,
			driver=driver,
			sessionid=sessionid,
			cookies_list=cookies_list,
			cookies_str=cookies_str,
			proxy=proxy,
			browser=browser,
			browser_agent=browser_agent,
			on_complete=on_complete,
			headless=headless,
			num_retires=num_retires,
			waste_time_before=waste_time_before,
			waste_time_after=waste_time_after,
			*args, **kwargs
		)



def upload_videos(videos: list = None,
				driver=None,
				auth: AuthBackend = None,
				cookies='',
				username='',
				password='',
				sessionid=None,
				cookies_list=None,
				cookies_str=None,
				proxy: dict = None,
				browser='chrome',
				browser_agent=None,
				on_complete=None,
				headless=False,
				num_retires : int = 1,
				waste_time_before : float = 0,
				waste_time_after : float = 0,
				retries : int = 3,
				current_retry : int = 0,
				*args, **kwargs):
	"""
	Uploads multiple videos to TikTok

	Parameters
	----------
	videos : list
		A list of dictionaries containing the video's ('path') and description ('description')
	proxy: dict
		A dictionary containing the proxy user, pass, host and port
	browser : str
		The browser to use for uploading
	browser_agent : selenium.webdriver
		A selenium webdriver object to use for uploading
	on_complete : function
		A function to call when the upload is complete
	headless : bool
		Whether or not the browser should be run in headless mode
	num_retries : int
		The number of retries to attempt if the upload fails
	options : SeleniumOptions
		The options to pass into the browser -> custom privacy settings, etc.
	*args :
		Additional arguments to pass into the upload function
	**kwargs :
		Additional keyword arguments to pass into the upload function

	Returns
	-------
	failed : list
		A list of videos which failed to upload
	"""
	videos = _convert_videos_dict(videos)

	if videos and len(videos) > 1:
		logger.debug(green(f"Uploading {len(videos)} videos"))

	if driver is None or not driver_alive(driver): # UPDATED
		driver = get_authentic_driver(
				auth=auth,
				cookies=cookies,
				username=username,
				password=password,
				sessionid=sessionid,
				cookies_list=cookies_list,
				cookies_str=cookies_str,
				proxy=proxy,
				browser=browser,
				browser_agent=browser_agent,
				headless=headless,
				*args, **kwargs
			)
		

	failed = []
	# uploads each video
	for video in videos:
		try:
			logger.debug(green("Uploading video"))
			path = abspath(video.get('path'))
			description = video.get('description', '')
			schedule = video.get('schedule', None)
			audio = video.get('audio', None)

			if waste_time_before:
				scroll_and_waste_time(driver, waste_time_before)

			logger.debug(green('Posting %s%s'), bold(video.get('path')),
			f'\n{" " * 15}with description: {bold(description)}' if description else '')

			# Video must be of supported type
			if not _check_valid_path(path):
				logger.debug(red(f'{path} is invalid, skipping'))
				failed.append(video)
				continue

			# Video must have a valid datetime for tiktok's scheduler
			if schedule:
				timezone = pytz.UTC
				if schedule.tzinfo is None:
					schedule = schedule.astimezone(timezone)
				elif int(schedule.utcoffset().total_seconds()) == 0:  # Equivalent to UTC
					schedule = timezone.localize(schedule)
				else:
					logger.debug(red(f'{schedule} is invalid, the schedule datetime must be naive or aware with UTC timezone, skipping'))
					failed.append(video)
					continue

				valid_tiktok_minute_multiple = 5
				schedule = _get_valid_schedule_minute(schedule, valid_tiktok_minute_multiple)
				if not _check_valid_schedule(schedule):
					logger.debug(red(f'{schedule} is invalid, the schedule datetime must be as least 20 minutes in the future, and a maximum of 10 days, skipping'))
					failed.append(video)
					continue

			logger.debug(green("Filling upload form"))
			complete_upload_form(driver, path, description, schedule, audio,
								 num_retires=num_retires, headless=headless,
								 *args, **kwargs)
			logger.debug(green("Video uploaded"))

			if waste_time_after:
				scroll_and_waste_time(driver, waste_time_after)

		except Exception as exception:
			logger.error(red(f'Failed to upload {path}'))
			if current_retry < retries:
				logger.error(red(f'Retrying'))
				return upload_videos(videos=videos,
									driver=driver,
									auth=auth,
									cookies=cookies,
									username=username,
									password=password,
									sessionid=sessionid,
									cookies_list=cookies_list,
									cookies_str=cookies_str,
									proxy=proxy,
									browser=browser,
									browser_agent=browser_agent,
									on_complete=on_complete,
									headless=headless,
									num_retires=num_retires,
									waste_time_before=0, # waste time before only on the first try
									waste_time_after=0, # waste time after only on the first try
									retries=retries,
									current_retry=current_retry + 1,
									*args, **kwargs)
			logger.error(traceback.format_exc())
			failed.append(video)

		if on_complete is callable: # calls the user-specified on-complete function
			on_complete(video)

	if config['quit_on_end']:
		driver.quit()

	return failed


def go_to_profile(driver):
	"""
	Goes to the profile page
	"""
	# check if user is in home page
	if driver.current_url != config['paths']['main']:
		driver.get(config['paths']['main'])
		time.sleep(5)

	_wait_n_find(driver, By.CSS_SELECTOR, config['selectors']['login']['profile']).click()

	time.sleep(10)

def go_to_followers(driver):
	"""
	Goes to the followers page
	"""
	# _wait_n_find(driver, By.CSS_SELECTOR, config['selectors']['login']['followers']).click()
	driver.find_element(By.CSS_SELECTOR, config['selectors']['login']['followers']).click()

	time.sleep(10)

def follow_back_all(driver):
	"""
	Follows back all followers
	"""
	logger.debug(green("Following back all followers"))

	logger.debug("Going to profile")
	go_to_profile(driver)

	logger.debug("Going to followers")
	go_to_followers(driver)

	logger.debug("Clicking followers box")

	followers = _wait_n_find(driver, By.CSS_SELECTOR, config['selectors']['login']['followers_box'], config['implicit_wait'])

	logger.debug("Getting follow buttons")
	follow_btns = followers.find_elements(By.CSS_SELECTOR, config['selectors']['login']['follow_back'])

	logger.debug("Following back all followers")

	for follow_button in follow_btns:
		try:
			# scroll to the follow button
			actions = ActionChains(driver)
			actions.move_to_element(follow_button).perform()

			if follow_button.text == 'Following' or follow_button.text == 'Requested' or follow_button.text == 'Friends':
				continue
			if follow_button.text.startswith('Follow'):
				follow_button.click()
				time.sleep(1)
		except:
			pass

	logger.debug(green("Followed back all followers"))


def delete_low_videos(driver, min_views=100):
	"""
	Deletes all videos with less than min_views views
	"""
	logger.debug(green("Deleting all videos with less than %s views"), min_views)

	_delete_low_views(driver, min_views)


	logger.debug(green("delete_low_videos >>  Deleted all videos with less than %s views"), min_views)

def _delete_low_views(driver, min_views=100):
	logger.debug("delete_low_videos >>  Going to profile")
	go_to_profile(driver)

	time.sleep(5)

	logger.debug("delete_low_videos >>  Clicking videos box")
	videos_counts = driver.find_elements(By.CSS_SELECTOR, config['selectors']['login']['videos_count'])

	view = 0

	for videos_count in videos_counts:
		action = ActionChains(driver)
		action.move_to_element(videos_count).perform() # to make sure it keeps scrolling down
		if int(videos_count.text) < min_views:
			view = int(videos_count.text)
			videos_count.click()
			break

	else:
		return

	time.sleep(10)

	logger.debug("delete_low_videos >>  Hovering over 3dots")
	ActionChains(driver).move_to_element(_wait_n_find(driver, By.CSS_SELECTOR, config['selectors']['login']['three_dots'])).perform()

	logger.debug("delete_low_videos >>  Clicking delete button")
	_wait_n_find(driver, By.CSS_SELECTOR, config['selectors']['login']['delete_video']).click()

	time.sleep(2)

	logger.debug("delete_low_videos >>  Clicking confirm delete button")
	_wait_n_find(driver, By.CSS_SELECTOR, config['selectors']['login']['confirm_delete_video']).click()

	logger.debug(green("delete_low_videos >>  Deleted a video with"))

	time.sleep(5)

	_delete_low_views(driver, min_views)


	






	logger.debug(green("Deleted all videos with less than %s views"), min_views)


def complete_upload_form(driver, path: str, description: str, schedule: datetime.datetime, audio:str, headless=False, *args, **kwargs) -> None:
	"""
	Actually uploads each video

	Parameters
	----------
	driver : selenium.webdriver
		The selenium webdriver to use for uploading
	path : str
		The path to the video to upload
	"""
	_go_to_upload(driver)
	#  _remove_cookies_window(driver)
	_set_video(driver, path=path, **kwargs)
	logger.debug(green("Video set"))

	_remove_split_window(driver)
	_set_interactivity(driver, **kwargs)
	logger.debug(green("Interactivity set"))

	_set_description(driver, description)
	logger.debug(green("Description set"))

	if schedule:
		_set_schedule_video(driver, schedule)

	if audio:
		_add_audio(driver, audio)

	_post_video(driver)

	_return_to_post_list(driver)


def _return_to_post_list(driver) -> None:
	logger.debug(green("Returning to post list"))
	_wait_n_find(driver, By.CSS_SELECTOR, config['selectors']['upload']['go_to_upload_list']).click()

	time.sleep(5)


def _go_to_upload(driver) -> None:
	"""
	Navigates to the upload page, switches to the iframe and waits for it to load

	Parameters
	----------
	driver : selenium.webdriver
	"""
	logger.debug(green('Navigating to upload page'))

	# if the upload page is not open, navigate to it
	if driver.current_url != config['paths']['upload']:
		driver.get(config['paths']['upload'])
	# otherwise, refresh the page and accept the reload alert
	else:
		_refresh_with_alert(driver)

	# changes to the iframe
	_change_to_upload_iframe(driver)

	# waits for the iframe to load
	# root_selector = EC.presence_of_element_located((By.ID, 'root'))
	# WebDriverWait(driver, config['explicit_wait']).until(root_selector)

	# Return to default webpage
	# driver.switch_to.default_content()

def _change_to_upload_iframe(driver) -> None:
    """
    Switch to the iframe of the upload page

    Parameters
    ----------
    driver : selenium.webdriver
    """
    try:
        iframe_selector = EC.presence_of_element_located(
            (By.XPATH, config['selectors']['upload']['iframe'])
        )
        iframe = WebDriverWait(driver, config['extra_explicit_wait']).until(iframe_selector)
        driver.switch_to.frame(iframe)

        logger.debug("Switched to iframe")
    except TimeoutException:
        logger.error(red("Timeout while waiting for the iframe. Unable to switch to iframe."))

def _set_description(driver, description: str) -> None:
	"""
	Sets the description of the video

	Parameters
	----------
	driver : selenium.webdriver
	description : str
		The description to set
	"""
	if description is None:
		# if no description is provided, filename
		return

	logger.debug(green('Setting description'))

	# Remove any characters outside the BMP range (emojis, etc) & Fix accents
	description = description.encode('utf-8', 'ignore').decode('utf-8')

	saved_description = description # save the description in case it fails

	desc = _wait_n_find(driver, By.XPATH, config['selectors']['upload']['description'])

	# desc populates with filename before clearing
	WebDriverWait(driver, config['explicit_wait']).until(lambda driver: desc.text != '')

	_clear(desc)

	try:
		while description:
			nearest_mention = description.find('@')
			nearest_hash = description.find('#')

			if nearest_mention == 0 or nearest_hash == 0:
				desc.send_keys('@' if nearest_mention == 0 else '#')

				name = description[1:].split(' ')[0]
				if nearest_mention == 0: # @ case
					mention_xpath = config['selectors']['upload']['mention_box']
					condition = EC.presence_of_element_located((By.XPATH, mention_xpath))
					mention_box = WebDriverWait(driver, config['explicit_wait']).until(condition)
					mention_box.send_keys(name)
				else:
					desc.send_keys(name)

				time.sleep(config['implicit_wait'])

				if nearest_mention == 0: # @ case
					mention_xpath = config['selectors']['upload']['mentions'].format('@' + name)
					condition = EC.presence_of_element_located((By.XPATH, mention_xpath))
				else:
					hashtag_xpath = config['selectors']['upload']['hashtags'].format(name)
					condition = EC.presence_of_element_located((By.XPATH, hashtag_xpath))

				# if the element never appears (timeout exception) remove the tag and continue
				try:
					elem = WebDriverWait(driver, config['implicit_wait']).until(condition)
				except:
					desc.send_keys(Keys.BACKSPACE * (len(name) + 1))
					description = description[len(name) + 2:]
					continue

				ActionChains(driver).move_to_element(elem).click(elem).perform()

				description = description[len(name) + 2:]
			else:
				min_index = _get_splice_index(nearest_mention, nearest_hash, description)

				desc.send_keys(description[:min_index])
				description = description[min_index:]

		logger.debug(green("Description set"))
	except Exception as exception:
		logger.debug(red(f'Failed to set description: {exception}'))
		_clear(desc)
		desc.send_keys(saved_description) # if fail, use saved description




def _clear(element) -> None:
	"""
	Clears the text of the element (an issue with the TikTok website when automating)

	Parameters
	----------
	element
		The text box to clear
	"""
	element.send_keys(2 * len(element.text) * Keys.BACKSPACE)

def _click_upload_card(driver) -> None:
    """
    Clicks on the uploader card to open the file dialog

    Parameters
    ----------
    driver : selenium.webdriver
    """
    upload_card_selector = EC.element_to_be_clickable((By.XPATH, '//*[@id="root"]/div/div/div/div/div/div/div/div'))
    upload_card = WebDriverWait(driver, config['extra_explicit_wait']).until(upload_card_selector)
    upload_card.click()

    logger.debug("Clicked on the uploader card")

def _set_video(driver, path: str = '', num_retries: int = 3, **kwargs) -> None:
    """
    Sets the video to upload UPDATED

    Parameters
    ----------
    driver : selenium.webdriver
    path : str
        The path to the video to upload
    num_retries : number of retries (can occasionally fail)
    """
    # uploads the element
    logger.debug(green('Uploading video file'))

    for trial in range(num_retries):
        try:
            # Click on the uploader card to open the file dialog
            _click_upload_card(driver)

            # Wait for the upload progress bar to disappear (assuming it shows up)
            upload_finished_selector = (By.XPATH, config['selectors']['upload']['upload_finished'])
            WebDriverWait(driver, config['extra_explicit_wait']).until(
                EC.invisibility_of_element_located(upload_finished_selector)
            )

            # Wait for the video to upload (assuming upload confirmation is visible)
            upload_confirmation_selector = (By.XPATH, config['selectors']['upload']['upload_confirmation'])
            WebDriverWait(driver, config['extra_explicit_wait']).until(
                EC.presence_of_element_located(upload_confirmation_selector)
            )

            # Wait until a non-draggable image is found
            process_confirmation_selector = (By.XPATH, config['selectors']['upload']['process_confirmation'])
            WebDriverWait(driver, config['extra_explicit_wait']).until(
                EC.presence_of_element_located(process_confirmation_selector)
            )

            logger.debug(green('Process confirmation Done'))
            return
        except TimeoutException:
            logger.debug(red(f'Timeout during upload attempt {trial + 1}/{num_retries}'))
            logger.debug(red(traceback.format_exc()))

            if trial < num_retries - 1:
                logger.debug('RETRYING')
            time.sleep(5)

    raise FailedToUpload()

def _remove_cookies_window(driver) -> None:
	"""
	Removes the cookies window if it is open

	Parameters
	----------
	driver : selenium.webdriver
	"""

	logger.debug(green('Removing cookies window'))
	cookies_banner = WebDriverWait(driver, config['implicit_wait']).until(
		EC.presence_of_element_located((By.TAG_NAME, config['selectors']['upload']['cookies_banner']['banner'])))

	item = WebDriverWait(driver, config['implicit_wait']).until(
		EC.visibility_of(cookies_banner.shadow_root.find_element(By.CSS_SELECTOR, config['selectors']['upload']['cookies_banner']['button'])))

	# Wait that the Decline all button is clickable
	decline_button = WebDriverWait(driver, config['implicit_wait']).until(
		EC.element_to_be_clickable(item.find_elements(By.TAG_NAME, 'button')[0]))

	decline_button.click()

def _remove_split_window(driver) -> None:
	"""
	Remove the split window if it is open

	Parameters
	----------
	driver : selenium.webdriver
	"""
	logger.debug(green('Removing split window'))
	window_xpath = config['selectors']['upload']['split_window']

	try:
		condition = EC.presence_of_element_located((By.XPATH, window_xpath))
		window = WebDriverWait(driver, config['implicit_wait']).until(condition)
		window.click()

		logger.debug(green("Split window removed"))
	except TimeoutException:
		logger.debug("Split window not found or operation timed out")
	except Exception as exception:
		logger.debug(f"Failed to remove split window")

def _set_interactivity(driver, comment=True, stitch=True, duet=True, *args, **kwargs) -> None:
	"""
	Sets the interactivity settings of the video

	Parameters
	----------
	driver : selenium.webdriver
	comment : bool
		Whether or not to allow comments
	stitch : bool
		Whether or not to allow stitching
	duet : bool
		Whether or not to allow duets
	"""
	try:
		logger.debug(green('Setting interactivity settings'))

		comment_box = _wait_n_find(driver, By.XPATH, config['selectors']['upload']['comment'])
		stitch_box = _wait_n_find(driver, By.XPATH, config['selectors']['upload']['stitch'])
		duet_box = _wait_n_find(driver, By.XPATH, config['selectors']['upload']['duet'])

		# xor the current state with the desired state
		if comment ^ comment_box.is_selected():
			comment_box.click()

		if stitch ^ stitch_box.is_selected():
			stitch_box.click()

		if duet ^ duet_box.is_selected():
			duet_box.click()

		logger.debug(green('Interactivity settings set'))
	except Exception as _:
		logger.error(red('Failed to set interactivity settings'))


def _set_schedule_video(driver, schedule: datetime.datetime) -> None:
	"""
	Sets the schedule of the video

	Parameters
	----------
	driver : selenium.webdriver
	schedule : datetime.datetime
		The datetime to set
	"""

	logger.debug(green('Setting schedule'))

	driver_timezone = __get_driver_timezone(driver)
	schedule = schedule.astimezone(driver_timezone)

	month = schedule.month
	day = schedule.day
	hour = schedule.hour
	minute = schedule.minute

	try:
		switch = _wait_n_find(driver, By.XPATH, config['selectors']['schedule']['switch'])
		switch.click()
		__date_picker(driver, month, day)
		__time_picker(driver, hour, minute)
	except Exception as e:
		msg = f'Failed to set schedule: {e}'
		print(msg)
		logger.error(red(msg))
		raise FailedToUpload()



def __date_picker(driver, month: int, day: int) -> None:
	logger.debug(green('Picking date'))

	condition = EC.presence_of_element_located(
		(By.XPATH, config['selectors']['schedule']['date_picker'])
		)
	date_picker = WebDriverWait(driver, config['implicit_wait']).until(condition)
	date_picker.click()

	condition = EC.presence_of_element_located(
		(By.XPATH, config['selectors']['schedule']['calendar'])
	)
	calendar = WebDriverWait(driver, config['implicit_wait']).until(condition)

	calendar_month = _wait_n_find(driver, By.XPATH, config['selectors']['schedule']['calendar_month']).text
	n_calendar_month = datetime.datetime.strptime(calendar_month, '%B').month
	if n_calendar_month != month:  # Max can be a month before or after
		if n_calendar_month < month:
			arrow = driver.find_elements(By.XPATH, config['selectors']['schedule']['calendar_arrows'])[-1]
		else:
			arrow = driver.find_elements(By.XPATH, config['selectors']['schedule']['calendar_arrows'])[0]
		arrow.click()
	valid_days = driver.find_elements(By.XPATH, config['selectors']['schedule']['calendar_valid_days'])

	day_to_click = None
	for day_option in valid_days:
		if int(day_option.text) == day:
			day_to_click = day_option
			break
	if day_to_click:
		day_to_click.click()
	else:
		raise Exception('Day not found in calendar')

	__verify_date_picked_is_correct(driver, month, day)


def __verify_date_picked_is_correct(driver, month: int, day: int):
	date_selected = _wait_n_find(driver, By.XPATH, config['selectors']['schedule']['date_picker']).text
	date_selected_month = int(date_selected.split('-')[1])
	date_selected_day = int(date_selected.split('-')[2])

	if date_selected_month == month and date_selected_day == day:
		logger.debug(green('Date picked correctly'))
	else:
		msg = f'Something went wrong with the date picker, expected {month}-{day} but got {date_selected_month}-{date_selected_day}'
		logger.error(red(msg))
		raise Exception(msg)


def __time_picker(driver, hour: int, minute: int) -> None:
	logger.debug(green('Picking time'))

	condition = EC.presence_of_element_located(
		(By.XPATH, config['selectors']['schedule']['time_picker'])
		)
	time_picker = WebDriverWait(driver, config['implicit_wait']).until(condition)
	time_picker.click()

	condition = EC.presence_of_element_located(
		(By.XPATH, config['selectors']['schedule']['time_picker_container'])
	)
	time_picker_container = WebDriverWait(driver, config['implicit_wait']).until(condition)

	# 00 = 0, 01 = 1, 02 = 2, 03 = 3, 04 = 4, 05 = 5, 06 = 6, 07 = 7, 08 = 8, 09 = 9, 10 = 10, 11 = 11, 12 = 12,
	# 13 = 13, 14 = 14, 15 = 15, 16 = 16, 17 = 17, 18 = 18, 19 = 19, 20 = 20, 21 = 21, 22 = 22, 23 = 23
	hour_options = driver.find_elements(By.XPATH, config['selectors']['schedule']['timepicker_hours'])
	# 00 == 0, 05 == 1, 10 == 2, 15 == 3, 20 == 4, 25 == 5, 30 == 6, 35 == 7, 40 == 8, 45 == 9, 50 == 10, 55 == 11
	minute_options = driver.find_elements(By.XPATH, config['selectors']['schedule']['timepicker_minutes'])

	hour_to_click = hour_options[hour]
	minute_option_correct_index = int(minute / 5)
	minute_to_click = minute_options[minute_option_correct_index]

	driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", hour_to_click)
	hour_to_click.click()
	driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", minute_to_click)
	minute_to_click.click()

	# click somewhere else to close the time picker
	time_picker.click()

	time.sleep(.5)  # wait for the DOM change
	__verify_time_picked_is_correct(driver, hour, minute)


def __verify_time_picked_is_correct(driver, hour: int, minute: int):
	time_selected = _wait_n_find(driver, By.XPATH, config['selectors']['schedule']['time_picker_text']).text
	time_selected_hour = int(time_selected.split(':')[0])
	time_selected_minute = int(time_selected.split(':')[1])

	if time_selected_hour == hour and time_selected_minute == minute:
		logger.debug(green('Time picked correctly'))
	else:
		msg = f'Something went wrong with the time picker, ' \
			  f'expected {hour:02d}:{minute:02d} ' \
			  f'but got {time_selected_hour:02d}:{time_selected_minute:02d}'
		logger.error(red(msg))
		raise Exception(msg)


def _post_video(driver) -> None:
	"""
	Posts the video by clicking the post button

	Parameters
	----------
	driver : selenium.webdriver
	"""
	logger.debug(green('Clicking the post button'))

	try:
		post = WebDriverWait(driver, config['implicit_wait']).until(EC.element_to_be_clickable((By.XPATH, config['selectors']['upload']['post'])))
		action = ActionChains(driver)
		action.move_to_element(post).perform()
		post.click()
	except ElementClickInterceptedException:
		logger.debug(yellow("Trying to click on the button again"))
		driver.execute_script('document.querySelector(".btn-post > button").click()')

	# waits for the video to upload
	post_confirmation = EC.presence_of_element_located(
		(By.XPATH, config['selectors']['upload']['post_confirmation'])
		)
	WebDriverWait(driver, config['extra_explicit_wait']).until(post_confirmation)

	logger.debug(green('Video posted successfully'))


# HELPERS

def _check_valid_path(path: str) -> bool:
	"""
	Returns whether or not the filetype is supported by TikTok
	"""
	return exists(path) and path.split('.')[-1] in config['supported_file_types']


def _get_valid_schedule_minute(schedule, valid_multiple) -> datetime.datetime:
	"""
	Returns a datetime.datetime with valid minute for TikTok
	"""
	if _is_valid_schedule_minute(schedule.minute, valid_multiple):
		return schedule
	else:
		return _set_valid_schedule_minute(schedule, valid_multiple)


def _is_valid_schedule_minute(minute, valid_multiple) -> bool:
	if minute % valid_multiple != 0:
		return False
	else:
		return True


def _set_valid_schedule_minute(schedule, valid_multiple) -> datetime.datetime:
	minute = schedule.minute

	remainder = minute % valid_multiple
	integers_to_valid_multiple = 5 - remainder
	schedule += datetime.timedelta(minutes=integers_to_valid_multiple)

	return schedule


def _check_valid_schedule(schedule: datetime.datetime) -> bool:
	"""
	Returns if the schedule is supported by TikTok
	"""
	valid_tiktok_minute_multiple = 5
	margin_to_complete_upload_form = 5

	datetime_utc_now = pytz.UTC.localize(datetime.datetime.utcnow())
	min_datetime_tiktok_valid = datetime_utc_now + datetime.timedelta(minutes=15)
	min_datetime_tiktok_valid += datetime.timedelta(minutes=margin_to_complete_upload_form)
	max_datetime_tiktok_valid = datetime_utc_now + datetime.timedelta(days=10)
	if schedule < min_datetime_tiktok_valid \
			or schedule > max_datetime_tiktok_valid:
		return False
	elif not _is_valid_schedule_minute(schedule.minute, valid_tiktok_minute_multiple):
		return False
	else:
		return True


def _get_splice_index(nearest_mention: int, nearest_hashtag: int, description: str) -> int:
	"""
	Returns the index to splice the description at

	Parameters
	----------
	nearest_mention : int
		The index of the nearest mention
	nearest_hashtag : int
		The index of the nearest hashtag

	Returns
	-------
	int
		The index to splice the description at
	"""
	if nearest_mention == -1 and nearest_hashtag == -1:
		return len(description)
	elif nearest_hashtag == -1:
		return nearest_mention
	elif nearest_mention == -1:
		return nearest_hashtag
	else:
		return min(nearest_mention, nearest_hashtag)

def _convert_videos_dict(videos_list_of_dictionaries) -> List:
	"""
	Takes in a videos dictionary and converts it.

	This allows the user to use the wrong stuff and thing to just work
	"""
	if not videos_list_of_dictionaries:
		raise RuntimeError("No videos to upload")

	valid_path = config['valid_path_names']
	valid_description = config['valid_descriptions']

	correct_path = valid_path[0]
	correct_description = valid_description[0]

	def intersection(lst1, lst2):
		""" return the intersection of two lists """
		return list(set(lst1) & set(lst2))

	return_list = []
	for elem in videos_list_of_dictionaries:
		# preprocess the dictionary
		elem = {k.strip().lower(): v for k, v in elem.items()}

		keys = elem.keys()
		path_intersection = intersection(valid_path, keys)
		description_intersection = intersection(valid_description, keys)

		if path_intersection:
			# we have a path
			path = elem[path_intersection.pop()]

			if not _check_valid_path(path):
				raise RuntimeError("Invalid path: " + path)

			elem[correct_path] = path
		else:
			# iterates over the elem and find a key which is a path with a valid extension
			for _, value in elem.items():
				if _check_valid_path(value):
					elem[correct_path] = value
					break
			else:
				# no valid path found
				raise RuntimeError("Path not found in dictionary: " + str(elem))

		if description_intersection:
			# we have a description
			elem[correct_description] = elem[description_intersection.pop()]
		else:
			# iterates over the elem and finds a description which is not a valid path
			for _, value in elem.items():
				if not _check_valid_path(value):
					elem[correct_description] = value
					break
			else:
				elem[correct_description] = '' # null description is fine

		return_list.append(elem)

	return return_list

def __get_driver_timezone(driver) -> pytz.timezone:
	"""
	Returns the timezone of the driver
	"""
	timezone_str = driver.execute_script("return Intl.DateTimeFormat().resolvedOptions().timeZone")
	return pytz.timezone(timezone_str)

class DescriptionTooLong(Exception):
	"""
	A video description longer than the maximum allowed by TikTok's website (not app) uploader
	"""

	def __init__(self, message=None):
		super().__init__(message or self.__doc__)


class FailedToUpload(Exception):
	"""
	A video failed to upload
	"""

	def __init__(self, message=None):
		super().__init__(message or self.__doc__)
