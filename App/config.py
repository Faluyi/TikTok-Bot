from os.path import realpath as os_realpath

class AboutApp_ :     #fc=A000
	""" Contains Information about the app and version details"""
	_APP_PATH = os_realpath(__file__)

	data_dir = "./data/"
	# location to store app data
	temp_dir = data_dir + "temp/"
	# location to store user data
	user_data_dir = data_dir + "user_data/"
	# location to store temp data
	cached_webpages_dir = data_dir + ".cached_webpages/"


AboutApp = AboutApp_()

PP_Client_sec = "k7DakZxSESYlRehSlgSGnlrPRqVf2Mtc-tEy1TRBg36T-dfLAxXtiWHx3lZss0nJy3QHbgX3qC6D5AVj"

Limits = {
	"leadG_kw": 5,
	"leadG_count": 500,
}


Rates = {
	"leadG": 1,
}

Conversion_rate = 100 # 100 points = 1$
