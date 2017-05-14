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

import mock
import testtools

from cloudify.mocks import MockCloudifyContext
from cloudify_rest_client.exceptions import CloudifyClientError

REST_CLIENT_EXCEPTION = \
    mock.MagicMock(side_effect=CloudifyClientError('Mistake'))

DEPLOYMENT_PROXY_PROPS = {
    'resource_config': {
        'blueprint': {
            'id': '',
            'blueprint_archive': 'URL',
            'main_file_name': 'blueprint.yaml'
        },
        'deployment': {
            'id': '',
            'inputs': {},
            'outputs': {
                'output1': 'output2'
            }
        }
    }
}

DEPLOYMENT_PROXY_TYPE = 'cloudify.nodes.DeploymentProxy'


class DeploymentProxyTestBase(testtools.TestCase):

    def get_mock_ctx(self,
                     test_name,
                     test_properties=DEPLOYMENT_PROXY_PROPS,
                     node_type=DEPLOYMENT_PROXY_TYPE,
                     retry_number=0):

        test_node_id = test_name
        test_properties = test_properties

        operation = {
            'retry_number': retry_number
        }
        ctx = MockCloudifyContext(
            node_id=test_node_id,
            deployment_id=test_name,
            operation=operation,
            properties=test_properties
        )

        ctx.operation._operation_context = {'name': 'some.test'}
        ctx.node.type_hierarchy = ['cloudify.nodes.Root', node_type]
        ctx.node.type = node_type

        return ctx
