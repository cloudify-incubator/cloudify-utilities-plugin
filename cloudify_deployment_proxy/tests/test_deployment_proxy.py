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
import testtools

# Third Party Imports
import mock

# Cloudify Imports
from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError
from cloudify_rest_client.exceptions import CloudifyClientError


class TestCloudifyRequests(testtools.TestCase):

    def get_mock_ctx(self,
                     test_name,
                     test_properties):

        """ Creates a mock context for the base
            tests
        """
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
        from ..tasks import poll_with_timeout

        test_name = 'test_poll_with_timeout'
        test_properties = {
            'resource_id': 'test_poll_with_timeout',
            'resource_config': {}
        }
        _ctx = self.get_mock_ctx(test_name,
                                 test_properties)
        current_ctx.set(_ctx)

        # Test that non-callable pollster raises error.
        mock_timeout = .1
        mock_interval = .1
        mock_pollster = None
        error = self.assertRaises(NonRecoverableError,
                                  poll_with_timeout,
                                  mock_pollster,
                                  mock_timeout,
                                  mock_interval)
        self.assertIn('is not callable', error.message)

        # Test that failed polling raises an error
        mock_pollster = mock.MagicMock
        output = poll_with_timeout(mock_pollster, mock_timeout, mock_interval)
        error = self.assertEqual(False, output)

    def test_all_dep_workflows_in_state_pollster(self):
        from ..tasks import all_dep_workflows_in_state_pollster

        test_name = 'test_all_dep_workflows_in_state_pollster'
        test_properties = {
            'resource_id': 'test_all_dep_workflows_in_state_pollster',
            'resource_config': {}
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
            output = all_dep_workflows_in_state_pollster(mock_client, 'care bears', 'terminated')
            error = self.assertEqual(False, output)

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
            output = all_dep_workflows_in_state_pollster(mock_client, 'care bears', 'terminated')
            self.assertEqual(True, output)


    def test_wait_for_deployment_ready(self):
        from ..tasks import wait_for_deployment_ready

        test_name = 'test_wait_for_deployment_ready'
        test_properties = {
            'resource_id': 'test_wait_for_deployment_ready',
            'resource_config': {}
        }
        _ctx = self.get_mock_ctx(test_name,
                                 test_properties)
        current_ctx.set(_ctx)
        mock_state = 'terminated'
        mock_timeout = .01

        # Test that wait_for_deployment_ready.. Fails if not succussessful.
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
            error = self.assertRaises(NonRecoverableError,
                                      wait_for_deployment_ready,
                                      mock_state,
                                      mock_timeout)
            self.assertIn('is not callable', error.message)

    def test_query_deployment_data(self):
        from ..tasks import query_deployment_data

        deployment_outputs_expected = 0
        deployment_outputs_mapping = '_zero'

        test_name = 'test_query_deployment_data'
        test_properties = {
            'resource_id': 'test_query_deployment_data',
            'resource_config': {
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
            _mock_list = mock.MagicMock(side_effect=CloudifyClientError('Mistake'))
            mock_deployments = mock.MagicMock
            setattr(mock_client, 'deployments', mock_deployments)
            setattr(mock_deployments, 'get', _mock_list)
            output = query_deployment_data(mock_daemonize, mock_interval, mock_timeout)
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
            output = query_deployment_data(mock_daemonize, mock_interval, mock_timeout)
            self.assertEqual(True, output)
            self.assertEqual(
                _ctx.instance.runtime_properties[deployment_outputs_mapping],
                deployment_outputs_expected)
