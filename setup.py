#!/usr/bin/env python
from setuptools import setup, find_packages


setup(name='pyec2', 
	description='Generates a new SSH config for you from your EC2 instances.',
	version='0.1.6', 
	author='Kasper Jacobsen',
	author_email='k@three65.org',
	url='https://github.com/Dinoshauer/PyEC2',
	packages=find_packages(),
	entry_points={
		'console_scripts': [
			'pyec2 = pyec2.pyec2:main']
	},
	license='MIT',
	long_description=open('README.rst').read(),
	install_requires=[]
)