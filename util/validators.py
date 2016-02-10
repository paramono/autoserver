import argparse
import ipaddress

import os
import re


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
        print('Creating [%s]' % path)
        return True
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
