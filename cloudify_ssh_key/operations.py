######
# Copyright (c) 2016 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

from . import get_desired_value

import os
import tempfile
from Crypto.PublicKey import RSA

from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError
from cloudify import ctx, manager
from cloudify_rest_client.exceptions import CloudifyClientError

OPENSSH_FORMAT_STRING = 'OpenSSH'
PRIVATE_KEY_EXPORT_TYPE = 'PEM'
ALGORITHM = 'RSA'


@operation
def create(**_):

    config = get_desired_value(
        'resource_config', _,
        ctx.instance.runtime_properties,
        ctx.node.properties)

    private_key_path = config.get('private_key_path')
    public_key_path = config.get('public_key_path')
    openssh_format = config.get('openssh_format', True)
    algorithm = config.get('algorithm')
    bits = config.get('bits')
    use_secret_store = config.get('use_secret_store') \
        or ctx.node.properties.get('use_secret_store')
    key_name = config.get('key_name') \
        or '{0}-{1}'.format(ctx.deployment.id, ctx.instance.id)

    if config.get('comment'):
        ctx.logger.error('Property "comment" not implemented.')
    if config.get('passphrase'):
        ctx.logger.error('Property "passphrase" not implemented.')
    if config.get('unvalidated'):
        ctx.logger.error('Property "unvalidated" not implemented.')

    # openssh_format is of type boolean
    if not openssh_format:
        raise NonRecoverableError('Only OpenSSH format is supported')

    if algorithm != ALGORITHM:
        raise NonRecoverableError('Only RSA algorithm is supported')

    key_object = RSA.generate(bits)
    private_key_export = key_object.exportKey(PRIVATE_KEY_EXPORT_TYPE)
    pubkey = key_object.publickey()
    public_key_export = pubkey.exportKey(OPENSSH_FORMAT_STRING)

    if use_secret_store:
        _create_secret(key_name, private_key_export)
    else:
        if not private_key_path:
            raise NonRecoverableError(
                'Must provide private_key_path when use_secret_store is false')

        _write_key_file(private_key_path,
                        private_key_export,
                        _private_key_permissions=True)

    if public_key_path:
        _write_key_file(public_key_path, public_key_export)

    return


@operation
def delete(**_):

    config = get_desired_value(
        'resource_config', _,
        ctx.instance.runtime_properties,
        ctx.node.properties)

    private_key_path = config.get('private_key_path')
    public_key_path = config.get('public_key_path')
    use_secret_store = config.get('use_secret_store') \
        or ctx.node.properties.get('use_secret_store')
    key_name = config.get('key_name') \
        or '{0}-{1}'.format(ctx.deployment.id, ctx.instance.id)

    if use_secret_store:
        if _get_secret(key_name):
            _delete_secret(key_name)
    else:
        _remove_path(private_key_path)

    _remove_path(public_key_path)

    return


def _create_secret(key, value):

    try:
        client = manager.get_rest_client()
        client.secrets.create(key, value)
    except CloudifyClientError as e:
        raise NonRecoverableError(str(e))


def _get_secret(key):

    try:
        client = manager.get_rest_client()
        return client.secrets.get(key)
    except CloudifyClientError as e:
        raise NonRecoverableError(str(e))


def _delete_secret(key):

    try:
        client = manager.get_rest_client()
        client.secrets.delete(key)
    except CloudifyClientError as e:
        raise NonRecoverableError(str(e))


def _write_key_file(_key_file_path,
                    _key_file_material,
                    _private_key_permissions=False):

    temporary_file = \
        tempfile.NamedTemporaryFile(delete=False)

    expanded_key_path = os.path.expanduser(_key_file_path)
    with open(temporary_file.name, 'w') as outfile:
        outfile.write(_key_file_material)
    try:
        directory = os.path.dirname(expanded_key_path)
        if not os.path.exists(directory):
            os.makedirs(directory)
        os.rename(temporary_file.name,
                  expanded_key_path)
    except OSError as e:
        raise NonRecoverableError(str(e))

    if _private_key_permissions:
        os.chmod(os.path.expanduser(_key_file_path), 0600)

    return


def _remove_path(key_path):

    try:
        os.remove(os.path.expanduser(key_path))
    except OSError as e:
        raise NonRecoverableError(str(e))
