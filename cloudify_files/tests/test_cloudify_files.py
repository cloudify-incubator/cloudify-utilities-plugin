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


import os
import tempfile
import testtools
from pwd import getpwnam
from mock import MagicMock

from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError
from cloudify.state import current_ctx

from cloudify_common_sdk._compat import text_type

from .. import tasks as operation_task


class CloudifyFilesTestBase(testtools.TestCase):

    @property
    def _file_path(self):
        _, _file_path = tempfile.mkstemp()
        return _file_path

    @property
    def _downloaded_file_path(self):
        _, _file_path = tempfile.mkstemp()
        return _file_path

    @property
    def _owner(self):
        # For circle.ci.
        _user = os.environ.get('USER', 'circleci')
        _group = os.environ.get('GROUP', 'circleci')
        # Toggle these for local testing.
        return ':'.join([_user, _group])

    @property
    def _user_id(self):
        _owner = self._owner
        if not isinstance(_owner, text_type):
            return None
        split_owner = _owner.split(':')
        if not len(split_owner) == 2:
            return None
        _pwnam = getpwnam(split_owner[0])
        return getattr(_pwnam, 'pw_uid')

    @property
    def _resource_config(self):
        _resource_config = {
            'resource_path': 'resources/file',
            'owner': self._owner,
            'mode': 644,
            'file_path': self._file_path,
            'use_sudo': False
        }
        return _resource_config

    def get_mock_ctx(self):
        _ctx = MockCloudifyContext(
            node_id='mock',
            deployment_id='mock',
            operation={'retry_number': 1},
            properties={},
            runtime_properties={}
        )
        setattr(
            _ctx,
            'download_resource',
            MagicMock(return_value=self._downloaded_file_path))
        return _ctx

    def common_asserts(self, _operation_output):
        self.assertIs(True, _operation_output)
        self.assertIs(
            True, os.path.exists(self._file_path))
        self.assertIs(
            True,
            os.access(
                self._file_path,
                os.R_OK))
        self.assertIs(
            True,
            os.access(
                self._file_path,
                os.W_OK))
        self.assertIs(
            False,
            os.access(
                self._file_path,
                os.X_OK))
        file_stat = os.stat(self._file_path)
        self.assertEqual(self._user_id, getattr(file_stat, 'st_uid'))

    def test_operation_create_from_inputs_no_file(self):
        """Test the create function with inputs"""

        _ctx = self.get_mock_ctx()
        current_ctx.set(_ctx)
        resource_config = self._resource_config
        resource_config['file_path'] = \
            '/aint/no/platform/in/the/world/with/this/dumb/path' \
            'yet'
        self.addCleanup(os.remove, self._file_path)
        raised_error = self.assertRaises(
            NonRecoverableError,
            operation_task.create,
            resource_config=resource_config)
        self.assertIn(
            'No such file or directory',
            str(raised_error))

    def test_operation_create_from_inputs(self):
        """Test the create function with inputs"""

        _ctx = self.get_mock_ctx()
        current_ctx.set(_ctx)
        resource_config = self._resource_config
        self.addCleanup(os.remove, self._file_path)
        operation_output = \
            operation_task.create(resource_config=resource_config)
        self.common_asserts(operation_output)

    def test_operation_create_from_node_properties(self):
        """Test the create function with node properties"""

        _ctx = self.get_mock_ctx()
        current_ctx.set(_ctx)
        _ctx.node.properties['resource_config'] = self._resource_config
        self.addCleanup(os.remove, self._file_path)
        operation_output = operation_task.create()
        self.common_asserts(operation_output)

    def test_operation_create_from_runtime_properties(self):
        """Test the create function with runtime properties"""

        _ctx = self.get_mock_ctx()
        current_ctx.set(_ctx)
        _ctx.instance.runtime_properties['resource_config'] = \
            self._resource_config
        self.addCleanup(os.remove, self._file_path)
        operation_output = operation_task.create()
        self.common_asserts(operation_output)

    def test_operation_delete(self):
        """Test the create function with runtime properties"""

        _ctx = self.get_mock_ctx()
        current_ctx.set(_ctx)
        resource_config = self._resource_config
        # self.addCleanup(os.remove, self._file_path)
        operation_output = \
            operation_task.create(resource_config=resource_config)
        self.common_asserts(operation_output)
        operation_task.delete(resource_config=resource_config)
        self.assertIs(False, os.path.exists(resource_config.get('file_path')))

    def test_operation_create_from_inputs_sudo(self):
        """Test the create function with inputs"""

        _ctx = self.get_mock_ctx()
        current_ctx.set(_ctx)
        self._resource_config['use_sudo'] = True
        resource_config = self._resource_config
        self.addCleanup(os.remove, self._file_path)
        operation_output = \
            operation_task.create(resource_config=resource_config)
        self.common_asserts(operation_output)

    def test_operation_create_from_node_properties_sudo(self):
        """Test the create function with node properties"""

        _ctx = self.get_mock_ctx()
        current_ctx.set(_ctx)
        self._resource_config['use_sudo'] = True
        _ctx.node.properties['resource_config'] = self._resource_config
        self.addCleanup(os.remove, self._file_path)
        operation_output = operation_task.create()
        self.common_asserts(operation_output)

    def test_operation_create_from_runtime_properties_sudo(self):
        """Test the create function with runtime properties"""

        _ctx = self.get_mock_ctx()
        current_ctx.set(_ctx)
        self._resource_config['use_sudo'] = True
        _ctx.instance.runtime_properties['resource_config'] = \
            self._resource_config
        self.addCleanup(os.remove, self._file_path)
        operation_output = operation_task.create()
        self.common_asserts(operation_output)

    def test_operation_delete_sudo(self):
        """Test the create function with runtime properties"""

        _ctx = self.get_mock_ctx()
        current_ctx.set(_ctx)
        self._resource_config['use_sudo'] = True
        resource_config = self._resource_config
        # self.addCleanup(os.remove, self._file_path)
        operation_output = \
            operation_task.create(resource_config=resource_config)
        self.common_asserts(operation_output)
        operation_task.delete(resource_config=resource_config)
        self.assertIs(False, os.path.exists(resource_config.get('file_path')))
