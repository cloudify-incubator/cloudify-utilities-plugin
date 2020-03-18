# Copyright (c) 2020 Cloudify Platform Ltd. All rights reserved
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
import unittest
from mock import Mock, patch

from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext
from cloudify.manager import DirtyTrackingDict


import cloudify_ftp.tasks as tasks


class TestTasks(unittest.TestCase):

    def tearDown(self):
        current_ctx.clear()
        super(TestTasks, self).tearDown()

    def _gen_ctx(self):
        _ctx = MockCloudifyContext(
            'node_name',
            properties={},
        )
        _ctx._operation = Mock()
        _ctx._execution_id = "execution_id"
        _ctx.instance.host_ip = None
        _ctx.instance._runtime_properties = DirtyTrackingDict({})

        current_ctx.set(_ctx)
        return _ctx

    def test_create(self):
        _ctx = self._gen_ctx()

        _ctx._operation.name = "cloudify.interfaces.lifecycle.create"
        tasks.create(ctx=_ctx, resource_config={}, raw_files={}, files={})

        _ctx._operation.name = "cloudify.interfaces.lifecycle.create"
        _ctx.get_resource = Mock(return_value="")
        ftp_mock = Mock()
        with patch("cloudify_ftp.tasks.ftp", ftp_mock):
            tasks.create(
                ctx=_ctx,
                resource_config={
                    'ip': 'localhost',
                    'port': 21,
                    'user': "user",
                    'password': "pass",
                },
                raw_files={
                    "blueprint.yaml": "upload_ftp.yaml"
                },
                files={
                    "new_file.yaml": "yaml_file: abcd"
                },
                force_rerun=True
            )
        self.assertEqual(
            _ctx.instance.runtime_properties,
            {
                'files': ['new_file.yaml', 'blueprint.yaml'],
                '_finished_operations': {
                    'cloudify.interfaces.lifecycle.create': True
                }
            }
        )

    def test_delete(self):
        _ctx = self._gen_ctx()

        tasks.delete(ctx=_ctx, resource_config={})

        _ctx._operation.name = "cloudify.interfaces.lifecycle.delete"
        _ctx.instance.runtime_properties['files'] = ["abc"]
        ftp_mock = Mock()
        with patch("cloudify_ftp.tasks.ftp", ftp_mock):
            tasks.delete(ctx=_ctx, resource_config={
                'ip': 'localhost',
                'port': 21,
                'user': "user",
                'password': "pass",
            })
        ftp_mock.delete.assert_called_with(
            filename='abc', host='localhost', ignore_host=False,
            password='pass', port=21, tls=False, user='user')
        self.assertFalse(_ctx.instance.runtime_properties)


if __name__ == '__main__':
    unittest.main()
