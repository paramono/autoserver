#!/usr/bin/env python3

import sys
import os
import argparse

from subprocess import call
from getpass import getuser

from util.validators import (
        is_writable, 
        is_valid_ip, 
        is_valid_hostname, 
        is_valid_path
        )
from util.template_helpers import instance_template, copy_template


def print_hr(length=40, end='\n'):
    print('-' * length + end)


def setup_nginx(**kwargs):
    # handle nginx
    locals().update(kwargs)

    if skip_nginx:
        print("\n* * * Skipping nginx")
        return

    if ip and domain: # only if ip and domain present
        print("* * * Creating nginx configs")

        # make some locals available for templates
        # (including absolute paths)
        # required for template rendering 

        # instance the main nginx project config
        instance_template('nginx', te_nginx_conf, nginx_conf, **kwargs)

        # https forcing snippet (commented out)
        copy_template('nginx', te_nginx_https, nginx_https, **kwargs)

        # redirect list snippet (commented out)
        copy_template('nginx', te_nginx_redirects, nginx_redirects, **kwargs)
        print_hr()


# handle uwsgi
def setup_uwsgi(**kwargs):
    locals().update(kwargs)

    if skip_uwsgi:
        print('* * * Skipping uwsgi')
        return

    print("* * * Creating uwsgi configs")

    instance_template('uwsgi', te_uwsgi_emperor, uwsgi_emperor, **kwargs)
    instance_template('uwsgi', te_uwsgi_ini,     uwsgi_ini,     **kwargs)
    print_hr()

# create git repo
def setup_git(**kwargs):
    locals().update(kwargs)

    if skip_git:
        print('* * * Skipping git repo')
        return

    repo_dir = os.path.join(proj_dir, 'repo.git')
    if not os.path.exists(repo_dir) or force_reinit_git:
        print('* * * Creating git bare repo')
        call(['git', 'init', '--bare', repo_dir])
        repo_hooks = os.path.join(repo_dir, 'hooks')

        git_hook = os.path.abspath(
            os.path.join(repo_hooks, 'post-receive'))

        instance_template('git', te_git_hook, git_hook, **args)
        os.chmod(git_hook, 0o755)

        print('\n>>> Run this on your workstation <<<')
        print(
            'git remote add live ssh://{username}@{domain}{repo_dir}'
            .format(username=user, domain=domain, repo_dir=repo_dir)
        )
    else: 
        print('* * * Repo already exists.')
        print('Run with "--force-reinit-git" to reinitialize repo')

    print('\n>>> Run this on your workstation <<<')
    print(
        'git remote add live ssh://{username}@{domain}{repo_dir}'
        .format(username=user, domain=domain, repo_dir=repo_dir)
    )
    print_hr()


def setup_venv(**kwargs):
    # print(locals())
    # locals().update(kwargs)
    # print()
    # print(locals())

    # skip_venv = kwargs['skip_venv']
    locals().update({'skip_venv': True})
    print(locals())


    if skip_venv:
        print('* * * Skipping virtualenv')
        return

    # create dir
    target_env_dir = os.path.join(proj_dir, 'env%s' % proj)

    print('* * * Running virtualenv')
    call(['virtualenv', '-p', 'python3', target_env_dir])

def run_setup(**kwargs):
    # print(locals())
    # locals().update(kwargs)
    # print()
    # print(locals())

    setup_venv(**kwargs)

    if not production:
        print("* * * Production mode off, deploying locally")
    else:

        os.makedirs(django_proj_dir, exist_ok=True)
        os.makedirs(static_dir,      exist_ok=True)
        os.makedirs(backups_dir,     exist_ok=True)

        setup_nginx(**kwargs)
        setup_uwsgi(**kwargs)
        setup_git(**kwargs)


def run_deploy(**kwargs):
    euid = os.geteuid()
    if euid != 0:
        print ("Script not started as root. Running sudo..")
        args = ['sudo', sys.executable] + sys.argv + [os.environ]
        # the next line replaces the currently-running process with the sudo
        os.execlpe('sudo', *args)
        return

    if not skip_nginx:
        link = '/etc/nginx/sites-enabled/%s' % os.path.basename(nginx_conf)
        if not os.path.islink(link):
            os.symlink(nginx_conf, link)
        else:
            if overwrite:
                os.unlink(link)
                os.symlink(nginx_conf, link)

    if not skip_uwsgi:
        link = '/etc/systemd/system/%s' % os.path.basename(uwsgi_emperor)
        if not os.path.islink(link):
            os.symlink(uwsgi_emperor, link)
        else:
            if overwrite:
                os.unlink(link)
                os.symlink(uwsgi_emperor, link)


if __name__ == '__main__':
    try:
        script_path = os.readlink(__file__)
    except OSError:
        script_path = os.path.abspath(__file__)
    finally:
        script_dir = os.path.abspath(
            os.path.dirname(script_path)
        )

    template_dir = os.path.join(script_dir, 'templates')

    parser = argparse.ArgumentParser(
        description="Automatically generate conf files for a server")

    parser.add_argument('mode', metavar='mode', nargs=1)

    parser.add_argument('-t', '--target-dir', 
        type=is_valid_path,  
        help='path to project', 
        # required=True,
        default=os.getcwd()
        )
    parser.add_argument('-p', '--proj', 
        type=str, 
        help='global project name',
        required=True
        )
    parser.add_argument('-j', '--django-proj', 
        type=str, 
        help='django project name',
        required=True
        )
    parser.add_argument('-i', '--ip', 
        type=is_valid_ip, 
        help='server IP address',
        )
    parser.add_argument('-d', '--domain', 
        type=is_valid_hostname, 
        help='Domain name'
        )
    parser.add_argument('-u', '--user', 
        type=str, 
        help='Non root user that has access to project',
        default=getuser(),
        )

    # boolean switches
    parser.add_argument('--skip-nginx', action='store_true')
    parser.add_argument('--skip-uwsgi', action='store_true')
    parser.add_argument('--skip-venv',  action='store_true')
    parser.add_argument('--skip-git',   action='store_true')
    parser.add_argument('--production', action='store_true')
    parser.add_argument('--deploy',     action='store_true')
    parser.add_argument('-w', '--overwrite', action='store_true')
    parser.add_argument('--force-reinit-git', action='store_true')

    args = vars(parser.parse_args())
    args['mode'] = args['mode'][0]
    # locals().update(args)

    # template locations
    templates = {
        'te_nginx_conf': 
            os.path.join(template_dir, 'nginx_proj.conf'),
        'te_nginx_https': 
            os.path.join(template_dir, 'nginx_proj_https.conf'),
        'te_nginx_redirects': 
            os.path.join(template_dir, 'nginx_proj_redirects.conf'),
        'te_uwsgi_emperor':
            os.path.join(template_dir, 'uwsgi.emperor.proj.service'),
        'te_uwsgi_ini': 
            os.path.join(template_dir, 'uwsgi_proj.ini'),
        'te_git_hook': 
            os.path.join(template_dir, 'post-receive'),
        }





    # create project dir (working dir for repo):
    proj_dir = os.path.join(args['target_dir'], args['proj'])
    dirs = {
        'proj_dir'        : proj_dir,
        'django_proj_dir' : os.path.join(proj_dir, args['django_proj']),
        'static_dir'      : os.path.join(proj_dir, 'global_static'),
        'backups_dir'     : os.path.join(proj_dir, 'backups'),
        }
    args.update(templates)
    args.update(dirs)

    # create conf directory
    conf_dir = os.path.join(proj_dir, 'conf')
    args.update({'conf_dir': conf_dir})
    if not all((args['skip_nginx'], args['skip_uwsgi'])):
        os.makedirs(conf_dir, exist_ok=True)

    nginx_conf_basename = 'nginx_%s.conf' % args['proj']

    # nginx target directories
    nginx_conf      = os.path.abspath(
        os.path.join(conf_dir, nginx_conf_basename))
    nginx_https     = os.path.abspath(
        os.path.join(conf_dir, 'nginx_%s_https.conf' % args['proj']))
    nginx_redirects = os.path.abspath(
        os.path.join(conf_dir, 'nginx_%s_redirects.conf' % args['proj']))

    nginx_vars = ['nginx_conf', 'nginx_https', 'nginx_redirects']
    local_vars = locals()
    args.update({k:local_vars[k] for k in nginx_vars})

    uwsgi_emperor = os.path.abspath(
        os.path.join(conf_dir, 'uwsgi.emperor.%s.service' % args['proj']))
    uwsgi_ini = os.path.abspath(
        os.path.join(conf_dir, 'uwsgi_%s.ini' % args['proj']))

    locals().update(args) # FIXME, ugly!

    if 'setup' == mode:
        run_setup(**args)
    elif 'deploy' == mode:
        run_deploy(**args)


