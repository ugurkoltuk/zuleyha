import json
import argparse
import os
import sys
import subprocess
import jinja2
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer

slave_db = "slaves.json"
args_parser = argparse.ArgumentParser()

args_parser.add_argument('-r', '--register', dest='slave_info', nargs=2,
			help='Register a new machine to retrieve current status from with a username and hostname or IP address.',
			metavar=('hostname', 'username'))

args = args_parser.parse_args()

def render(template, all_hosts):
	path, filename = os.path.split(template)
	return jinja2.Environment(
		loader=jinja2.FileSystemLoader(path or './')
	).get_template(filename).render(all_hosts=all_hosts)

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

	if not os.path.exists(slave_db):
		print("Cannot find the slave database file %s" % slave_db)
		return []

	slaves_list=read_slave_list(slave_db)

	max_processes=3

	for slave in slaves_list:
		slave_connection_string = "{0}@{1}".format(slave["username"], slave["hostname"])
		get_top_processes = "top -bn1 | tail -n+7 | head -n{0} | grep -v top | head -n{1}".format(max_processes + 2, max_processes + 1)
		get_system_load = "cat /proc/loadavg | awk '{print $1}' | sed 's/,$//'"
		get_processor_count = "cat /proc/cpuinfo | grep ^processor | wc -l"
		get_disk_usage = 'df -P | column -t | grep \'^/dev\' | grep -Ev \'\/boot(\/efi)?$\' | awk \'{print "\\""$6"\\"" " " $5}\' | sed \'s/%//\''

		p = subprocess.Popen(["ping", slave["hostname"], "-c", "1"], stdout=subprocess.PIPE)
		stdout,stderr = p.communicate()
		if p.returncode != 0:
			continue
		ping = stdout.decode("unicode_escape").splitlines()
		if len(ping) < 6: #ping that i know prints 6 lines for -c 1
			continue
		ping,pingunit = ping[-1].split("=")[1].split("/")[1],ping[-1].split()[-1]  #how nice it is that python is dynamically typed

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

		p = subprocess.Popen(["ssh", slave_connection_string, get_disk_usage], stdout=subprocess.PIPE)
		stdout,stderr = p.communicate()
		if p.returncode != 0:
			continue
		disk_usage = stdout.decode("unicode_escape").splitlines()

		hostname = slave["hostname"]
		try:
			dnsname = socket.gethostbyaddr(hostname)[0]
			if hostname != dnsname:
				hostname = "%s(%s)" % (hostname, dnsname)
		except:
			pass

		all_hosts.append( { "hostname" : hostname,
							#TODO: Fix according to LOCALE
							"load" : system_load.replace(',', '.'),
							"process_table" : [[field.replace(',', '.') for field in line.split()] for line in top_processes],
							"processor_count" : processor_count,
							"disk_usage" : [[field.replace(',', '.') for field in line.split()] for line in disk_usage],
							"ping" : ping,
							"pingunit" : pingunit
						 } )
	return all_hosts

def show_main_container():
	return render('main_container.html', all_hosts=get_host_status())

def show_load():
	return render('show_load.html', all_hosts=get_host_status())

class RequestHandler(BaseHTTPRequestHandler):
	def do_GET(self):

		if self.path == '/':
			self.send_response(200)
			self.send_header('Content-type','text/html')
			self.end_headers()
			message = show_load()
		elif self.path.startswith('/main-container'):
			self.send_response(200)
			self.send_header('Content-type','text/html')
			self.end_headers()
			message = show_main_container()
		elif self.path.endswith(".css"):
			with open(self.path[1:]) as cssfile:
				self.send_response(200)
				self.send_header('Content-type', 'text/css')
				self.end_headers()
				message = cssfile.read()
		elif self.path.endswith(".js"):
			with open(self.path[1:]) as jsfile:
				self.send_response(200)
				self.send_header('Content-type', 'application/javascript')
				self.end_headers()
				message = jsfile.read()
		else:
			self.send_response(404)
			return

		self.wfile.write(bytes(message, "utf8"))
		return

def run():
	server = HTTPServer(('0.0.0.0', 8080), RequestHandler)
	print('running server on port 8080')
	server.serve_forever()

def register(hostname, username):
	if hostname is None or username is None:
		return
	add_authorized_key = "mkdir -p .ssh && cat >> .ssh/authorized_keys"
	if not os.path.exists(os.path.expanduser('~/.ssh/id_rsa.pub')):
		os.system('ssh-keygen -t rsa')

	with open(os.path.expanduser("~/.ssh/id_rsa.pub")) as ssh_pub_file:
		p = subprocess.Popen(["ssh", "{0}@{1}".format(username, hostname), add_authorized_key], stdin=ssh_pub_file)
		result = p.wait() #catch return code

	print ("Result is %d" % int(result))
	if int(result) != 0:
		sys.exit(result)

	add_slave_to_list(slave_db, {"username" : "%s" % username, "hostname" : "%s" % hostname})

if __name__ == '__main__':
	if args.slave_info is None:
		run()
	else:
		register(args.slave_info[0], args.slave_info[1])
