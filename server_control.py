#!/usr/bin/python3

from sys import argv, exit
import re
import os
import psutil
import subprocess
import time

# This is a command-line executable for managing factorio servers.

path = os.path.dirname(os.path.abspath(__file__))
factorio_root = '/home/factorio/factorio'
binary_path = factorio_root + '/bin/x64/factorio'
saves_path = factorio_root + '/saves/'
logs_path = factorio_root + '/logs/'
pidfilepath = path + '/factorio_games.pid'
lockfilepath = path + '/server_control.lock'
usage = 'server_control factorio_name <start|status|stop>'

def verify_args():
	# Sanity checks
	command = re.compile(r'start|status|stop')
	if len(argv) != 3 or not command.match(argv[1]):
		exit(usage)
	if '=' in argv[2] or '.' in argv[2] or '_' in argv[2]:
		exit('= and . not permitted in game names.')

# Return name:pid dictionary of all running games.
def get_pids():
	try:
		with open(pidfilepath) as pidfile:
			games = dict([game.strip().split('=') for game in pidfile.readlines()])
	except FileNotFoundError:
		return {} # That's fine. Probably implies first run.
	return games

def start_game(name, latency=300):
	if check_lockfile():
		# First, see if it's already running.
		if get_status(name):
			os.remove(lockfilepath)
			exit(name + ' is already running')
		# No game by that name is running. Go ahead and start it.
		# First thing, prepare a log file to record the output.
		try:
			output_file = open(logs_path + name + '.log', 'w')
		except FileNotFoundError:
			os.mkdir(logs_path)
			output_file = open(logs_path + name + '.log', 'w')
		command = [binary_path, '--start-server', saves_path + name + '.zip', '--latency-ms', str(latency)]
		#print(' '.join(command))
		game = subprocess.Popen(command, stdout=output_file)
		with open(pidfilepath, 'a') as pidfile:
			pidfile.write(name + '=' + str(game.pid) + '\n')
		print('Game {} started with pid {}'.format(name, game.pid))
		os.remove(lockfilepath)
	
# Returns True if a game by that name is running. Else False.
def get_status(name):
	try:
		pid = int(get_pids()[name])
		print('get_status identified pid {} for name {}'.format(pid, name))
	except KeyError:
		print('Game named {} wasn\'t found in pidfile.'.format(name))
		return False
	status = psutil.pid_exists(pid)
	if not status:
		# It's not running, but there's an entry in the games list.
		purge_game_from_pids(name)
		print('Stopped game {} no longer tracked.'.format(name))
	return psutil.pid_exists(pid)

# User interface wrapper for get_status.
def check_status(name):
	if get_status(name):
		print(('Game {} is currently running.').format(name))
	else:
		print(('No game {} is currently running').format(name))
	os.remove(lockfilepath)
	
# Kill the game by sending sigint.
def stop_game(name):
	if check_lockfile():
		# Make sure that we don't have collisions.
		if get_status(name):
			p = psutil.Process(int(get_pids()[name]))
			p.send_signal(2)
			purge_game_from_pids(name)
		else:
			print('Kill command failed. {} wasn\'t running!'.format(name))
	os.remove(lockfilepath)

def purge_game_from_pids(name):
	with open(pidfilepath) as pidfile:
		lines = pidfile.readlines()
	with open(pidfilepath, 'w') as pidfile:
		for line in lines:
			if line.split('=')[0] != name:
				pidfile.write(line)
	
def check_lockfile():
	try:
		os.stat(lockfilepath)
		exit('Conflicting lockfile: ' + lockfilepath)
	except FileNotFoundError:
		with open(lockfilepath, 'a') as lock:
			lock.write(str(time.time()))
			return True

# Return all .zip files in the saves path that don't start with _
def get_available_games():
	saves = os.listdir(saves_path)
	saves = [save[:-4] for save in saves if save.endswith('.zip') and not 
		save.endswith('.tmp.zip') and not	save.startswith('_')]
	return saves

def execute_commands():
	if argv[1] == 'start':
		# Get rid of metacharacters for this system from the name.	
		start_game(argv[2])
	elif argv[1] == 'status':
		check_status(argv[2])
	elif argv[1] == 'stop':
		stop_game(argv[2])
	else:
		os.remove(lockfilepath)
		print(usage)
		exit('Unsupported instruction: ', argv[1])
	
if __name__ == '__main__':
	verify_args()
	execute_commands()
