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

import tempfile
import os
import stat

import testtools
from cloudify.mocks import MockCloudifyContext
from cloudify_files import tasks, utils
from cloudify.state import current_ctx
from cloudify.exceptions import OperationRetry

DOWNLOAD_RESOURCE = ''

FILE_CONTENT = 'hello world\nhello world\n'

CONFIG_FILE_CONTENT = """[other]
string

[defaults]
host_key_checking = False
log_path = string
inventory = string
private_key_file = string


"""

DOWNLOAD_FILE_NODE_PROPS = {
    'resource_config':
        {
            'resource_path': DOWNLOAD_RESOURCE,
            'template_variables': {
                'key': 'value'
            },
            'file_permissions': '0777'
        },
}

CONFIG_FILE_NODE_PROPS = {
    'resource_config':
        {
            'config_sections': {
                'defaults': {
                    'host_key_checking': False,
                    'private_key_file': 'string',
                    'inventory': 'string',
                    'log_path': 'string'
                },
                'other': {
                    'string': None
                }
            },
            'file_permissions': '0777'
        },
}

REGULAR_FILE_NODE_PROPS = {
    'resource_config':
        {
            'file_content': FILE_CONTENT,
            'file_permissions': '0777'
        },
}

NODE_TYPE = 'cloudify.nodes.File'


class CloudifyFileTestBase(testtools.TestCase):

    def get_mock_ctx(self,
                     test_name,
                     test_properties=REGULAR_FILE_NODE_PROPS,
                     node_type=NODE_TYPE,
                     retry_number=0):

        operation = {
            'retry_number': retry_number
        }
        _, temporary_file_path = tempfile.mkstemp()
        test_properties['resource_config']['target_path'] = \
            temporary_file_path

        ctx = MockCloudifyContext(
            node_id=test_name,
            deployment_id=test_name,
            operation=operation,
            properties=test_properties,
            runtime_properties={}
        )

        ctx.operation._operation_context = {'name': 'some.test'}
        ctx.node.type_hierarchy = ['cloudify.nodes.Root', node_type]
        ctx.node.type = node_type

        return ctx

    def test_operation_create_bad_target_path(self):
        """Test the update function"""

        test_name = 'test_operation_create_bad_target_path'
        _ctx = self.get_mock_ctx(test_name)
        _ctx.node.properties['resource_config']['target_path'] = \
            '/no/os/in/the/world/has/this/path/file'
        current_ctx.set(_ctx)
        error = self.assertRaises(OperationRetry, tasks.create, ctx=_ctx)
        self.assertIn(
            '/no/os/in/the/world/has/this/path does not exist yet',
            error.message)

    def test_operation_create_regular_file(self):
        """Test the update function"""

        test_name = 'test_operation_create_regular_file'
        _ctx = self.get_mock_ctx(test_name)
        current_ctx.set(_ctx)

        tasks.create(ctx=_ctx)
        test_file = _ctx.node.properties['resource_config']['target_path']
        self.addCleanup(os.remove, test_file)
        with open(test_file, 'r') as outfile:
            file_content = outfile.read()
        os_stat = os.stat(test_file)
        self.assertTrue(
            bool(os_stat.st_mode & stat.S_IRWXU | stat.S_IRWXU | stat.S_IRWXO))
        self.assertEquals(file_content, FILE_CONTENT)

    def test_operation_create_download_resource(self):
        """Test the update function"""

        test_name = 'test_operation_create_download_resource'
        _ctx = self.get_mock_ctx(
            test_name,
            test_properties=DOWNLOAD_FILE_NODE_PROPS)
        current_ctx.set(_ctx)
        tasks.create(ctx=_ctx)
        test_file = _ctx.node.properties['resource_config']['target_path']
        self.addCleanup(os.remove, test_file)
        os_stat = os.stat(test_file)
        self.assertTrue(
            bool(os_stat.st_mode & stat.S_IRWXU | stat.S_IRWXU | stat.S_IRWXO))
        with open(test_file, 'r') as outfile:
            self.assertEquals('', outfile.read())

    def test_operation_create_config(self):
        """Test the update function"""

        test_name = 'test_operation_create_config'
        _ctx = self.get_mock_ctx(
            test_name,
            test_properties=CONFIG_FILE_NODE_PROPS)
        current_ctx.set(_ctx)
        tasks.create(ctx=_ctx)
        test_file = _ctx.node.properties['resource_config']['target_path']
        self.addCleanup(os.remove, test_file)
        os_stat = os.stat(test_file)
        self.assertTrue(
            bool(os_stat.st_mode & stat.S_IRWXU | stat.S_IRWXU | stat.S_IRWXO))
        with open(test_file, 'r') as outfile:
            self.assertEquals(
                sorted(CONFIG_FILE_CONTENT),
                sorted(outfile.read()))

    def test_operation_remove(self):
        """Test the update function"""

        test_name = 'test_operation_remove'
        _ctx = self.get_mock_ctx(
            test_name,
            test_properties=CONFIG_FILE_NODE_PROPS)
        test_file = _ctx.node.properties['resource_config']['target_path']
        self.addCleanup(os.remove, test_file)
        _, temporary_file_path = tempfile.mkstemp()
        self.addCleanup(os.remove, temporary_file_path)
        OLD_STRING = '[another]\nsomething\n\n'
        with open(temporary_file_path, 'w') as infile:
            infile.write(OLD_STRING)
        _ctx.node.properties['resource_config']['target_path'] = \
            temporary_file_path
        _ctx.node.properties['use_external_resource'] = True
        current_ctx.set(_ctx)

        tasks.create(ctx=_ctx)
        os_stat = os.stat(temporary_file_path)
        self.assertTrue(
            bool(os_stat.st_mode & stat.S_IRWXU | stat.S_IRWXU | stat.S_IRWXO))
        with open(temporary_file_path, 'r') as outfile:
            self.assertEquals(
                sorted(OLD_STRING + CONFIG_FILE_CONTENT),
                sorted(outfile.read()))
        tasks.remove(ctx=_ctx)
        with open(temporary_file_path, 'r') as outfile:
            self.assertEquals(
                OLD_STRING + '\n',
                outfile.read())

    def test_operation_delete(self):
        """Test the update function"""

        test_name = 'test_operation_create_regular_file'
        _ctx = self.get_mock_ctx(test_name)
        current_ctx.set(_ctx)

        tasks.create(ctx=_ctx)
        test_file = _ctx.node.properties['resource_config']['target_path']
        tasks.delete(ctx=_ctx)
        self.assertFalse(os.path.exists(test_file))

    def test_util_execute_command(self):
        test_name = 'test_util_execute_command'
        _ctx = self.get_mock_ctx(test_name)
        current_ctx.set(_ctx)
        _, temporary_file_path = tempfile.mkstemp()
        command = "rm {0}".format(temporary_file_path)
        utils.execute_command(command, debug=True)
        self.assertEquals(False, os.path.exists(temporary_file_path))
