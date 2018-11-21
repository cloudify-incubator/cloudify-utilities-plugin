# Copyright (c) 2017-2018 Cloudify Platform Ltd. All rights reserved
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

# Built-in Imports
import os
import mock
import copy
import tempfile
import testtools

# Third Party Imports
from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError
from cloudify_rest_client.exceptions import CloudifyClientError
from cloudify_ssh_key.operations import (create, delete, _get_secret,
                                         _create_secret, _delete_secret,
                                         _remove_path, _write_key_file)


class TestKey(testtools.TestCase):

    def setUp(self):
        super(TestKey, self).setUp()

    def mock_ctx(self, test_name, use_secret_store=False):

        key_path = tempfile.mkdtemp()

        test_node_id = test_name
        if use_secret_store:
            test_properties = {
                'use_secret_store': use_secret_store,
                'key_name': test_name,
                'resource_config': {
                    'public_key_path': '{0}/{1}.pem.pub'.format(
                            key_path,
                            test_name),
                    'openssh_format': True,
                    'algorithm': 'RSA',
                    'bits': 2048
                }
            }
        else:
            test_properties = {
                'use_secret_store': use_secret_store,
                'resource_config': {
                    'private_key_path': '{0}/{1}'.format(
                            key_path,
                            test_name),
                    'public_key_path': '{0}/{1}.pub'.format(
                            key_path,
                            test_name),
                    'openssh_format': True,
                    'algorithm': 'RSA',
                    'bits': 2048
                },
            }

        ctx = MockCloudifyContext(
                node_id=test_node_id,
                properties=test_properties
        )

        return ctx

    def create_private_key_path(self, ctx):
        resource_config = ctx.node.properties['resource_config']
        key_path = os.path.expanduser(
                resource_config.get('private_key_path'))
        return key_path

    def create_public_key_path(self, ctx):
        resource_config = ctx.node.properties['resource_config']
        key_path = os.path.expanduser(
                resource_config.get('public_key_path'))
        return key_path

    def test_operations_with_secret(self):

        ctx = self.mock_ctx('test_delete_with_secret', use_secret_store=True)
        current_ctx.set(ctx=ctx)

        with mock.patch('cloudify.manager.get_rest_client'):
            key_path = self.create_public_key_path(ctx=ctx)
            create(store_private_key_material=True)
            self.assertIsNotNone(
                ctx.instance.runtime_properties.get('private_key_export')
            )
            self.assertIsNotNone(_get_secret('test_delete_with_secret'))
            self.assertTrue(os.path.exists(key_path))
            delete()
            self.assertFalse(os.path.exists(key_path))

    def test_operations_no_secret(self):

        ctx = self.mock_ctx('test_delete_no_secret')
        current_ctx.set(ctx=ctx)

        key_path = self.create_private_key_path(ctx=ctx)
        create()
        self.assertTrue(os.path.exists(key_path))
        delete()
        self.assertFalse(os.path.exists(key_path))

    def test_raise_unimplemented(self):

        corner_cases = [{
            'comment': 'some_comment',
            'passphrase': 'some_passphrase',
            'unvalidated': 'some_unvalidated',
            'openssh_format': False
        }, {
            'algorithm': 'DSA'
        }, {
            'use_secret_store': False,
            'private_key_path': None,
            'openssh_format': True,
            'algorithm': 'RSA',
            'bits': 2048
        }]

        for case in corner_cases:
            _ctx = self.mock_ctx('test_raise_unimplemented', True)
            _ctx.node.properties['use_secret_store'] = False
            current_ctx.set(ctx=_ctx)
            self.assertRaises(NonRecoverableError,
                              create,
                              resource_config=copy.deepcopy(case))

    def test_create_secret_Error(self):
        mock_client = mock.MagicMock(side_effect=CloudifyClientError("e"))
        with mock.patch('cloudify.manager.get_rest_client', mock_client):
            self.assertRaises(NonRecoverableError, _create_secret, 'k', 'v')

    def test_get_secret_Error(self):
        mock_client = mock.MagicMock(side_effect=CloudifyClientError("e"))
        with mock.patch('cloudify.manager.get_rest_client', mock_client):
            self.assertRaises(NonRecoverableError, _get_secret, 'k')

    def test_delete_secret_Error(self):
        mock_client = mock.MagicMock(side_effect=CloudifyClientError("e"))
        with mock.patch('cloudify.manager.get_rest_client', mock_client):
            self.assertRaises(NonRecoverableError, _delete_secret, 'k')

    def test_remove_path_Error(self):
        mock_client = mock.MagicMock(side_effect=OSError("e"))
        with mock.patch('os.remove', mock_client):
            self.assertRaises(NonRecoverableError, _remove_path, 'k')

    def test__write_key_file_Error(self):
        mock_client = mock.MagicMock(side_effect=OSError("e"))
        with mock.patch('os.path.exists', mock.MagicMock(return_value=False)):
            with mock.patch('os.makedirs', mock_client):
                fake_file = mock.mock_open()
                with mock.patch('__builtin__.open', fake_file):
                    self.assertRaises(NonRecoverableError, _write_key_file,
                                      'k', 'content')
