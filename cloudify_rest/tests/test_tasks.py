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

import mock
import unittest

from cloudify.state import current_ctx
from cloudify.manager import DirtyTrackingDict
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError

from cloudify_common_sdk._compat import PY2

from .. import tasks

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
        _ctx.get_resource = mock.Mock(return_value=TEMPLATE.encode("utf-8"))
        current_ctx.set(_ctx)
        return _ctx

    def test_execute_mock_sdk(self):
        # empty tempate
        _ctx = self._gen_ctx()
        tasks._execute({}, "",
                       instance_props=_ctx.instance.runtime_properties,
                       node_props=_ctx.node.properties,
                       ctx=_ctx, save_path=None, prerender=False,
                       remove_calls=False, retry_count=1, retry_sleep=15)

        # run without issues
        _ctx = self._gen_ctx()
        sdk_process = mock.Mock(return_value={
            'result_properties': {'a': 'b'},
            'calls': [{'path': 'http://check.test/'}]
        })
        with mock.patch("cloudify_rest_sdk.utility.process", sdk_process):
            tasks._execute({}, "rest_calls.yaml",
                           instance_props=_ctx.instance.runtime_properties,
                           node_props=_ctx.node.properties,
                           ctx=_ctx, save_path=None,
                           prerender=False, remove_calls=False,
                           resource_callback=_ctx.get_resource,
                           retry_count=1, retry_sleep=15)
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
            tasks._execute({}, "rest_calls.yaml",
                           instance_props=_ctx.instance.runtime_properties,
                           node_props=_ctx.node.properties,
                           ctx=_ctx, save_path=None,
                           prerender=False, remove_calls=True,
                           resource_callback=_ctx.get_resource,
                           retry_count=1, retry_sleep=15)
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
                           instance_props=_ctx.instance.runtime_properties,
                           node_props=_ctx.node.properties, ctx=_ctx,
                           save_path='save', prerender=False,
                           remove_calls=True,
                           resource_callback=_ctx.get_resource,
                           retry_count=1, retry_sleep=15)
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
                               instance_props=_ctx.instance.runtime_properties,
                               node_props=_ctx.node.properties,
                               ctx=_ctx, save_path='save', prerender=False,
                               remove_calls=True,
                               resource_callback=_ctx.get_resource,
                               retry_count=1, retry_sleep=15)

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

        mock_execute = mock.Mock(return_value=None)
        with mock.patch("cloudify_rest.tasks._execute", mock_execute):
            tasks.execute_as_relationship(ctx=_ctx)

        mock_execute.assert_called_with(
            params={}, template_file=None, auth=None, ctx=_ctx,
            instance_props={}, node_props={}, prerender=False,
            remove_calls=False, retry_count=1, retry_sleep=15,
            resource_callback=_ctx.get_resource,
            save_path=None)

    def test_execute(self):
        _ctx = self._gen_ctx()
        current_ctx.set(_ctx)

        mock_execute = mock.Mock(return_value=None)
        with mock.patch("cloudify_rest.tasks._execute", mock_execute):
            tasks.execute(ctx=_ctx)

        mock_execute.assert_called_with(
            params={}, template_file=None, auth=None, ctx=_ctx,
            instance_props={'_finished_operations': {None: True}},
            node_props={}, prerender=False,
            remove_calls=False, retry_count=1, retry_sleep=15,
            resource_callback=_ctx.get_resource,
            save_path=None)

    def test_execute_as_workflow(self):
        # wrong context type
        _ctx = mock.Mock()
        _ctx.type = '<unknown>'

        mock_execute = mock.Mock(return_value=None)
        with mock.patch("cloudify_rest.tasks._execute", mock_execute):
            with self.assertRaises(tasks.NonRecoverableError):
                tasks.execute_as_workflow(
                    inputs={
                        'blueprint_id': '<blueprint>',
                        'deployment_id': '<deployment>',
                        'tenant_name': '<tenant>',
                        'rest_token': '<token>'}, ctx=_ctx,
                    properties={
                        "hosts": ["jsonplaceholder.typicode.com"],
                        "port": 443,
                        "ssl": True, "verify": False})

        # correct context type
        _ctx = mock.Mock()
        _ctx.type = 'deployment'

        mock_execute = mock.Mock(return_value=None)
        with mock.patch("cloudify_rest.tasks._execute", mock_execute):
            tasks.execute_as_workflow(
                inputs={
                    'blueprint_id': '<blueprint>',
                    'deployment_id': '<deployment>',
                    'tenant_name': '<tenant>',
                    'rest_token': '<token>'}, ctx=_ctx,
                properties={
                    "hosts": ["jsonplaceholder.typicode.com"], "port": 443,
                    "ssl": True, "verify": False})
        mock_execute.assert_called_with(
            params={
                '__inputs__': {
                    'tenant_name': '<tenant>',
                    'deployment_id': '<deployment>',
                    'rest_token': '<token>',
                    'blueprint_id': '<blueprint>'}},
            template_file=None, auth=None, ctx=_ctx,
            instance_props={},
            node_props={
                "hosts": ["jsonplaceholder.typicode.com"],
                "port": 443,
                "ssl": True,
                "verify": False
            },
            prerender=False,
            remove_calls=False, retry_count=1, retry_sleep=15,
            resource_callback=tasks.workflow_get_resource,
            save_path=None)

    def test_execute_as_workflow_hook(self):
        _ctx = mock.Mock()
        _ctx.type = 'deployment'

        mock_execute = mock.Mock(return_value=None)
        with mock.patch("cloudify_rest.tasks._execute", mock_execute):
            tasks.execute_as_workflow(
                {
                    'blueprint_id': '<blueprint>',
                    'deployment_id': '<deployment>',
                    'tenant_name': '<tenant>',
                    'rest_token': '<token>'}, ctx=_ctx,
                logger_file='/tmp/workflow_failed.log',
                properties={
                    "hosts": ["jsonplaceholder.typicode.com"], "port": 443,
                    "ssl": True, "verify": False})
        mock_execute.assert_called_with(
            params={
                '__inputs__': {
                    'tenant_name': '<tenant>',
                    'deployment_id': '<deployment>',
                    'rest_token': '<token>',
                    'blueprint_id': '<blueprint>'}},
            template_file=None, auth=None, ctx=_ctx,
            instance_props={},
            node_props={
                "hosts": ["jsonplaceholder.typicode.com"],
                "port": 443,
                "ssl": True,
                "verify": False
            },
            prerender=False,
            remove_calls=False, retry_count=1, retry_sleep=15,
            resource_callback=tasks.workflow_get_resource,
            save_path=None)

    def test_workflow_get_resource(self):
        fake_file = mock.mock_open()
        fake_file.read = mock.Mock(return_value="abc")
        if PY2:
            # python 2
            with mock.patch(
                    '__builtin__.open', fake_file
            ):
                tasks.workflow_get_resource('/proc/read_only_file')
        else:
            # python 3
            with mock.patch(
                    'builtins.open', fake_file
            ):
                tasks.workflow_get_resource('/proc/read_only_file')
        fake_file.assert_called_once_with('/proc/read_only_file', 'r')
        fake_file().read.assert_called_with()


if __name__ == '__main__':
    unittest.main()
