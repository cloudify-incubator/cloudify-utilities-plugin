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
import unittest
import yaml
import json
import mock

from cloudify.manager import DirtyTrackingDict
from cloudify.mocks import MockCloudifyContext
from cloudify.state import current_ctx

from .. import tasks


NODE_PROPS = {
    'header': 'Content-Type: text/cloud_config',
    'resource_config': {},
}
RUNTIME_PROPS = {
    'resource_config': {},
}

DEPLOYMENT_PROXY_TYPE = 'cloudify.nodes.CloudInit'


class CloudifyCloudTasksTest(unittest.TestCase):

    def tearDown(self):
        current_ctx.clear()
        super(CloudifyCloudTasksTest, self).tearDown()

    def get_mock_ctx(self,
                     test_name,
                     test_properties=NODE_PROPS,
                     runtime_properties=RUNTIME_PROPS,
                     node_type=DEPLOYMENT_PROXY_TYPE,
                     retry_number=0,
                     operation_name=""):

        operation = {
            'retry_number': retry_number
        }

        ctx = MockCloudifyContext(
            node_id=test_name,
            deployment_id=test_name,
            operation=operation,
            properties=test_properties,
        )
        ctx.instance._runtime_properties = DirtyTrackingDict(
            runtime_properties)

        ctx.operation._operation_context = {'name': operation_name}
        ctx.node.type_hierarchy = ['cloudify.nodes.Root', node_type]
        ctx.get_resource_and_render = mock.Mock(
            return_value="resource_and_render")
        ctx.get_resource = mock.Mock(
            return_value="get_resource")
        try:
            ctx.node.type = node_type
        except AttributeError:
            ctx.logger.error('Failed to set node type attribute.')

        current_ctx.set(ctx)
        return ctx

    def test_update(self):

        _ctx = self.get_mock_ctx(
            "check", operation_name="cloudify.interfaces.lifecycle.create")

        tasks.update(ctx=_ctx, resource_config={
            'packages': [
                ["epel-release"],
                ["openssl-devel"]
            ]
        })
        self.assertEquals(
            {
                'Content-Type': 'text/cloud_config',
                'packages': [['epel-release'],
                             ['openssl-devel']]},
            yaml.load(
                _ctx.instance.runtime_properties.get('cloud_config')))
        self.assertEquals(
            {
                'packages': [['epel-release'],
                             ['openssl-devel']]},
            json.loads(
                _ctx.instance.runtime_properties.get('json_config')))

    def test_delete(self):

        _ctx = self.get_mock_ctx(
            "check", operation_name="cloudify.interfaces.lifecycle.delete")

        tasks.delete(ctx=_ctx, resource_config={
            'packages': [
                ["epel-release"],
                ["openssl-devel"]
            ]
        })
        self.assertFalse(_ctx.instance.runtime_properties)


if __name__ == '__main__':
    unittest.main()
