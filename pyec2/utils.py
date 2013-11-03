import os
import logging
from ConfigParser import SafeConfigParser, NoSectionError

HOME = os.environ['HOME']

class Utils:

	def __init__(self, key_extension=None):
		self.key_extension = key_extension

	def _caseify(self, string):
		"""Convert string to first-character-lowercase
		"""
		if string is not None:
			return string[:1].lower() + string[1:]
		return string

	def _stripWhiteSpace(self, string):
		if string is not None:
			return string.replace(' ', '')
		return string

	def keyExt(self, string):
		return '{}.{}'.format(string, self.key_extension.replace('.', '') if self.key_extension is not None else 'pem')

	def indent(self, string):
		if string is not None:
			return '\t{}'.format(string)
		return string

	def prepare(self, string):
		return self._stripWhiteSpace(self._caseify(string))

	def printExceptions(self, list):
		no_file = False
		for e in list:
			print e
			if 'file' in e:
				no_file = True
		if no_file:
			print 'It seems I couldn\'t find any configuration files to use,\nplease run pyec2 with the --new_config flag'

	def log(self, debug_level='debug'):
		level = {
					'debug': logging.DEBUG,
					'info': logging.INFO,
					'warning': logging.WARNING,
					'error': logging.ERROR,
					'critical': logging.CRITICAL,
				}
		logger = logging.getLogger('pyec2.logger')
		logger.setLevel(level[debug_level.lower()])
		handler = logging.handlers.RotatingFileHandler('/tmp/pyec2.log', maxBytes=2097152, backupCount=2)
		formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')
		handler.setFormatter(formatter)
		logger.addHandler(handler)
		return logger

	def loadConfig(self):
		pyec2_conf = ['%s/.pyec2' % HOME, '/etc/pyec2.cfg', 'pyec2.cfg.sample']
		for pyec2 in pyec2_conf:
			try:
				with open(pyec2) as f:
					parser = SafeConfigParser()
					parser.read(pyec2)

					conf = dict()

					conf['pyec2'] = dict()
					conf['pyec2']['key_dir'] = parser.get('pyec2', 'key_dir')
					conf['pyec2']['key_extension'] = parser.get('pyec2', 'key_extension')
					conf['pyec2']['log_level'] = parser.get('pyec2', 'log_level')
					conf['pyec2']['add_to_known_hosts'] = parser.getboolean('pyec2', 'add_to_known_hosts')
					conf['pyec2']['prepend_file'] = parser.get('pyec2', 'prepend_file')

					conf['aws'] = dict()
					conf['aws']['usernames'] = parser.get('aws', 'usernames').split(',')
					conf['aws']['aws_access_key_id'] = parser.get('aws', 'aws_access_key_id')
					conf['aws']['aws_secret_access_key'] = parser.get('aws', 'aws_secret_access_key')
					conf['aws']['ec2_region'] = parser.get('aws', 'ec2_region')
					conf['aws']['name_tag'] = parser.get('aws', 'name_tag')

					return conf
			except IOError, e:
				print e
			except NoSectionError, e:
				print 'It seems that something is wrong with your configuration, please create a new one now.'
				self.newConfig()
		return None

	def promptChoice(self, message, short=True, long=False):
		result = raw_input(message).lower()
		if short and result == 'y':
			return 'True'
		elif short and result == 'n':
			return 'False'
		elif long and result == 'yes':
			return 'True'
		elif long and result == 'no':
			return 'False'
		else:
			if short:
				return self.promptChoice('Please respond with either y or n\n' + message, short=short, long=long)
			else:
				return self.promptChoice('Please respond with either yes or no\n' + message, short=short, long=long)

	def promptUser(self):
		result = dict()
		result['pyec2'] = dict()
		result['pyec2']['key_dir'] = raw_input('Key file directory: ')
		result['pyec2']['key_extension'] = raw_input('Key file extension (E.g. pem): ')
		result['pyec2']['log_level'] = raw_input('Log level (E.g. info, debug, warning, error): ')
		result['pyec2']['add_to_known_hosts'] = self.promptChoice('Do you want PyEC2 to add the instances to known hosts automatically? (y/n): ')
		result['pyec2']['prepend_file'] = raw_input('Do you have a .prepend file you would like to prependto the ssh config?\n(Use this to persist personal options, the lines will be added before any hosts in the config file. Use the absolute path to the file):')
		result['aws'] = dict()
		result['aws']['usernames'] = raw_input('Possible usernames (Delimit by comma, no spaces. Put the most used one first): ')
		result['aws']['aws_access_key_id'] = raw_input('AWS Access key ID: ')
		result['aws']['aws_secret_access_key'] = raw_input('AWS Secret access key: ')
		result['aws']['ec2_region'] = raw_input('EC2 region (E.g. eu-west-1/us-east-2): ')
		result['aws']['name_tag'] = raw_input('EC2 name tag (E.g. Name - NB: This is case sensitive!): ')
		return result

	def newConfig(self):
		pyec2_conf = ['%s/.pyec2' % HOME, 'pyec2.conf']
		for pyec2 in pyec2_conf:
			try:
				with open(pyec2, 'wb') as conf:
					values = self.promptUser()
					parser = SafeConfigParser()

					parser.add_section('pyec2')
					for section, v in values.items():
						if section is 'pyec2':
							for option, value in v.items():
								parser.set(section, option, value)

					parser.add_section('aws')
					for section, v in values.items():
						if section is 'aws':
							for option, value in v.items():
								parser.set(section, option, value)

					parser.write(conf)
				break
			except IOError, e:
				print e
		return None


class NullDevice():

	"""Used to take over stdout or stderr to shut up Fabric
	"""

	def write(self, s):
		pass

if __name__ == '__main__':
	print 'This module is not supposed to be used by itself.\nPlease refer to PyEC2.'
