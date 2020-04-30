######
# Copyright (c) 2016-2018 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from . import get_desired_value

import sys
import os
import tempfile
import shutil
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError
from cloudify.utils import exception_to_error_cause
from cloudify import ctx, manager
from cloudify_rest_client.exceptions import CloudifyClientError

from cloudify_terminal import operation_cleanup

ALGORITHM = 'RSA'

# runtime names
SECRETS_KEY_NAME = 'secret_key_name'
PUBLIC_KEY_PATH = 'public_key_path'
PRIVATE_KEY_PATH = 'private_key_path'
PUBLIC_KEY_EXPORT = 'public_key_export'
PRIVATE_KEY_EXPORT = 'private_key_export'
SECRETS_KEY_OWNER = 'secrets_key_owner'


@operation(resumable=True)
def create(**_):
    for key in [SECRETS_KEY_NAME, PUBLIC_KEY_PATH, PRIVATE_KEY_PATH,
                PUBLIC_KEY_EXPORT, PRIVATE_KEY_EXPORT, SECRETS_KEY_OWNER]:
        if key in ctx.instance.runtime_properties:
            ctx.logger.error("You should run delete before run create")
            return

    config = get_desired_value(
        'resource_config', _,
        ctx.instance.runtime_properties,
        ctx.node.properties)

    private_key_path = config.get('private_key_path')
    public_key_path = config.get('public_key_path')
    openssh_format = config.get('openssh_format', True)
    algorithm = config.get('algorithm')
    bits = config.get('bits')
    use_secret_store = config.get(
        'use_secret_store') or ctx.node.properties.get('use_secret_store')
    key_name = config.get('key_name') or '{0}-{1}'.format(ctx.deployment.id,
                                                          ctx.instance.id)
    store_private_key_material = _.get('store_private_key_material', False)
    store_public_key_material = _.get('store_public_key_material', True)
    use_secrets_if_exist = config.get(
        'use_secrets_if_exist') or ctx.node.properties.get(
        'use_secrets_if_exist')

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

    if not use_secret_store and use_secrets_if_exist:
        raise NonRecoverableError(
            'Cant enable "use_secrets_if_exist" property without '
            'enable "use_secret_store" property')

    key_object = rsa.generate_private_key(
        backend=default_backend(),
        public_exponent=65537,
        key_size=bits
    )
    private_key_export = key_object.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption())
    public_key_export = key_object.public_key().public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH
    )

    if use_secret_store:
        private_name = '{0}_private'.format(key_name)
        public_name = '{0}_public'.format(key_name)
        if use_secrets_if_exist and _check_if_secret_exist(
                private_name) and _check_if_secret_exist(public_name):
            ctx.instance.runtime_properties[SECRETS_KEY_OWNER] = False
            private_key_export = _get_secret(private_name).value
            public_key_export = _get_secret(public_name).value
        # if the user want to use existing secrets but one of them is missing
        elif use_secrets_if_exist and (
                _check_if_secret_exist(public_name) ^ _check_if_secret_exist(
                private_name)):
            raise NonRecoverableError('Cant use existing secrets: {0}, {1} '
                                      'because only one of them exists in '
                                      'your manager'.format(public_name,
                                                            private_name))
        else:
            _create_secret(private_name, private_key_export)
            _create_secret(public_name, public_key_export)
            ctx.instance.runtime_properties[SECRETS_KEY_OWNER] = True
        ctx.instance.runtime_properties[SECRETS_KEY_NAME] = key_name

    if (
        not private_key_path and
        not use_secret_store and
        not store_private_key_material
    ):
        raise NonRecoverableError(
            'Must provide private_key_path when use_secret_store is false')

    if private_key_path:
        _write_key_file(private_key_path,
                        private_key_export,
                        _private_key_permissions=True)
        ctx.instance.runtime_properties[PRIVATE_KEY_PATH] = private_key_path

    if public_key_path:
        _write_key_file(public_key_path, public_key_export)
        ctx.instance.runtime_properties[PUBLIC_KEY_PATH] = public_key_path

    if store_public_key_material:
        ctx.instance.runtime_properties[PUBLIC_KEY_EXPORT] = \
            public_key_export

    if store_private_key_material:
        ctx.instance.runtime_properties[PRIVATE_KEY_EXPORT] = \
            private_key_export


@operation_cleanup
def delete(**_):
    # remove keys only if created on previous step
    key_name = ctx.instance.runtime_properties.get(SECRETS_KEY_NAME)
    if key_name and ctx.instance.runtime_properties.get(SECRETS_KEY_OWNER):
        private_name = '{0}_private'.format(key_name)
        if _get_secret(private_name):
            _delete_secret(private_name)
        public_name = '{0}_public'.format(key_name)
        if _get_secret(public_name):
            _delete_secret(public_name)
        del ctx.instance.runtime_properties[SECRETS_KEY_NAME]
        del ctx.instance.runtime_properties[SECRETS_KEY_OWNER]
    else:
        ctx.logger.info(
            "Skipping delete secrets task because you are using a secret that"
            " was not created in this deployment.")
    # remove stored to filesystem keys
    private_key_path = ctx.instance.runtime_properties.get(PRIVATE_KEY_PATH)
    public_key_path = ctx.instance.runtime_properties.get(PUBLIC_KEY_PATH)
    if private_key_path:
        _remove_path(private_key_path)
        del ctx.instance.runtime_properties[PRIVATE_KEY_PATH]

    if public_key_path:
        _remove_path(public_key_path)
        del ctx.instance.runtime_properties[PUBLIC_KEY_PATH]


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


def _check_if_secret_exist(key):
    try:
        if _get_secret(key).key == key:
            return True
        return False
    except NonRecoverableError:
        return False


def _delete_secret(key):
    try:
        client = manager.get_rest_client()
        client.secrets.delete(key)
    except CloudifyClientError as e:
        raise NonRecoverableError(str(e))


def _write_key_file(_key_file_path,
                    _key_file_material,
                    _private_key_permissions=False):
    expanded_key_path = os.path.expanduser(_key_file_path)
    with tempfile.NamedTemporaryFile('wb', delete=False) as temporary_file:
        temporary_file.write(_key_file_material)
        temporary_file.close()
        try:
            directory = os.path.dirname(expanded_key_path)
            if not os.path.exists(directory):
                os.makedirs(directory)
            shutil.move(temporary_file.name, expanded_key_path)
        except Exception:
            _, last_ex, last_tb = sys.exc_info()
            raise NonRecoverableError(
                "Failed moving private key", causes=[
                    exception_to_error_cause(last_ex, last_tb)])
        finally:
            if os.path.exists(temporary_file.name):
                os.remove(temporary_file.name)

    if _private_key_permissions:
        os.chmod(os.path.expanduser(_key_file_path), 0o600)


def _remove_path(key_path):
    try:
        path = os.path.expanduser(key_path)
        if os.path.exists(path):
            os.remove(path)
    except OSError as e:
        raise NonRecoverableError(str(e))
