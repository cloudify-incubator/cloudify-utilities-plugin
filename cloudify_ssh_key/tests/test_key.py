# Copyright (c) 2017 GigaSpaces Technologies Ltd. All rights reserved
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

# Built-in Imports
import os
import mock
import tempfile
import testtools

# Third Party Imports
from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext
from cloudify_ssh_key.operations import create, delete, _get_secret


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
                    'OpenSSH_format': True,
                    'algorithm': 'RSA',
                    'bits': 2048
                }
            }
        else:
            test_properties = {
                'use_secret_store': use_secret_store,
                'resource_config': {
                    'private_key_path': '{0}/{1}.pem'.format(
                            key_path,
                            test_name),
                    'public_key_path': '{0}/{1}.pem.pub'.format(
                            key_path,
                            test_name),
                    'OpenSSH_format': True,
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
            create()
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
