from collections import defaultdict
import functools
import logging
import tempfile
import contextlib

from . import log_utils

LOGGER = logging.getLogger(__name__)
LogTask = functools.partial(log_utils.LogTask, logger=LOGGER)


class LagoAnsible(object):
    """
    A class for handling Ansible related tasks

    Attributes:
        prefix (lago.prefix.Prefix): The prefix that this object wraps
    """

    def __init__(self, prefix):
        """
        Args:
            prefix (lago.prefix.Prefix): A prefix to wrap
        """
        self.prefix = prefix

    def get_inventory_str(self, keys=None):
        """
        Convert a dict generated by ansible.LagoAnsible.get_inventory
        to an INI-like file.

        Args:
            keys (list of str): Path to the keys that will be used to
                create groups.

        Returns:
            str: INI-like Ansible inventory
        """
        inventory = self.get_inventory(keys)
        lines = []
        for name, hosts in inventory.viewitems():
            lines.append('[{name}]'.format(name=name))
            for host in sorted(hosts):
                lines.append(host)

        return '\n'.join(lines)

    def get_inventory(self, keys=None):
        """
        Create an Ansible inventory based on python dicts and lists.
        The returned value is a dict in which every key represents a group
        and every value is a list of entries for that group.

        Args:
            keys (list of str): Path to the keys that will be used to
                create groups.

        Returns:
            dict: dict based Ansible inventory
        """
        inventory = defaultdict(list)
        keys = keys or ['vm-type', 'groups', 'vm-provider']
        vms = self.prefix.get_vms().values()

        for vm in vms:
            entry = self._generate_entry(vm)
            vm_spec = vm.spec
            for key in keys:
                value = self.get_key(key, vm_spec)
                if value is None:
                    continue
                if isinstance(value, list):
                    for sub_value in value:
                        inventory['{}={}'.format(key, sub_value)].append(entry)
                else:
                    inventory['{}={}'.format(key, value)].append(entry)

        return inventory

    def _generate_entry(self, vm):
        """
        Generate host entry for the given VM
        Args:
            vm (lago.plugins.vm.VMPlugin): The VM for which the entry
                should be created for.

        Returns:
            str: An entry for vm
        """
        return \
            '{name} ' \
            'ansible_host={ip} ' \
            'ansible_ssh_private_key_file={key}'.format(
                name=vm.name(),
                ip=vm.ip(),
                key=self.prefix.paths.ssh_id_rsa()
            )

    @staticmethod
    def get_key(key, data_structure):
        """
        Helper method for extracting values from a nested data structure.

        Args:
            key (str): The path to the vales (a series of keys and indexes
                separated by '/')
            data_structure (dict or list): The data structure from which the
                value will be extracted.

        Returns:
            str: The values associated with key
        """
        if key == '/':
            return data_structure

        path = key.split('/')
        # If the path start with '/', remove the empty string from the list
        path[0] or path.pop(0)
        current_value = data_structure
        while path:
            current_key = path.pop(0)
            try:
                current_key = int(current_key)
            except ValueError:
                pass

            try:
                current_value = current_value[current_key]
            except (KeyError, IndexError):
                LOGGER.debug('failed to extract path {}'.format(key))
                return None

        return current_value

    @contextlib.contextmanager
    def get_inventory_temp_file(self, keys=None):
        """
        Context manager which returns the inventory written on a tempfile.
        The tempfile will be deleted as soon as this context manger ends.

        Args:
            keys (list of str): Path to the keys that will be used to
                create groups.

        Yields:
            tempfile.NamedTemporaryFile: Temp file containing the inventory
        """
        temp_file = tempfile.NamedTemporaryFile(mode='r+t')
        inventory = self.get_inventory_str(keys)
        LOGGER.debug(
            'Writing inventory to temp file {} \n{}'.
            format(temp_file.name, inventory)
        )
        temp_file.write(inventory)
        temp_file.flush()
        temp_file.seek(0)
        yield temp_file
        temp_file.close()