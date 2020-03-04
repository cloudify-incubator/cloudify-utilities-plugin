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
import base64
import yaml
import mock
from cloudify.mocks import MockCloudifyContext
from cloudify_cloudinit import CloudInit
from cloudify.state import current_ctx

NODE_PROPS = {
    'header': 'Content-Type: text/cloud_config',
    'resource_config': {},
}
RUNTIME_PROPS = {
    'resource_config': {},
}

DEPLOYMENT_PROXY_TYPE = 'cloudify.nodes.CloudInit'
MINIMUM_CLOUD_CONFIG = 'Content-Type: text/cloud_config\n{}\n'


class CloudifyCloudInitTestBase(unittest.TestCase):

    def get_mock_ctx(self,
                     test_name,
                     test_properties=NODE_PROPS,
                     runtime_properties=RUNTIME_PROPS,
                     node_type=DEPLOYMENT_PROXY_TYPE,
                     retry_number=0):

        operation = {
            'retry_number': retry_number
        }

        ctx = MockCloudifyContext(
            node_id=test_name,
            deployment_id=test_name,
            operation=operation,
            properties=test_properties,
            runtime_properties=runtime_properties
        )

        ctx.operation._operation_context = {'name': 'some.test'}
        ctx.node.type_hierarchy = ['cloudify.nodes.Root', node_type]
        ctx.get_resource_and_render = mock.Mock(
            return_value="resource_and_render")
        ctx.get_resource = mock.Mock(
            return_value="get_resource")
        try:
            ctx.node.type = node_type
        except AttributeError:
            ctx.logger.error('Failed to set node type attribute.')
        return ctx

    def test_operation_delete(self):
        """Test the delete function"""

        test_name = 'test_operation_delete'
        _ctx = self.get_mock_ctx(test_name)
        current_ctx.set(_ctx)
        _ctx.instance.runtime_properties['a'] = 'b'

        CloudInit(operation_inputs={}).delete()
        self.assertFalse(_ctx.instance.runtime_properties)

    def test_operation_update(self):
        """Test the update function"""

        test_name = 'test_operation_update'
        _ctx = self.get_mock_ctx(test_name)
        current_ctx.set(_ctx)

        # First time with no inputs.
        CloudInit(operation_inputs={}).update()
        self.assertEquals(
            MINIMUM_CLOUD_CONFIG,
            _ctx._runtime_properties.get('cloud_config'))

        # Operation inputs for the rest of the test.
        update_inputs = {
            'resource_config': {'packages': ['package1', 'package2']}
        }

        # Test that Operation inputs override the current ctx.
        CloudInit(operation_inputs=update_inputs).update()
        self.assertEquals(
            # Need to covert before compare as we can have different syntax
            yaml.load(
                MINIMUM_CLOUD_CONFIG.format("packages: [package1, package2]")),
            yaml.load(
                _ctx._runtime_properties.get('cloud_config')))

        # Test that base64 version of inputs are equivalent.
        _ctx.node.properties['encode_base64'] = True
        CloudInit(operation_inputs={}).update()
        self.assertEquals(
            # Need to covert before compare as we can have different syntax
            yaml.load(
                MINIMUM_CLOUD_CONFIG.format("packages: [package1, package2]")),
            yaml.load(base64.decodestring(
                _ctx._runtime_properties.get('cloud_config'))))

        # Test that even if we run Base64 on the string
        # the resource_config is not touched.
        self.assertEquals(
            update_inputs.get('resource_config'),
            _ctx._runtime_properties.get('resource_config'))

        # Test that cloud_config string can be ignored.
        _ctx.node.properties['encode_base64'] = False
        CloudInit(operation_inputs={}).update()
        self.assertEquals(
            # Need to covert before compare as we can have different syntax
            yaml.load(
                MINIMUM_CLOUD_CONFIG.format("packages: [package1, package2]")),
            yaml.load(
                _ctx._runtime_properties.get('cloud_config')))

        # check file content
        update_inputs = {
            'resource_config': {'write_files': [{
                'path': 'direct',
                'content': 'abc'
            }, {
                'path': 'resource',
                'content': {
                    'resource_name': 'resource',
                    'resource_type': 'file_resource'
                }
            }, {
                'path': 'resource_render',
                'content': {
                    'resource_type': 'file_resource',
                    'resource_name': 'render',
                    'template_variables': {'a': 'b'}
                }
            }]}
        }

        # Test that Operation inputs override the current ctx.
        CloudInit(operation_inputs=update_inputs).update()
        self.assertEquals(
            {
                'packages': ['package1', 'package2'],
                'Content-Type': 'text/cloud_config',
                'write_files': [{
                    'content': 'abc',
                    'path': 'direct'
                }, {
                    'content': '|\nget_resource',
                    'path': 'resource'
                }, {
                    'content': '|\nresource_and_render',
                    'path': 'resource_render'
                }]
            },
            # Need to covert before compare as we can have different syntax
            yaml.load(
                _ctx._runtime_properties.get('cloud_config')))

        # custom cases
        _ctx.get_resource = mock.Mock(side_effect=ValueError('Strage'))
        update_inputs = {
            'resource_config': {'write_files': [{
                'path': 'resource',
                'content': {
                    'resource_name': 'resource',
                    'resource_type': 'file_resource'
                }
            }, 'something_strage']}
        }
        CloudInit(operation_inputs=update_inputs).update()


if __name__ == '__main__':
    unittest.main()
