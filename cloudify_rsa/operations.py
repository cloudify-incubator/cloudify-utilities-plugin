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


@operation
def create(args={}, **_):

    resource_config_property = ctx.node.properties.get('resource_config')
    public_key_path = resource_config_property.get('public_key_path')

    private_key_export_type = \
        args.get('private_key_export_type') \
        or 'PEM'

    if resource_config_property.get('OpenSSH_format') is not None:
        if resource_config_property.get('OpenSSH_format'):
            openssh_format = 'OpenSSH'
        else:
            raise NonRecoverableError('Only OpenSSH format is supported')
    else:
        openssh_format = 'OpenSSH'

    algorithm = resource_config_property.get('algorithm')
    if algorithm != 'RSA':
        raise NonRecoverableError('Only RSA algorithm is supported')

    bits = resource_config_property.get('bits')
    key = RSA.generate(bits)
    private_key_export = key.exportKey(private_key_export_type)

    use_secret_store = ctx.node.properties.get('use_secret_store')
    if use_secret_store:
        key_name = ctx.node.properties.get('key_name') or '{0}-{1}' \
            .format(ctx.deployment.id, ctx.instance.id)
        _create_secret(key_name, private_key_export)
    else:
        private_key_path = resource_config_property.get('private_key_path')
        if not private_key_path:
            raise NonRecoverableError('Must provide private_key_path'
                                      ' when use_secret_store is false')

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

    public_key_file = \
        tempfile.NamedTemporaryFile(delete=False)

    pubkey = key.publickey()
    public_key_export = pubkey.exportKey(openssh_format)

    if public_key_path:

        with open(public_key_file.name, 'w') as outfile_public_key:
            outfile_public_key.write(public_key_export)
        try:
            os.rename(public_key_file.name,
                      os.path.expanduser(public_key_path))
        except OSError as e:
            raise NonRecoverableError(str(e))

    if resource_config_property.get('comment'):
        raise NotImplementedError
    if resource_config_property.get('passphrase'):
        raise NotImplementedError
    if resource_config_property.get('unvalidated'):
        raise NotImplementedError

    return


@operation
def delete(args={}, **_):

    resource_config_property = ctx.node.properties.get('resource_config')

    use_secret_store = ctx.node.properties.get('use_secret_store')
    if use_secret_store:
        if ctx.node.properties.get('key_name'):
            key_name = ctx.node.properties.get('key_name')
        else:
            key_name = '{0}-{1}'.format(ctx.deployment.id, ctx.instance.id)

        if _get_secret(key_name):
            _delete_secret(key_name)
    else:
        try:
            os.remove(os.path.expanduser(resource_config_property
                                         .get('private_key_path')))
        except OSError as e:
            raise NonRecoverableError(str(e))
    try:
        os.remove(os.path.expanduser(resource_config_property
                                     .get('public_key_path')))
    except OSError as e:
        raise NonRecoverableError(str(e))

    return


def _create_secret(key, value):

    client = manager.get_rest_client()
    client.secrets.create(key, value)


def _get_secret(key):

    client = manager.get_rest_client()
    return client.secrets.get(key)


def _delete_secret(key):

    client = manager.get_rest_client()
    client.secrets.delete(key)
