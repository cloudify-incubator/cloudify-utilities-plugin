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

import os
import tempfile
from Crypto.PublicKey import RSA

from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError
from cloudify import ctx, manager
from cloudify_rest_client.exceptions import CloudifyClientError

OPENSSH_FORMAT = 'OpenSSH'
PRIVATE_KEY_EXPORT_TYPE = 'PEM'
ALGORITHM = 'RSA'


@operation
def create(**_):

    resource_config_property = _.get('resource_config') or ctx.instance\
        .runtime_properties\
        .get('resource_config') or ctx.node.properties\
        .get('resource_config')
    private_key_path = _.get('private_key_path') or ctx.instance\
        .runtime_properties\
        .get('private_key_path') or resource_config_property\
        .get('private_key_path')
    public_key_path = _.get('public_key_path') or ctx.instance\
        .runtime_properties\
        .get('public_key_path') or resource_config_property\
        .get('public_key_path')
    OpenSSH_format = _.get(OPENSSH_FORMAT) or ctx.instance.runtime_properties\
        .get(OPENSSH_FORMAT) or resource_config_property\
        .get(OPENSSH_FORMAT, True)
    algorithm = _.get('algorithm') or ctx.instance.runtime_properties\
        .get('algorithm') or resource_config_property.get('algorithm')
    bits = _.get('bits') or ctx.instance.runtime_properties\
        .get('bits') or resource_config_property\
        .get('bits')
    use_secret_store = _.get('use_secret_store') or ctx.instance\
        .runtime_properties\
        .get('use_secret_store') or ctx.node.properties\
        .get('use_secret_store')
    key_name = _.get('key_name') or ctx.instance.runtime_properties\
        .get('key_name') or ctx.node.properties\
        .get('key_name', '{0}-{1}'.format(ctx.deployment.id,
                                          ctx.instance.id))

    if resource_config_property.get('comment'):
        ctx.logger.error('NotImplementedError: '
                         'Tried to pass comment property.')
    if resource_config_property.get('passphrase'):
        ctx.logger.error('NotImplementedError: '
                         'Tried to pass passphrase property.')
    if resource_config_property.get('unvalidated'):
        ctx.logger.error('NotImplementedError: '
                         'Tried to pass unvalidated property.')

    # OpenSSH_format is of type boolean
    if OpenSSH_format:
        openssh_format_string = OPENSSH_FORMAT
    else:
        raise NonRecoverableError('Only OpenSSH format is supported')

    if algorithm != ALGORITHM:
        raise NonRecoverableError('Only RSA algorithm is supported')

    key_object = RSA.generate(bits)
    private_key_export = key_object.exportKey(PRIVATE_KEY_EXPORT_TYPE)
    pubkey = key_object.publickey()
    public_key_export = pubkey.exportKey(openssh_format_string)

    if use_secret_store:
        _create_secret(key_name, private_key_export)
    else:
        if not private_key_path:
            raise NonRecoverableError('Must provide private_key_path'
                                      ' when use_secret_store is false')
        _private_key_handler(private_key_path, private_key_export)

    if public_key_path:
        _public_key_handler(public_key_path, public_key_export)

    return


@operation
def delete(**_):

    resource_config_property = _.get('resource_config') or ctx.instance\
        .runtime_properties\
        .get('resource_config') or ctx.node.properties\
        .get('resource_config')
    private_key_path = _.get('private_key_path') or ctx.instance\
        .runtime_properties\
        .get('private_key_path') or resource_config_property\
        .get('private_key_path')
    public_key_path = _.get('public_key_path') or ctx.instance\
        .runtime_properties\
        .get('public_key_path') or resource_config_property\
        .get('public_key_path')
    use_secret_store = _.get('use_secret_store') or ctx.instance\
        .runtime_properties\
        .get('use_secret_store') or ctx.node.properties\
        .get('use_secret_store')
    key_name = _.get('key_name') or ctx.instance.runtime_properties\
        .get('key_name') or ctx.node.properties\
        .get('key_name', '{0}-{1}'.format(ctx.deployment.id,
                                          ctx.instance.id))
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


def _private_key_handler(private_key_path, private_key_export):

    private_key_file = \
        tempfile.NamedTemporaryFile(delete=False)

    private_key_path_expanded = os.path.expanduser(private_key_path)
    if private_key_path_expanded:
        with open(private_key_file.name, 'w') as outfile_private_key:
            outfile_private_key.write(private_key_export)
        try:
            directory = os.path.dirname(private_key_path_expanded)
            if not os.path.exists(directory):
                os.makedirs(directory)
            os.rename(private_key_file.name,
                      private_key_path_expanded)
        except OSError as e:
            raise NonRecoverableError(str(e))

        os.chmod(os.path.expanduser(private_key_path),
                 0600)

    return


def _public_key_handler(public_key_path, public_key_export):

    public_key_file = \
        tempfile.NamedTemporaryFile(delete=False)

    with open(public_key_file.name, 'w') as outfile_public_key:
        outfile_public_key.write(public_key_export)
    try:
        os.rename(public_key_file.name,
                  os.path.expanduser(public_key_path))
    except OSError as e:
        raise NonRecoverableError(str(e))

    return


def _remove_path(key_path):

    try:
        os.remove(os.path.expanduser(key_path))
    except OSError as e:
        raise NonRecoverableError(str(e))
