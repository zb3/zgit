import os
import re
import sys
import shutil
import ftplib
import hashlib
import tarfile
import getpass
import fnmatch
import tempfile
import configparser
from zgitignore import ZgitIgnore, normalize_path

local_storage = ''
use_local = True
ftp_host = ''
ftp_path = ''
ftp_user = ''
ftp_pass = ''

project = os.path.relpath('.', '..')
action = 'status'
rev = 0
ignorefile = None


def upload_ftp_file(f, name):
    f.seek(0)
    ftpfile = ftplib.FTP(ftp_host, ftp_user, ftp_pass)
    ftpfile.cwd(ftp_path)
    ftpfile.storbinary('STOR ' + name, f)
    ftpfile.quit()


def download_ftp_file(f, name):
    ftpfile = ftplib.FTP(ftp_host, ftp_user, ftp_pass)
    ftpfile.cwd(ftp_path)
    ftpfile.retrbinary('RETR ' + name, f.write)
    ftpfile.quit()


def ensure_login_info():
    global ftp_pass
    global use_local

    if use_local:
        return None

    if not ftp_pass:
        ftp_pass = getpass.getpass()
        if not ftp_pass:
            use_local = True
            return None


def sane_path_translate(pat):
    if pat.startswith('/'):
        pat = '.' + pat

    i, n = 0, len(pat)
    res = ''
    while i < n:
        c = pat[i]
        i = i + 1
        if c == '*':
            res = res + '.*'
        elif c == '?':
            res = res + '.'
        elif c == '[':
            j = i
            if j < n and pat[j] == '!':
                j = j + 1
            if j < n and pat[j] == ']':
                j = j + 1
            while j < n and pat[j] != ']':
                j = j + 1
            if j >= n:
                res = res + '\\['
            else:
                stuff = pat[i:j].replace('\\', '\\\\')
                i = j + 1
                if stuff[0] == '!':
                    stuff = '^' + stuff[1:]
                elif stuff[0] == '^':
                    stuff = '\\' + stuff
                res = '%s[%s]' % (res, stuff)
        else:
            res = res + re.escape(c)
    return res


def traverse_directory(dir_root='.'):
    for dirpath, dirnames, filenames in os.walk(dir_root, topdown=True):
        dirnames.sort()
        filenames.sort()

        dirnames[:] = [
            d for d in dirnames if not ignorefile.is_ignored(
                os.path.join(
                    dirpath,
                    d),
                True)]
        filenames[:] = [
            f for f in filenames if not ignorefile.is_ignored(
                os.path.join(
                    dirpath,
                    f))]

        itemlist = dirnames + filenames

        for filename in itemlist:
            yield os.path.join(dirpath, filename)


def pack(f):
    targz = tarfile.open(fileobj=f, mode='w:gz')

    for filepath in traverse_directory('.'):
        targz.add(filepath, recursive=False)

    targz.close()


def directory_md5(dir_root='.'):
    hash = hashlib.md5()

    for filepath in traverse_directory('.'):
        hash.update(normalize_path(filepath).encode('ascii'))

        if os.path.isfile(filepath):
            f = open(filepath, 'rb')
            for chunk in iter(lambda: f.read(65536), b''):
                hash.update(chunk)
            f.close()

    return hash.hexdigest()


def unpack(f):
    tf = tarfile.open(fileobj=f)
    tf.extractall('.')
    tf.close()


def upload(f, name):
    ensure_login_info()

    if use_local:
        f.seek(0)
        nf = open(local_storage + os.path.sep + name, 'wb')
        shutil.copyfileobj(f, nf)
        nf.close()
    else:
        upload_ftp_file(f, name)


def download(f, name):
    login_info = ensure_login_info()

    if use_local:
        fsrc = open(local_storage + os.path.sep + name, 'rb')
        shutil.copyfileobj(fsrc, f)
        fsrc.close()
    else:
        download_ftp_file(f, name)


def get_remote_revision():
    global rr
    rr = -1

    try:
        tf = tempfile.TemporaryFile()
        download(tf, project + '.rev')
        tf.seek(0)
        rr = int(tf.read())
        tf.close()

    except:
        pass


def get_remote_sum(r):
    tf = tempfile.TemporaryFile()
    download(tf, project + '-' + str(r) + '.md5')
    tf.seek(0)
    ret = tf.read().decode('ascii')
    tf.close()
    return ret


def check_up_to_date():  # -1 out of date, 0 up to date, 1 unsaved changes
    get_remote_revision()

    current_sum = get_current_sum()

    if rr > rev:
        return -2 if rev and current_sum != get_remote_sum(rev) else -1
    elif rr < rev:
        return 1
    else:
        if not get_remote_sum(rev) == current_sum:
            return 1
        else:
            return 0


def yes():
    really = input()
    return True if len(really) and really.lower()[0] == 'y' else False


def get_current_sum():
    return directory_md5()


def parse_config():
    global local_storage, use_local, ftp_host, ftp_path, ftp_user, ftp_pass, action

    config = configparser.ConfigParser()
    try:
        config.read(os.path.expanduser('~/.zgitconf'))
    except:
        print(
            'Failed to read configuration file. Place a .zgitconf file in your home directory.')
        exit()

    if 'config' in config:
        if 'default_action' in config['config']:
            action = config['config']['default_action']

    if 'local' in config:
        if 'directory' in config['local']:
            local_storage = os.path.expanduser(config['local']['directory'])

    if not local_storage:
        print('Local directory not specified.')
        exit()

    if 'remote' in config and (
            not 'disabled' in config['remote'] or not config['remote']['disabled'] == 'True'):
        if 'host' in config['remote']:
            ftp_host = config['remote']['host']

        if 'path' in config['remote']:
            ftp_path = config['remote']['path']

        if 'user' in config['remote']:
            ftp_user = config['remote']['user']

    if ftp_host and ftp_user:
        use_local = False


def main():
    global action, rev, ignorefile

    parse_config()

    try:
        os.makedirs(local_storage, exist_ok=True)
    except:
        pass

    if not os.path.isdir(local_storage):
        print('Failed to create local storage directory')
        exit()

    if len(sys.argv) > 1:
        action = sys.argv[1]

    print(project + ' => ' + action)

    # try to read .zgitignore, if not present then read .gitignore
    ignorefile = ZgitIgnore()

    try:
        with open('.zgitignore', 'r') as f:
            ignorefile.add_patterns(f.read().splitlines())
    except:
        try:
            with open('.gitignore', 'r') as f:
                ignorefile.add_patterns(f.read().splitlines())
        except:
            pass

    ignorefile.add_patterns(['.zgitrev'])

    if not os.path.isfile('.zgitrev'):
        try:
            with open('.zgitrev', 'w') as f:
                f.write('0')
        except:
            print('Failed to create rev file')
            exit()

    try:
        with open('.zgitrev') as f:
            for line in f:
                rev = int(line)
    except:
        print('Failed to open rev file')
        exit()

    amend = False

    if action == 'amend':
        action = 'push'
        amend = True

    if action == 'push':
        if len(sys.argv) == 3 and sys.argv[2] == 'amend':
            amend = True

        if check_up_to_date() < 0:
            print(
                'You are not up to date. Do you really want to continue? [y/N]')
            if not yes():
                exit()
            rev = rr

        if not amend or not rev:
            rev += 1

        tarname = project + '-' + str(rev) + '.tar.gz'

        tar_handle = tempfile.TemporaryFile()
        pack(tar_handle)
        try:
            upload(tar_handle, tarname)
        except:
            print('Failed to upload file.')
            exit()

        with open('.zgitrev', 'w') as f:
            f.write(str(rev))

        zf = open('.zgitrev', 'rb')
        upload(zf, project + '.rev')
        zf.close()

        tsf = tempfile.TemporaryFile()
        tsf.write(get_current_sum().encode('ascii'))
        upload(tsf, project + '-' + str(rev) + '.md5')
        tsf.close()

        print('New revision is', rev)

    elif action == 'pull':
        status = check_up_to_date()

        if status == 1 or status == -2:
            print('You have unsaved changes' +
                  ('(and an outdated revision)' 
                  if status == -2 else '') +
                  '. Do you really want to continue? [y/N]')
            if not yes():
                exit()

        rv = rr
        if len(sys.argv) == 3:
            rv = int(sys.argv[2])

        tarname = project + '-' + str(rv) + '.tar.gz'
        tf = tempfile.TemporaryFile()
        try:
            download(tf, tarname)
        except:
            print('Failed to download tar file.')
            tf.close()
            exit()

        for f in os.listdir('.'):
            if os.path.isdir(f):
                shutil.rmtree(f)
            else:
                os.remove(f)

        tf.seek(0)
        unpack(tf)

        with open('.zgitrev', 'w') as f:
            f.write(str(rv))

        tf.close()
    elif action == 'status':
        status = check_up_to_date()

        if status < 0:
            print(
                'Out of date!' + (' (and unsaved changes)' if status == -2 else ''))
        elif status == 0:
            print('Up to date!')
        elif status == 1:
            print('Unsaved changes!')

        print('---')
        print('Current revision is: ' + str(rev))
        if rr == -1:
            print('No remote revision found')
        else:
            print('Current remote revision is: ' + str(rr))
