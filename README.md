# PyEC2

PyEC2 was written to help me keep track of our EC2 instances.
It writes a SSH config file with the names of the instances, their IPs and key files.

Usage:

	--aws_key  # AWS access key
	--aws_secret  # AWS secret key
	-r, --ec2_region  # EC2 region
	-u, --user_names  # A list of possible user names to attempt to connect with, list the most used one first
	-e, --key_ext  # SSH key extension
	-d, --key_dir  # SSH key directory
	--dry_run  # Do a dry run, no connections will be made
	--new_config  # Create a new configuration file in your home directory.

Log levels:

	debug
	info
	error
	warning
	critical