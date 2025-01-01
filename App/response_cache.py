import charset_normalizer as chardet
from os.path import isfile
import json

class Cached_Response:
	# TODO: use JSON
	# TODO: Need documentation
	def __init__(self, status_code=None, content = None, content_location = None, headers = None, encoding = None, url = None):
		self.status_code = status_code
		if content is not None:
			self.content = content
		elif content_location is not None:
			if not isfile(content_location):
				return None
			with open(content_location, 'rb') as f:
				self.content = f.read()
		else:
			return None
		self.headers = headers
		self.encoding = encoding
		self.url = url

	def __str__(self):
		return "Cached_Response: %s\n%s\n%s\n%s\n%s" % (self.status_code, self.content, self.headers, self.encoding, self.url)

	def __repr__(self):
		return f'Cached_Response(status_code={self.status_code}, content={self.content}, headers={self.headers}, encoding="{self.encoding}", url="{self.url}")'
	def __bool__(self):
		return not 400 <= self.status_code < 600

	def __getattr__(self, name):
		if name == 'text':
			return self.text_()
		else:
			raise AttributeError("%s instance has no attribute '%s'" % (self.__class__, name))

	def text_(self):
		"""Content of the response, in unicode.

		If Response.encoding is None, encoding will be guessed using
		``charset_normalizer`` or ``chardet``.

		The encoding of the response content is determined based solely on HTTP
		headers, following RFC 2616 to the letter. If you can take advantage of
		non-HTTP knowledge to make a better guess at the encoding, you should
		set ``r.encoding`` appropriately before accessing this property.
		"""

		# Try charset from content-type
		content = None
		encoding = self.encoding

		if not self.content:
			return str('')

		# Fallback to auto-detected encoding.
		if self.encoding is None:
			encoding = chardet.detect(self.content)['encoding']

		# Decode unicode from given encoding.
		try:
			content = str(self.content, encoding, errors='replace')
		except (LookupError, TypeError):
			# A LookupError is raised if the encoding was not found which could
			# indicate a misspelling or similar mistake.
			#
			# A TypeError can be raised if encoding is None
			#
			# So we try blindly encoding.
			content = str(self.content, errors='replace', encoding="utf8")

		return content
		
	@property
	def text(self):
		content = None
		encoding = self.encoding

		if not self.content:
			return str('')

		# Fallback to auto-detected encoding.
		if self.encoding is None:
			encoding = chardet.detect(self.content)['encoding']

		# Decode unicode from given encoding.
		try:
			content = self.content.decode(encoding, errors='replace')
		except (LookupError, TypeError):
			# A LookupError is raised if the encoding was not found which could
			# indicate a misspelling or similar mistake.
			#
			# A TypeError can be raised if encoding is None
			#
			# So we try blindly encoding.
			content = self.content.decode( errors='replace', encoding="utf8")

		return content


	def json(self, **kwargs):
		"""Returns the json-encoded content of a response, if any.

		:param \*\*kwargs: Optional arguments that ``json.loads`` takes.
		:raises ValueError: If the response body does not contain valid json.
		"""
		try:
			return json.loads(
				self.text, **kwargs
			)
		except UnicodeDecodeError:
			pass
		

# x = requests.get('https://www.google.com/')


# from bs4 import BeautifulSoup as bs
# # print(repr(bs(x.text, 'lxml')))
# y = Cached_Response(status_code=x.status_code, content=x.content, headers=x.headers, encoding=x.encoding, url=x.url, history=x.history)

# with open('text_cache.py', 'w') as f: f.write(repr(y))

# z= eval(repr(y))
# print(z)

# print(repr(y))