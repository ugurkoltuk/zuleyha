import json
import argparse
import os 
import sched
import time
import sys
import subprocess
import click
from flask import Flask, request, session, g, redirect, url_for, \
						abort, render_template, flash

app = Flask(__name__) 
app.config.from_object(__name__) 

# Load default config and override config from an environment variable
app.config.update(dict(
		SLAVES_FILE=os.path.join(app.root_path, 'slaves.json'),
		SECRET_KEY='SACMASAPAN'))
app.config.from_envvar('FLASKR_SETTINGS', silent=True)

def read_slave_list(slave_db):
	with open(slave_db) as slave_db_file:
		slaves = json.load(slave_db_file)
		return slaves["slave_list"]

def add_slave_to_list(slave_db, slave):
	with open(slave_db, 'a+') as slave_db_file:
		slave_db_file.seek(0)
		try: 
			slaves = json.load(slave_db_file)
		except:
			slaves = { "slave_list" : [] } 
		if slave not in slaves["slave_list"]:
			slaves["slave_list"].append(slave)
		slave_db_file.seek(0)
		slave_db_file.truncate()
		json.dump(slaves, slave_db_file, sort_keys=True, indent=4, separators=(',', ': '))
		slave_db_file.truncate()

def get_host_status():
	all_hosts = []

	if not os.path.exists(app.config['SLAVES_FILE']):
		return "Cannot find the slave database file %s" % app.config['SLAVES_FILE']

	slaves_list=read_slave_list(app.config['SLAVES_FILE'])

	max_processes=5

	for slave in slaves_list:
		slave_connection_string = "{0}@{1}".format(slave["username"], slave["hostname"])
		get_top_processes = "ps -eo pid,%cpu,%mem,vsz,ni,time,uname,comm --sort -%cpu | head -n {0}".format(max_processes + 1) 
		get_system_load = "cat /proc/loadavg | awk '{print $1}' | sed 's/,$//'"
		get_processor_count = "cat /proc/cpuinfo | grep ^processor | wc -l"

		p = subprocess.Popen(["ssh", slave_connection_string, get_top_processes], stdout=subprocess.PIPE)
		stdout,stderr = p.communicate()
		if p.returncode != 0: 
			continue
		top_processes = stdout.decode("unicode_escape").splitlines()
		
		p = subprocess.Popen(["ssh", slave_connection_string, get_system_load], stdout=subprocess.PIPE)
		stdout,stderr = p.communicate()
		if p.returncode != 0: 
			continue
		system_load = stdout.decode("unicode_escape")

		p = subprocess.Popen(["ssh", slave_connection_string, get_processor_count], stdout=subprocess.PIPE)
		stdout,stderr = p.communicate()
		if p.returncode != 0: 
			continue
		processor_count = stdout.decode("unicode_escape")
		
		all_hosts.append( { "hostname" : "%s" % slave["hostname"],
							#TODO: Fix according to LOCALE
							"load" : "%s" % system_load.replace(',', '.'),
							"process_table" : [[field for field in line.split()] for line in top_processes],
							"processor_count" : "%s" % processor_count
						 } )
	return all_hosts


@app.route('/main-container')
def show_main_container():
	return render_template('main_container.html', all_hosts=get_host_status())

@app.route('/')
def show_load():	
	return render_template('show_load.html', all_hosts=get_host_status())



@app.cli.command()
@click.option('--hostname')
@click.option('--username')
def register(hostname, username):
	if hostname is None or username is None:
		return
	add_authorized_key = "mkdir -p .ssh && cat >> .ssh/authorized_keys"
		
	with open(os.path.expanduser("~/.ssh/id_rsa.pub")) as ssh_pub_file:
		p = subprocess.Popen(["ssh", "{0}@{1}".format(username, hostname), add_authorized_key], stdin=ssh_pub_file)
		result = p.wait() #catch return code

	print ("Result is %d" % int(result))	
	if int(result) != 0:
		sys.exit(result)

	add_slave_to_list(app.config['SLAVES_FILE'], {"username" : "%s" % username, "hostname" : "%s" % hostname})
