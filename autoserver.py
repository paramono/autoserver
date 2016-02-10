#!/usr/bin/env python3

import sys, os, re
import argparse
import ipaddress

from string import Template
from shutil import copyfile
from subprocess import call

def print_hr(length=12, end='\n'):
    print('* ' * length + end)

def is_valid_ip(arg):
    try:
        ip = ipaddress.ip_address(arg)
        return arg
    except ValueError:
        raise argparse.ArgumentTypeError("Invalid IP address: %s" % arg)


def is_valid_path(arg):
    if not os.path.exists(arg):
        raise argparse.ArgumentTypeError("path %s does not exist!" % arg)
    else:
        return os.path.abspath(arg)


def is_writable(path, overwrite):
    if not os.path.exists(path):
        return True
    else:
        if overwrite:
            print('path [%s] exists, overwriting' % path)
        else:
            print('path [%s] exists, skipping' % path)
        return overwrite


def is_valid_hostname(arg):
    if len(arg) > 255:
        raise argparse.ArgumentTypeError("arg %s is longer than 255 symbols!" % arg)
    if arg[-1] == ".":
        arg = arg[:-1] # strip exactly one dot from the right, if present
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    # a = [(x, allowed.match(x)) for x in arg.split(".")]
    if all(allowed.match(x) for x in arg.split(".")):
        return arg
    else:
        raise argparse.ArgumentTypeError("Invalid domain name: %s" % arg)


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
        help='project name',
        required=True
        )
    parser.add_argument('-a', '--app', 
        type=str, 
        help='application name',
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

    # boolean switches
    parser.add_argument('--skip-nginx', action='store_true')
    parser.add_argument('--skip-uwsgi', action='store_true')
    parser.add_argument('--skip-git',   action='store_true')
    parser.add_argument('--skip-venv',  action='store_true')
    parser.add_argument('-w', '--overwrite', action='store_true')

    args = vars(parser.parse_args())

    glob_vars = [
        'target_dir',
        'skip_nginx', 
        'skip_uwsgi',
        'skip_git',
        'skip_venv',
        'overwrite',
        'ip',
        'domain',
        'proj',
    ]

    locals().update(
        {k: v for (k, v) in args.items() if k in glob_vars}
    )

    # template locations
    te_nginx_filename  = os.path.join(template_dir, 'nginx_proj.conf')
    te_nginx_https     = os.path.join(template_dir, 'nginx_https.conf')
    te_nginx_redirects = os.path.join(template_dir, 'nginx_redirects.conf')
    te_uwsgi_emperor   = os.path.join(template_dir, 'uwsgi_emperor_proj.service')
    te_uwsgi_proj      = os.path.join(template_dir, 'uwsgi_proj.ini')

    has_domain_and_ip = bool(args['domain'] and args['ip'])

    if not all((skip_nginx, skip_uwsgi)):
        target_conf_dir = os.path.join(target_dir, proj, 'conf')
        os.makedirs(target_conf_dir, exist_ok=True)

    if skip_nginx:
        print("* * * Skipping nginx")
    elif ip and domain: # only if ip and domain present
        print("* * * Creating nginx configs")
        # nginx target directories
        nginx_filename  = os.path.abspath(
            os.path.join(target_conf_dir, '%s_conf.nginx' % args['proj']))
        nginx_https     = os.path.abspath(
            os.path.join(target_conf_dir, '%s_https.nginx' % args['proj']))
        nginx_redirects = os.path.abspath(
            os.path.join(target_conf_dir, '%s_redirects.nginx' % args['proj']))

        nginx_vars = ['nginx_filename', 'nginx_https', 'nginx_redirects']
        local_vars = locals()
        args.update({k:local_vars[k] for k in nginx_vars})

        if is_writable(nginx_filename, overwrite):
            # open original template
            with open(te_nginx_filename, 'r') as te_nginx_file:
                nginx_template = Template(te_nginx_file.read())
                nginx_str = nginx_template.substitute(**args)

            # write a config from a "rendered" template
            with open(nginx_filename, 'w') as nginx_file:
                print('nginx: writing [%s]' % nginx_filename)
                nginx_file.write(nginx_str)

        # https forcing snippet (commented out)
        if is_writable(nginx_https, overwrite):
            print('nginx: writing [%s]' % nginx_https)
            copyfile(te_nginx_https, nginx_https)

        # redirect list snippet (commented out)
        if is_writable(nginx_redirects, overwrite):
            print('nginx: writing [%s]' % nginx_redirects)
            copyfile(te_nginx_redirects, nginx_redirects)

        print_hr()


    if skip_uwsgi:
        print('* * * Skipping uwsgi')
    else:
        pass


    if skip_venv:
        print('* * * Skipping virtualenv')
    else:
        # create dir
        target_env_dir = os.path.join(target_dir, proj, 'env{proj}'.format(proj=proj))

        print('\n* * * Running virtualenv')
        call(['virtualenv', '-p', 'python3', target_env_dir])
        print_hr()

