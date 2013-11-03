import os
import sys
from utils import Utils, NullDevice
from boto import ec2, exception as boto_exception
from fabric.api import env, run, local, hide

HOME = os.environ['HOME']
CONFIG = Utils().loadConfig()

class EC2ssh:

	def __init__(self, possible_user_names, ec2_region, key_dir='%s/.ssh/' % HOME, name_tag='Name', aws_access_key_id=None, aws_secret_access_key=None, key_extension=None, dry_run=False):
		self.usernames = possible_user_names
		self.key_dir = key_dir if key_dir[len(key_dir)-1:] is '/' else '%s/' % key_dir
		self.name_tag = name_tag
		self.conn = ec2.connect_to_region(ec2_region, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
		self.prep = Utils().prepare
		self.indent = Utils().indent
		self.ext = Utils(key_extension=key_extension).keyExt
		self.dry_run = dry_run
		self.log = Utils().log(CONFIG['pyec2']['log_level'])
		self.configdir = '%s/.ssh/' % HOME

	def fetchAllInfo(self):
		if self.dry_run:
			self.log.debug('Commencing dry run')
			instances = [
				{
					'name': 'instance01',
					'ip':	'10.0.0.10',
					'key':	'Falcon_EU.pem',
					'user':	'ubuntu'
				},
				{
					'name': 'instance02',
					'ip':	'10.0.0.20',
					'key':	'Falcon_EU.pem',
					'user':	'root'
				},
				{
					'name': 'instance03',
					'ip':	'10.0.0.30',
					'key':	'Falcon_EU.pem',
					'user':	'root'
				},
				{
					'name': 'instance04',
					'ip':	'10.0.0.40',
					'key':	'Falcon_EU.pem',
					'user':	'ec2-user'
				}
			]
			self.log.debug(instances)
			return instances 
		self.log.debug('Fetching all information on instances')
		result = list()
		try:
			instances = self.conn.get_only_instances()
		except boto_exception.EC2ResponseError, e:
			if e.status == 401:
				self.log.critical('Cannot connect to AWS. Reason: {}'.format(e.reason))
				raise Exception('Cannot connecto to AWS. Reason: {}'.format(e.reason))
			elif e.status == 403:
				self.log.critical('Cannot get instances. You are not authorized to perform this operation.')
				self.log.critical('Please check your AWS credentials.')
				raise Exception('Cannot get instances. You are not authorized to perform this operation.\n\tPlease check your AWS credentials.')
		self.log.info('Found {} instances.'.format(len(instances)))
		count = 0
		for instance in instances:
			if u'running' in instance.state:
				inst = dict()
				inst['name'] = self.prep(instance.tags[self.name_tag])
				inst['ip'] = instance.ip_address
				inst['key'] = self.ext(instance.key_name)
				result.append(inst)
				self.log.debug('Processed {} - {}/{}'.format(inst['name'], count, len(instances)))
				count += 1
		return result

	def establishConnection(self, connection_info):
		self.log.info('Attempting to establish usernames for {}'.format(connection_info['name']))
		self.log.debug('Available usernames:\n{}'.format(self.usernames))
		counter = 1
		for user in self.usernames:
			try:
				self.log.debug('Trying {} on {} - {}/{}'.format(user, connection_info['name'], counter, len(self.usernames)))
				sys.stderr = NullDevice()
				env.abort_on_prompts = True
				env.user = user
				env.host_string = connection_info['ip']
				env.key_filename = '{}{}'.format(self.key_dir, connection_info['key'])
				conn = run('echo Connected to %(host_string)s as %(user)s' % env, quiet=True)
				if conn.succeeded:
					self.log.debug('Connection successful.')
					connection_info['user'] = user
					if CONFIG['pyec2']['add_to_known_hosts']:
						self.addToKnownHosts(connection_info['ip'])
					return connection_info
			except SystemExit:
				self.log.debug('Connection failed.')
				counter += 1
				pass

	def addToKnownHosts(self, ip):
		with hide('stdout', 'stderr'):
			self.log.debug('Writing %s to known_hosts' % ip)
			sys.stderr = NullDevice()
			if not local('ssh-keyscan -H %s >> %s/.ssh/known_hosts.new' % (ip, HOME)).succeeded:
				self.log.warning('Could not write instance to known_hosts')

	def checkForConfig(self):
		try:
			with open(self.configdir + 'config') as config:
				self.log.debug('Existing SSH config file found in {}'.format(self.configdir))
				return True
		except IOError, e:
			if e.errno is 2:
				self.log.info('No config file found in {}' .format(self.configdir))
				return False
			print e

	def finish(self):
		try:
			self.log.info('Writing new SSH config')
			prepend_file = CONFIG['pyec2']['prepend_file']
			prepend_lines = None
			if prepend_file is not None:
				with open(prepend_file, 'r') as pf:
					prepend_lines = pf.read()
			with open(self.configdir + 'config.new', 'w+') as f:  # TODO: Write file to .ssh dir
				self.log.debug('Writing to config file')
				if prepend_lines is not None:
					f.writelines(prepend_lines)
					f.write('\n')
				count = 1
				instances = self.fetchAllInfo()
				for instance in instances:
					if not self.dry_run:
						instance = self.establishConnection(instance)
					f.write('Host %s\n' % instance['name'])
					f.write(self.indent('User %s\n' % instance['user']))
					f.write(self.indent('HostName %s\n' % instance['ip']))
					f.write(self.indent('IdentityFile %s%s\n' % (self.key_dir, instance['key'])))
					self.log.debug('Wrote {} - {}/{}'.format(instance['name'], count, len(instances)))
					count += 1
			try:
				self.log.info('Renaming known_hosts to known_hosts.old')
				os.rename('%s/.ssh/known_hosts' % HOME, '%s/.ssh/known_hosts.old' % HOME)
				os.rename('%s/.ssh/known_hosts.new' % HOME, '%s/.ssh/known_hosts' % HOME)
			except OSError, e:
				self.log.critical('Could not rename known_hosts, please do so manually if you have any trouble with PyEC2:\n mv %s/known_hosts %s/known_hosts.old' % (HOME, HOME))
				self.log.error(e)
			try:
				os.rename(self.configdir + 'config', self.configdir + 'config.old')
				os.rename(self.configdir + 'config.new', self.configdir + 'config')
			except OSError, e:
				if self.checkForConfig():
					self.log.error('Could not rename old config file. Proceeding to overwrite.')
			self.log.info('New config file created. Wrote {} hosts.'.format(count))
		except IOError, e:
			self.log.error('Could not write to config file.')
			self.log.error(e)

	def fetchSingleInfo(self, ip=None, name_tag=None):
		if ip is None and name_tag is None:
			self.log.info('Please provide either an IP or a name')


def main():
	import argparse

	parser = argparse.ArgumentParser(description='Generate a SSH config-file from your EC2 instances')
	parser.add_argument('--aws_key', type=str, help='AWS access key', required=False)
	parser.add_argument('--aws_secret', type=str, help='AWS secret key', required=False)
	parser.add_argument('-r', '--ec2_region', type=str, help='EC2 region', required=False)
	parser.add_argument('-u', '--user_names', type=list, help='A list of possible user names to attempt to connect with, list the most used one first', required=False)
	parser.add_argument('-e', '--key_ext', type=str, help='SSH key extension', required=False)
	parser.add_argument('-d', '--key_dir', type=str, help='SSH key directory', required=False)
	parser.add_argument('--dry_run', dest='dry_run', action='store_true', help='Do a dry run, no connections will be made', required=False)
	parser.add_argument('--new_config', dest='new_config', action='store_true', help='Create a new configuration file in your home directory.', required=False)
	parser.set_defaults(new_config=False)
	parser.set_defaults(dry_run=False)

	args = vars(parser.parse_args())

	new_config = args['new_config']
	dry_run = args['dry_run']
	key_ext = args['key_ext']
	key_dir = args['key_dir']
	aws_key = args['aws_key']
	aws_secret = args['aws_secret']
	ec2_region = args['ec2_region']
	possible_user_names = args['user_names']

	if new_config:
		if Utils().newConfig():
			print 'Configuration file created, you can now proceed to use PyEC2'
	else:
		if CONFIG is not None:
			app = EC2ssh(
						CONFIG['aws']['usernames'],
						CONFIG['aws']['ec2_region'],
						key_dir=CONFIG['pyec2']['key_dir'],
						name_tag=CONFIG['aws']['name_tag'],
						aws_access_key_id=CONFIG['aws']['aws_access_key_id'],
						aws_secret_access_key=CONFIG['aws']['aws_secret_access_key'],
						key_extension=CONFIG['pyec2']['key_extension'],
						dry_run=dry_run
						)
			app.finish()
		else:
			if (not dry_run) and (aws_key is None or aws_secret is None):
				files_not_found = list()
				boto_config = ['/etc/boto.cfg', '%s/.boto' % HOME]
				for boto in boto_config:
					try:
						with open(boto) as f:
							boto = f.read().splitlines()
							aws_key = boto[1]
							aws_secret = boto[2]
					except IOError, e:
						files_not_found.append(str(e))

				Utils().printExceptions(files_not_found)


if __name__ == '__main__':
	main()
