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
from cloudify.state import current_ctx
from cloudify_rest_client.exceptions import CloudifyClientError


class TestCloudifyRequests(testtools.TestCase):

    def get_mock_ctx(self,
                     test_name,
                     test_properties):

        test_node_id = test_name
        test_properties = test_properties

        ctx = MockCloudifyContext(
            node_id=test_node_id,
            deployment_id=test_name,
            properties=test_properties
        )

        ctx.node.type_hierarchy = ['cloudify.nodes.Root']

        return ctx

    def test_poll_with_timeout(self):
        from cloudify_deployment_proxy.tasks import poll_with_timeout

        test_name = 'test_poll_with_timeout'
        test_properties = {
            'resource_config': {'deployment_id': 'test_poll_with_timeout'}
        }
        _ctx = self.get_mock_ctx(test_name,
                                 test_properties)
        current_ctx.set(_ctx)

        mock_timeout = .1
        mock_interval = .1
        mock_pollster = None

        # Test that failed polling raises an error
        mock_pollster = mock.MagicMock
        output = poll_with_timeout(mock_pollster, mock_timeout, mock_interval)
        self.assertEqual(False, output)

    def test_all_dep_workflows_in_state_pollster(self):
        from cloudify_deployment_proxy.tasks import \
            all_dep_workflows_in_state_pollster

        test_name = 'test_all_dep_workflows_in_state_pollster'
        test_properties = {
            'resource_config': {
                'deployment_id': 'test_all_dep_workflows_in_state_pollster'
            }
        }
        _ctx = self.get_mock_ctx(test_name,
                                 test_properties)
        current_ctx.set(_ctx)

        # Test that all_dep_workflows.. returns False if not successful.
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            _mock_execution_object = {
                'execution_id': 'care bears care',
                'deployment_id': 'care bears',
                'status': 'failed',
            }
            _mock_list = mock.MagicMock(return_value=[_mock_execution_object])
            mock_client_executions = mock.MagicMock
            setattr(mock_client_executions, 'list', _mock_list)
            setattr(mock_client, 'executions', mock_client_executions)
            output = \
                all_dep_workflows_in_state_pollster(mock_client,
                                                    'care bears',
                                                    'terminated')
            self.assertEqual(False, output)

        # Test that all_dep_workflows.. returns False if not successful.
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            _mock_execution_object = {
                'execution_id': 'care bears care',
                'deployment_id': 'care bears',
                'status': 'terminated',
            }
            _mock_list = mock.MagicMock(return_value=[_mock_execution_object])
            mock_client_executions = mock.MagicMock
            setattr(mock_client_executions, 'list', _mock_list)
            setattr(mock_client, 'executions', mock_client_executions)
            output = \
                all_dep_workflows_in_state_pollster(mock_client,
                                                    'care bears',
                                                    'terminated')
            self.assertEqual(True, output)

    def test_query_deployment_data(self):
        from cloudify_deployment_proxy.tasks import query_deployment_data

        deployment_outputs_expected = 0
        deployment_outputs_mapping = '_zero'

        test_name = 'test_query_deployment_data'
        test_properties = {
            'resource_config': {
                'deployment_id': 'test_query_deployment_data',
                'outputs': {
                    'zero': deployment_outputs_mapping
                }
            }
        }
        _ctx = self.get_mock_ctx(test_name,
                                 test_properties)
        current_ctx.set(_ctx)
        mock_daemonize = False
        mock_interval = .01
        mock_timeout = .01

        # Tests that rest client raises Error
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            _mock_dep_outputs_object = {
                'deployment_id': 'test_query_deployment_data',
                'outputs': {
                    'zero': deployment_outputs_expected
                }
            }
            _mock_list = \
                mock.MagicMock(side_effect=CloudifyClientError('Mistake'))
            mock_deployments = mock.MagicMock
            setattr(mock_client, 'deployments', mock_deployments)
            setattr(mock_deployments, 'get', _mock_list)
            output = query_deployment_data(mock_daemonize,
                                           mock_interval,
                                           mock_timeout)
            self.assertEqual(True, output)
            self.assertNotIn(deployment_outputs_mapping,
                             _ctx.instance.runtime_properties.keys())

        # Tests that the runtime properties are set to the outputs received
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            _mock_dep_outputs_object = {
                'deployment_id': 'test_query_deployment_data',
                'outputs': {
                    'zero': deployment_outputs_expected
                }
            }
            _mock_list = mock.MagicMock(return_value=_mock_dep_outputs_object)
            mock_deployments = mock.MagicMock
            setattr(mock_client, 'deployments', mock_deployments)
            setattr(mock_deployments, 'get', _mock_list)
            output = query_deployment_data(mock_daemonize,
                                           mock_interval,
                                           mock_timeout)
            self.assertEqual(True, output)
            self.assertEqual(
                _ctx.instance.runtime_properties[deployment_outputs_mapping],
                deployment_outputs_expected)
