from string import Template
from shutil import copyfile

from util.validators import is_writable

def instance_template(service_name, temp_path, dest_path, overwrite=False, **kwargs):
    if is_writable(dest_path, overwrite):
        # open original template
        with open(temp_path, 'r') as temp_file:
            temp   = Template(temp_file.read())
            output = temp.substitute(**kwargs)

        # create a template instance
        with open(dest_path, 'w') as dest_file:
            # print('%s: writing [%s]' % (service_name, dest_path))
            dest_file.write(output)


def copy_template(service_name, temp_path, dest_path, overwrite=False, **kwargs):
    if is_writable(dest_path, overwrite):
        # print('%s: writing [%s]' % (service_name, dest_path))
        copyfile(temp_path, dest_path)
