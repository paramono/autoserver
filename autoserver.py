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
    locals().update(
        {k: v for (k, v) in args.items()}
    )

    # template locations
    te_nginx_conf      = os.path.join(template_dir, 'nginx_proj.conf')
    te_nginx_https     = os.path.join(template_dir, 'nginx_proj_https.conf')
    te_nginx_redirects = os.path.join(template_dir, 'nginx_proj_redirects.conf')
    te_uwsgi_emperor   = os.path.join(template_dir, 'uwsgi_emperor_proj.service')
    te_uwsgi_ini       = os.path.join(template_dir, 'uwsgi_proj.ini')
    te_git_hook        = os.path.join(template_dir, 'post-receive')

    has_domain_and_ip = bool(args['domain'] and args['ip'])

    # create project dir (working dir for repo)
    proj_dir = os.path.join(target_dir, proj)

    if skip_venv:
        print('* * * Skipping virtualenv')
    else:
        # create dir
        target_env_dir = os.path.join(proj_dir, 'env%s' % proj)

        print('* * * Running virtualenv')
        call(['virtualenv', '-p', 'python3', target_env_dir])
        print_hr()


    if not production:
        print("* * * Production mode off, deploying locally")
    else:
        # create conf directory
        if not all((skip_nginx, skip_uwsgi)):
            conf_dir = os.path.join(proj_dir, 'conf')
            os.makedirs(conf_dir, exist_ok=True)

        django_proj_dir = os.path.join(proj_dir, django_proj)
        static_dir      = os.path.join(proj_dir, 'global_static')
        backups_dir     = os.path.join(proj_dir, 'backups')

        os.makedirs(django_proj_dir, exist_ok=True)
        os.makedirs(static_dir,      exist_ok=True)
        os.makedirs(backups_dir,     exist_ok=True)

        # handle nginx
        if skip_nginx:
            print("\n* * * Skipping nginx")
        elif ip and domain: # only if ip and domain present
            print("* * * Creating nginx configs")
            # nginx target directories
            nginx_conf      = os.path.abspath(
                os.path.join(conf_dir, 'nginx_%s.conf' % proj))
            nginx_https     = os.path.abspath(
                os.path.join(conf_dir, 'nginx_%s_https.conf' % proj))
            nginx_redirects = os.path.abspath(
                os.path.join(conf_dir, 'nginx_%s_redirects.conf' % args['proj']))

            # make some locals available for templates
            # (including absolute paths)
            nginx_vars = ['nginx_conf', 'nginx_https', 'nginx_redirects']
            local_vars = locals()
            args.update({k:local_vars[k] for k in nginx_vars})

            # instance the main nginx project config
            instance_template('nginx', te_nginx_conf, nginx_conf, **args)

            # https forcing snippet (commented out)
            copy_template('nginx', te_nginx_https, nginx_https, **args)

            # redirect list snippet (commented out)
            copy_template('nginx', te_nginx_redirects, nginx_redirects, **args)
            print_hr()


        # handle uwsgi
        if skip_uwsgi:
            print('* * * Skipping uwsgi')
        else:
            print("* * * Creating uwsgi configs")
            uwsgi_emperor = os.path.abspath(
                os.path.join(conf_dir, 'uwsgi_emperor_%s.service' % proj))
            uwsgi_ini = os.path.abspath(
                os.path.join(conf_dir, 'uwsgi_%s.ini' % proj))

            instance_template('uwsgi', te_uwsgi_emperor, uwsgi_emperor, **args)
            instance_template('uwsgi', te_uwsgi_ini,     uwsgi_ini,     **args)
            print_hr()


        # create git repo
        if skip_git:
            print('* * * Skipping git repo')
        else:
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
            print_hr()


        if deploy:
            pass



