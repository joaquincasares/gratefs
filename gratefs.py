#!/usr/bin/env python

import ConfigParser
import logging
import os
import shlex
import subprocess
import sys
import tempfile
import time


##########################
# Configuration access

configfile = os.path.join(os.path.dirname(__file__), 'gratefs.conf')
config = ConfigParser.RawConfigParser()
config.read(configfile)
if not config.has_section('GrateFS'):
    config.add_section('GrateFS')

def set_config(section, variable, value):
    config.set(section, variable, value)
    with open(configfile, 'wb') as configtext:
        config.write(configtext)

def get_config(section, variable):
    return config.get(section, variable)

if not config.has_option('GrateFS', 'dse_path'):
    set_config('GrateFS', 'dse_path', '/usr/bin/dse')

##########################

##########################
# Logging options

if not config.has_option('GrateFS', 'log'):
    set_config('GrateFS', 'log', 'CRITICAL')

if get_config('GrateFS', 'log') == 'CRITICAL':
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.CRITICAL)
if get_config('GrateFS', 'log') == 'INFO':
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
if get_config('GrateFS', 'log') == 'DEBUG':
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)

##########################

##########################
# Process code

def exe_process_handling(process):
    stdout, stderr = process.communicate()

    if stdout:
        logging.debug('stdout:\n{0}'.format(stdout))
    if stderr:
        logging.error('{0}'.format(stderr))

    return stdout, stderr

def exe(command):
    logging.info('executing: {0}'.format(command))
    try:
        process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        old_path = get_config('GrateFS', 'dse_path')
        print '"{0}" not found. Please update the path to `dse`.'.format(old_path)
        new_path = raw_input('Path to `dse`: ')
        set_config('GrateFS', 'dse_path', new_path)
        return exe(command.replace(old_path, new_path))
    return exe_process_handling(process)

##########################

##########################
# Helper functions

def leading_directory(possible_filename_list):
    if type(possible_filename_list) is list:
        filename_list = possible_filename_list
        new_array = []
        for filename in filename_list:
            new_array.append(filename if (filename[0] == '/') else (os.path.join(get_pwd(), filename)))
        return " ".join(new_array)
    else:
        filename = possible_filename_list
        return filename if (filename[0] == '/') else (os.path.join(get_pwd(), filename))

def trailing_filename(dst, local_src_list):
    if len(local_src_list) == 1 and dst[-1] == '/':
        return os.path.join(dst, local_src_list[0])
    elif dst[-1] == '.':
        return dst[:-1]
    else:
        return dst

def get_connection():
    if config.has_option('GrateFS', 'remote') and get_config('GrateFS', 'remote'):
        return '{0} hadoop fs -Dfs.default.name="cfs://{1}/"'.format(get_config('GrateFS', 'dse_path'), get_config('GrateFS', 'remote'))
    return '{0} hadoop fs'.format(get_config('GrateFS', 'dse_path'))

def get_pwd():
    return get_config('GrateFS', 'pwd') if config.has_option('GrateFS', 'pwd') else '/'

##########################

##########################
# Pipe code

def open_pipe(dst):
    exe('{0} -mkdir {1}'.format(get_connection(), dst))

    stdout = ''
    stderr = ''
    file_index = -1
    while True:
        try:
            chunk = sys.stdin.read(8192)
            time.sleep(0.1) # Allows the KeyboardInterrupt to be caught, otherwise it's lost in os.system()
            if len(chunk) != 0:
                file_index += 1
                chunk_file = 'part-{0}'.format(str(file_index).zfill(10))
                chunk_dst = os.path.join(dst, chunk_file)

                with tempfile.NamedTemporaryFile() as tmp_file:
                    tmp_file.write(chunk)
                    tmp_file.flush()
                    stdpipe = exe('{0} -put {1} {2}'.format(get_connection(), tmp_file.name, chunk_dst))

                    if stdpipe[0]:
                        stdout += 'pipe: {0}:\n{1}\n\n'.format(chunk_dst,stdpipe[0])
                    if stdpipe[1]:
                        stderr += 'pipe: {0}:\n{1}\n\n'.format(chunk_dst,stdpipe[1])
        except KeyboardInterrupt:
            break
    return stdout, stderr

def closed_pipe(dst):
    with tempfile.NamedTemporaryFile() as tmp_file:
        tmp_file.write(sys.stdin.read())
        tmp_file.flush()
        return exe('{0} -put {1} {2}'.format(get_connection(), tmp_file.name, dst))

##########################


# File access
def put(local_src_list, dst):
    dst = leading_directory(dst)
    dst = trailing_filename(dst, local_src_list)
    return exe('{0} -put {1} {2}'.format(get_connection(), " ".join(local_src_list), dst))

def get(src, local_dst):
    src = leading_directory(src)
    return exe('{0} -get {1} {2}'.format(get_connection(), src, local_dst))

def delete(src_list):
    src_list = leading_directory(src_list)
    return exe('{0} -rm {1}'.format(get_connection(), src_list))


# Inspection
def ls(dst_list):
    dst_list = leading_directory(dst_list) if len(dst_list) else get_pwd()
    return exe('{0} -ls {1}'.format(get_connection(), dst_list))

def exists(src_list):
    src_list = leading_directory(src_list)
    stdout, stderr = exe('{0} -ls {1}'.format(get_connection(), src_list))
    return len(stderr) == 0

def cat(src_list):
    src_list = leading_directory(src_list)
    return exe('{0} -cat {1}'.format(get_connection(), src_list))

def tail(src_list):
    stdout = ''
    stderr = ''
    for src in src_list:
        src = leading_directory(src)
        stdpipe = exe('{0} -tail {1}'.format(get_connection(), src))
        if stdpipe[0]:
            stdout += 'tail: {0}:\n{1}\n\n'.format(src,stdpipe[0])
        if stdpipe[1]:
            stderr += 'tail: {0}:\n{1}\n\n'.format(src,stdpipe[1])
    return stdout, stderr


# Movement
def mkdir(dst):
    dst = leading_directory(dst)
    return exe('{0} -mkdir {1}'.format(get_connection(), dst))

def rmdir(dst):
    dst = leading_directory(dst)
    return exe('{0} -rmr {1}'.format(get_connection(), dst))

def cd(dst):
    dst = leading_directory(dst) if len(dst) else '/'
    if exists(dst):
        set_config('GrateFS', 'pwd', os.path.normpath(dst))
        return '', ''
    return '', 'cd: {0}: No such file or directory\n'.format(dst)

def pwd():
    return get_pwd(), ''


# Remote access
def remote(host, port):
    set_config('GrateFS', 'remote', '{0}:{1}'.format(host, port))

def local():
    set_config('GrateFS', 'remote', '')


# Pipe access
def pipe(dst):
    dst = leading_directory(dst)
    return closed_pipe(dst)

def openpipe(dst):
    dst = leading_directory(dst)
    return open_pipe(dst)

def merge(dst, local_dst):
    dst = leading_directory(dst)
    if os.path.exists(local_dst) and raw_input('Do you wish to overwrite {0}? [y/N] '.format(local_dst)) != 'y':
        sys.stderr.write('File not overwritten!\n')
        sys.exit(1)

    stdout, stderr = exe('dse hadoop fs -cat {0}/*'.format(dst))
    open(local_dst, 'wb').write(stdout)
    return '', stderr
