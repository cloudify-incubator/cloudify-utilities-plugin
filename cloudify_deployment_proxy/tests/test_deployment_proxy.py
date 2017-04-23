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
from cloudify.exceptions import NonRecoverableError

from .constants import (
    deployment_proxy_properties,
    EXECUTIONS_MOCK,
    EXECUTIONS_CREATE,
    EXECUTIONS_LIST,
    DEPLOYMENTS_MOCK,
    DEPLOYMENTS_DELETE,
    DEPLOYMENTS_CREATE,
    DEPLOYMENTS_LIST,
    BLUEPRINTS_MOCK,
    BLUEPRINTS_UPLOAD,
    REST_CLIENT_EXCEPTION
)


class TestDeploymentProxyUnitTests(testtools.TestCase):

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

    def test_execute_start(self):
        from cloudify_deployment_proxy.tasks import execute_start

        test_name = 'test_execute_start'
        _ctx = self.get_mock_ctx(test_name,
                                 deployment_proxy_properties)
        current_ctx.set(_ctx)

        # Tests that execute start fails on rest client error
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            setattr(EXECUTIONS_MOCK, 'start', REST_CLIENT_EXCEPTION)
            setattr(mock_client, 'executions', EXECUTIONS_MOCK)
            error = self.assertRaises(NonRecoverableError,
                                      execute_start,
                                      deployment_id='test_execute_start',
                                      workflow_id='install')
            self.assertIn('Executions start failed',
                          error.message)

        # Tests that execute start fails on timeout
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            setattr(EXECUTIONS_MOCK, 'start', EXECUTIONS_CREATE)
            setattr(mock_client, 'executions', EXECUTIONS_MOCK)
            poll_with_timeout_test = \
                'cloudify_deployment_proxy.tasks.poll_with_timeout'
            with mock.patch(poll_with_timeout_test) as poll:
                poll.return_value = False
                error = self.assertRaises(NonRecoverableError,
                                          execute_start,
                                          deployment_id='test_execute_start',
                                          workflow_id='install',
                                          timeout=.01)
                self.assertIn(
                    'Execution not finished. Timeout',
                    error.message)

        # Tests that execute start succeeds
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            setattr(EXECUTIONS_MOCK, 'start', EXECUTIONS_CREATE)
            setattr(mock_client, 'executions', EXECUTIONS_MOCK)
            poll_with_timeout_test = \
                'cloudify_deployment_proxy.tasks.poll_with_timeout'
            with mock.patch(poll_with_timeout_test) as poll:
                poll.return_value = True
                output = execute_start(deployment_id='test_execute_start',
                                       workflow_id='install',
                                       timeout=.01)
                self.assertTrue(output)

    def test_deployments_delete(self):
        from cloudify_deployment_proxy.tasks import delete_deployment

        test_name = 'test_deployments_delete'
        _ctx = self.get_mock_ctx(test_name,
                                 deployment_proxy_properties)
        current_ctx.set(_ctx)
        _ctx.instance.runtime_properties['deployment'] = {}
        _ctx.instance.runtime_properties['deployment']['id'] = test_name

        # Tests that deployments delete fails on rest client error
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            setattr(DEPLOYMENTS_MOCK, 'delete', REST_CLIENT_EXCEPTION)
            setattr(mock_client, 'deployments', DEPLOYMENTS_MOCK)
            error = self.assertRaises(NonRecoverableError,
                                      delete_deployment,
                                      deployment_id='test_deployments_delete',
                                      timeout=.01)
            self.assertIn('Deployment delete failed',
                          error.message)

        # Tests that deployments delete fails on timeout
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            setattr(DEPLOYMENTS_MOCK, 'delete', DEPLOYMENTS_DELETE)
            setattr(mock_client, 'deployments', DEPLOYMENTS_MOCK)
            poll_with_timeout_test = \
                'cloudify_deployment_proxy.tasks.poll_with_timeout'
            with mock.patch(poll_with_timeout_test) as poll:
                poll.return_value = False
                error = self.assertRaises(NonRecoverableError,
                                          delete_deployment,
                                          deployment_id='test',
                                          timeout=.01)
                self.assertIn(
                    'Deployment not deleted. Timeout',
                    error.message)

        # Tests that deployments delete succeeds
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            setattr(DEPLOYMENTS_MOCK, 'delete', DEPLOYMENTS_DELETE)
            setattr(mock_client, 'deployments', DEPLOYMENTS_MOCK)
            poll_with_timeout_test = \
                'cloudify_deployment_proxy.tasks.poll_with_timeout'
            with mock.patch(poll_with_timeout_test) as poll:
                poll.return_value = True
                output = delete_deployment(
                    deployment_id='test_deployments_delete',
                    timeout=.01)
                self.assertTrue(output)

        # Tests that deployments delete checks all_deps_pollster
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            setattr(DEPLOYMENTS_MOCK, 'delete', DEPLOYMENTS_DELETE)
            setattr(DEPLOYMENTS_MOCK, 'list', DEPLOYMENTS_LIST)
            setattr(mock_client, 'deployments', DEPLOYMENTS_MOCK)
            _ctx.instance.runtime_properties['deployment'] = {}
            _ctx.instance.runtime_properties['deployment']['id'] = test_name
            output = delete_deployment(deployment_id='test_deployments_delete',
                                       timeout=.01)
            self.assertTrue(output)

    def test_deployments_create(self):
        from cloudify_deployment_proxy.tasks import create_deployment

        test_name = 'test_deployments_create'
        _ctx = self.get_mock_ctx(test_name,
                                 deployment_proxy_properties)
        current_ctx.set(_ctx)
        _ctx.instance.runtime_properties['deployment'] = {}
        _ctx.instance.runtime_properties['deployment']['id'] = test_name

        # Tests that deployments create fails on rest client error
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            setattr(DEPLOYMENTS_MOCK, 'create', REST_CLIENT_EXCEPTION)
            setattr(mock_client, 'deployments', DEPLOYMENTS_MOCK)
            error = self.assertRaises(NonRecoverableError,
                                      create_deployment,
                                      deployment_id='test_deployments_create',
                                      blueprint_id='test_deployments_create',
                                      timeout=.01)
            self.assertIn('Deployment create failed',
                          error.message)

        # Tests that deployments create fails on timeout
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            setattr(DEPLOYMENTS_MOCK, 'create', DEPLOYMENTS_CREATE)
            setattr(mock_client, 'deployments', DEPLOYMENTS_MOCK)
            poll_with_timeout_test = \
                'cloudify_deployment_proxy.tasks.poll_with_timeout'
            with mock.patch(poll_with_timeout_test) as poll:
                poll.return_value = False
                error = self.assertRaises(NonRecoverableError,
                                          create_deployment,
                                          deployment_id='test',
                                          blueprint_id='test',
                                          timeout=.01)
                self.assertIn('Deployment not ready. Timeout',
                              error.message)

        # Tests that deployments create succeeds
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            setattr(DEPLOYMENTS_MOCK, 'create', DEPLOYMENTS_CREATE)
            setattr(mock_client, 'deployments', DEPLOYMENTS_MOCK)
            poll_with_timeout_test = \
                'cloudify_deployment_proxy.tasks.poll_with_timeout'
            with mock.patch(poll_with_timeout_test) as poll:
                poll.return_value = True
                output = create_deployment(deployment_id='test',
                                           blueprint_id='test',
                                           timeout=.01)
                self.assertTrue(output)

        # Tests that deployments create checks poll_workflow_after_execute
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            setattr(DEPLOYMENTS_MOCK, 'create', DEPLOYMENTS_CREATE)
            setattr(mock_client, 'deployments', DEPLOYMENTS_MOCK)
            setattr(mock_client, 'executions', EXECUTIONS_MOCK)
            setattr(mock_client, 'list', EXECUTIONS_LIST)
            poll_with_timeout_test = \
                'cloudify_deployment_proxy.tasks.all_deps_pollster'
            with mock.patch(poll_with_timeout_test) as poll:
                poll.return_value = EXECUTIONS_LIST
                error = self.assertRaises(NonRecoverableError,
                                          create_deployment,
                                          deployment_id='test',
                                          blueprint_id='test',
                                          timeout=.01,
                                          interval=.01)
                self.assertIn('Deployment not ready. Timeout',
                              error.message)

    def test_upload_blueprint(self):
        from cloudify_deployment_proxy.tasks import upload_blueprint

        test_name = 'test_upload_blueprint'
        _ctx = self.get_mock_ctx(test_name,
                                 deployment_proxy_properties)
        current_ctx.set(_ctx)

        # Tests that blueprints upload fails on rest client error
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            setattr(BLUEPRINTS_MOCK, '_upload', REST_CLIENT_EXCEPTION)
            setattr(mock_client, 'blueprints', BLUEPRINTS_MOCK)
            error = self.assertRaises(NonRecoverableError,
                                      upload_blueprint,
                                      blueprint_id='test_upload_blueprint')
            self.assertIn('Blueprint failed',
                          error.message)

        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            setattr(BLUEPRINTS_MOCK, '_upload', BLUEPRINTS_UPLOAD)
            setattr(mock_client, 'blueprints', BLUEPRINTS_MOCK)
            output = upload_blueprint(blueprint_id='test_upload_blueprint')
            self.assertTrue(output)

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

        # Tests that mock_daemonize True raises error
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            mock_daemonize = True
            error = self.assertRaises(NonRecoverableError,
                                      query_deployment_data,
                                      mock_daemonize,
                                      mock_interval,
                                      mock_timeout)
            self.assertIn('Option "daemonize" is not implemented',
                          error.message)

    def test_wait_for_deployment_ready(self):
        from cloudify_deployment_proxy.tasks import wait_for_deployment_ready

        test_name = 'test_wait_for_deployment_ready'
        test_properties = deployment_proxy_properties
        test_properties['resource_config']['deployment_id'] = test_name
        _ctx = self.get_mock_ctx(test_name,
                                 test_properties)
        current_ctx.set(_ctx)
        state = 'string'
        timeout = .01

        # Test that wait_for fails
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            setattr(EXECUTIONS_MOCK, 'list', EXECUTIONS_LIST)
            setattr(mock_client, 'executions', EXECUTIONS_MOCK)
            poll_with_timeout_test = \
                'cloudify_deployment_proxy.tasks.poll_with_timeout'
            with mock.patch(poll_with_timeout_test) as poll:
                poll.return_value = False
                error = self.assertRaises(NonRecoverableError,
                                          wait_for_deployment_ready,
                                          state=state, timeout=timeout)
                self.assertIn('Deployment not ready. Timeout', error.message)

        # Test that wait_for succeeds
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            setattr(EXECUTIONS_MOCK, 'list', EXECUTIONS_LIST)
            setattr(mock_client, 'executions', EXECUTIONS_MOCK)
            poll_with_timeout_test = \
                'cloudify_deployment_proxy.tasks.poll_with_timeout'
            with mock.patch(poll_with_timeout_test) as poll:
                poll.return_value = True
                output = wait_for_deployment_ready(state=state,
                                                   timeout=timeout)
                self.assertTrue(output)

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
