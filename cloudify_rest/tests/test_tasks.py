########
# Copyright (c) 2014-2018 Cloudify Platform Ltd. All rights reserved
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
import mock

from cloudify.exceptions import NonRecoverableError
from cloudify.mocks import MockCloudifyContext
from cloudify.state import current_ctx
from cloudify.manager import DirtyTrackingDict

from cloudify_rest import tasks

TEMPLATE = """
    rest_calls:
        - path: http://check.test/
"""


class TestTasks(unittest.TestCase):

    def tearDown(self):
        current_ctx.clear()
        super(TestTasks, self).tearDown()

    def _gen_ctx(self):
        _ctx = MockCloudifyContext(
            'node_name',
            properties={},
        )

        _ctx._execution_id = "execution_id"
        _ctx.instance.host_ip = None
        _ctx.instance._runtime_properties = DirtyTrackingDict({})
        _ctx.get_resource = mock.Mock(return_value=TEMPLATE)
        current_ctx.set(_ctx)
        return _ctx

    def test_execute_mock_sdk(self):
        # empty tempate
        _ctx = self._gen_ctx()
        tasks._execute({}, "", instance=_ctx.instance, node=_ctx.node,
                       save_path=None, prerender=False, remove_calls=False,
                       retry_count=1, retry_sleep=15)

        # run without issues
        _ctx = self._gen_ctx()
        sdk_process = mock.Mock(return_value={
            'result_properties': {'a': 'b'},
            'calls': [{'path': 'http://check.test/'}]
        })
        with mock.patch("cloudify_rest_sdk.utility.process", sdk_process):
            tasks._execute({}, "rest_calls.yaml", instance=_ctx.instance,
                           node=_ctx.node, save_path=None, prerender=False,
                           remove_calls=False, retry_count=1,
                           retry_sleep=15)
            self.assertDictEqual(_ctx.instance.runtime_properties, {
                'calls': [{'path': 'http://check.test/'}],
                'result_properties': {'a': 'b'}})

        # run without issues, remove calls
        _ctx = self._gen_ctx()
        sdk_process = mock.Mock(return_value={
            'result_properties': {'a': 'b'},
            'calls': [{'path': 'http://check.test/'}]
        })
        with mock.patch("cloudify_rest_sdk.utility.process", sdk_process):
            tasks._execute({}, "rest_calls.yaml", instance=_ctx.instance,
                           node=_ctx.node, save_path=None, prerender=False,
                           remove_calls=True, retry_count=1,
                           retry_sleep=15)
            self.assertDictEqual(_ctx.instance.runtime_properties, {
                'a': 'b'})

        # run without issues, remove calls, with save_path
        _ctx = self._gen_ctx()
        sdk_process = mock.Mock(return_value={
            'result_properties': {'a': 'b'},
            'calls': [{'path': 'http://check.test/'}]
        })
        with mock.patch("cloudify_rest_sdk.utility.process", sdk_process):
            tasks._execute({'1': '2'}, "rest_calls.yaml",
                           instance=_ctx.instance, node=_ctx.node,
                           save_path='save', prerender=False,
                           remove_calls=True, retry_count=1,
                           retry_sleep=15)
            self.assertDictEqual(_ctx.instance.runtime_properties, {
                'save': {'a': 'b'}})
        sdk_process.assert_called_with({'1': '2'}, TEMPLATE, {},
                                       prerender=False,
                                       resource_callback=_ctx.get_resource)
        _ctx.get_resource.assert_called_with("rest_calls.yaml")

        # Check exception
        _ctx = self._gen_ctx()
        sdk_process = mock.Mock(side_effect=Exception('abc'))
        with mock.patch("cloudify_rest_sdk.utility.process", sdk_process):
            with self.assertRaises(NonRecoverableError):
                tasks._execute({'1': '2'}, "rest_calls.yaml",
                               instance=_ctx.instance, node=_ctx.node,
                               save_path='save', prerender=False,
                               remove_calls=True, retry_count=1,
                               retry_sleep=15)

    def test_execute_as_relationship(self):
        _source_ctx = MockCloudifyContext(
            'source_name',
            properties={},
            runtime_properties={}
        )
        _target_ctx = MockCloudifyContext(
            'target_name',
            properties={},
            runtime_properties={}
        )
        _ctx = MockCloudifyContext(
            "execution_id",
            target=_target_ctx,
            source=_source_ctx
        )
        current_ctx.set(_ctx)

        tasks.execute_as_relationship(ctx=_ctx)


if __name__ == '__main__':
    unittest.main()
