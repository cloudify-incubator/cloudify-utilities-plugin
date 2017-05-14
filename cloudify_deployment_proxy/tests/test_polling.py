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

from cloudify.state import current_ctx
from cloudify.exceptions import NonRecoverableError
from cloudify_rest_client.exceptions import CloudifyClientError

from .base import DeploymentProxyTestBase
from .client_mock import MockCloudifyRestClient
from ..polling import (
    any_bp_by_id,
    any_dep_by_id,
    all_deps_by_id,
    resource_by_id,
    poll_with_timeout,
    dep_workflow_in_state_pollster,
    poll_workflow_after_execute)


class TestPolling(DeploymentProxyTestBase):

    # test that any bp by id returns false if there are no matching
    def test_any_bp_by_id_no_blueprint(self):
        test_name = 'test_any_bp_by_id_no_blueprint'
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            cfy_mock_client = MockCloudifyRestClient()
            mock_client.return_value = cfy_mock_client
            output = any_bp_by_id(mock_client, test_name)
            self.assertFalse(output)

    # test that any bp by id returns True if there are matching
    def test_any_bp_by_id_with_blueprint(self):
        test_name = 'test_any_bp_by_id_with_blueprint'
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            cfy_mock_client = MockCloudifyRestClient()
            list_response = cfy_mock_client.blueprints.list()
            list_response[0]['id'] = test_name

            def mock_return(*args, **kwargs):
                del args, kwargs
                return list_response

            cfy_mock_client.blueprints.list = mock_return
            mock_client.return_value = cfy_mock_client
            output = any_bp_by_id(cfy_mock_client, test_name)
            self.assertTrue(output)

    # test that any dep by id returns false if there are no matching
    def test_any_dep_by_id_no_deployment(self):
        test_name = 'test_any_dep_by_id_no_deployment'
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            cfy_mock_client = MockCloudifyRestClient()
            mock_client.return_value = cfy_mock_client
            output = any_dep_by_id(mock_client, test_name)
            self.assertFalse(output)

    # test that any dep by id returns True if there are matching
    def test_any_dep_by_id_with_deployment(self):
        test_name = 'test_any_dep_by_id_with_deployment'
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            cfy_mock_client = MockCloudifyRestClient()
            list_response = cfy_mock_client.deployments.list()
            list_response[0]['id'] = test_name

            def mock_return(*args, **kwargs):
                del args, kwargs
                return list_response

            cfy_mock_client.deployments.list = mock_return
            mock_client.return_value = cfy_mock_client
            output = any_dep_by_id(cfy_mock_client, test_name)
            self.assertTrue(output)

    # test that all dep by id returns False if there are not
    def test_all_deps_by_id_no_deployment(self):
        test_name = 'test_any_dep_by_id_no_deployment'
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            cfy_mock_client = MockCloudifyRestClient()
            mock_client.return_value = cfy_mock_client
            output = all_deps_by_id(mock_client, test_name)
            self.assertFalse(output)

    # test that all dep by id returns True if there are matching
    def test_all_deps_by_id_with_deployment(self):
        test_name = 'test_any_dep_by_id_with_deployment'
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            cfy_mock_client = MockCloudifyRestClient()
            list_response = cfy_mock_client.deployments.list()
            list_response[0]['id'] = test_name

            def mock_return(*args, **kwargs):
                del args, kwargs
                return list_response

            cfy_mock_client.deployments.list = mock_return
            mock_client.return_value = cfy_mock_client
            output = all_deps_by_id(cfy_mock_client, test_name)
            self.assertTrue(output)

    # test that resource_by_id raises when it catches an exception
    def test_resource_by_id_client_error(self):
        test_name = 'test_resource_by_id_client_error'

        def mock_return(*args, **kwargs):
            del args, kwargs
            raise CloudifyClientError('Mistake')

        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            cfy_mock_client = MockCloudifyRestClient()
            cfy_mock_client.deployments.list = mock_return
            mock_client.return_value = mock_return
            output = \
                self.assertRaises(
                    NonRecoverableError,
                    resource_by_id,
                    cfy_mock_client,
                    test_name,
                    'deployments')
            self.assertIn('failed', output.message)

    # Test that failed polling raises an error
    def test_poll_with_timeout_timeout(self):
        test_name = 'test_poll_with_timeout'
        _ctx = self.get_mock_ctx(test_name)
        current_ctx.set(_ctx)

        mock_timeout = .001
        mock_interval = .001

        mock_pollster = mock.MagicMock
        output = \
            poll_with_timeout(
                mock_pollster,
                mock_timeout,
                mock_interval)
        self.assertFalse(output)

    # Test that failed polling raises an error
    def test_poll_with_timeout_expected(self):
        test_name = 'test_poll_with_timeout_expected'
        _ctx = self.get_mock_ctx(test_name)
        current_ctx.set(_ctx)

        mock_timeout = .001
        mock_interval = .001

        def mock_return(*args, **kwargs):
            del args, kwargs
            return True

        output = \
            poll_with_timeout(
                mock_return,
                mock_timeout,
                mock_interval,
                {},
                True)
        self.assertTrue(output)

    # Test that no matching executions returns False
    def test_dep_workflow_in_state_pollster_no_executions(self):
        test_name = 'test_dep_workflow_in_state_pollster_no_executions'
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            cfy_mock_client = MockCloudifyRestClient()
            list_response = cfy_mock_client.deployments.list()
            list_response[0]['id'] = test_name

            mock_client.return_value = cfy_mock_client
            output = \
                dep_workflow_in_state_pollster(
                    cfy_mock_client,
                    test_name,
                    'terminated',
                    0)
            self.assertFalse(output)

    # Test that matching executions returns True
    def test_dep_workflow_in_state_pollster_matching_executions(self):
        test_name = 'test_dep_workflow_in_state_pollster_matching_executions'
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            cfy_mock_client = MockCloudifyRestClient()
            list_response = cfy_mock_client.blueprints.list()
            list_response[0]['id'] = test_name
            list_response[0]['status'] = 'terminated'

            def mock_return(*args, **kwargs):
                del args, kwargs
                return list_response

            cfy_mock_client.executions.list = mock_return
            mock_client.return_value = cfy_mock_client
            output = \
                dep_workflow_in_state_pollster(
                    cfy_mock_client,
                    test_name,
                    'terminated',
                    0)
            self.assertTrue(output)

    # Test that matching executions returns True
    def test_dep_workflow_in_state_pollster_matching_state(self):
        test_name = 'test_dep_workflow_in_state_pollster_matching_executions'
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            cfy_mock_client = MockCloudifyRestClient()
            list_response = cfy_mock_client.blueprints.list()
            list_response[0]['status'] = 'terminated'
            list_response[0]['workflow_id'] = 'workflow_id1'

            def mock_return(*args, **kwargs):
                del args, kwargs
                return list_response

            cfy_mock_client.executions.list = mock_return
            mock_client.return_value = cfy_mock_client
            output = \
                dep_workflow_in_state_pollster(
                    cfy_mock_client,
                    test_name,
                    _state='terminated',
                    _workflow_id='workflow_id0')
            self.assertFalse(output)

    # test that raises Exception is handled.
    def test_dep_workflow_in_state_pollster_raises(self):
        test_name = 'test_dep_workflow_in_state_pollster_raises'
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            cfy_mock_client = MockCloudifyRestClient()
            list_response = cfy_mock_client.blueprints.list()
            list_response[0]['id'] = test_name

            def mock_return(*args, **kwargs):
                del args, kwargs
                raise CloudifyClientError('Mistake')

            cfy_mock_client.executions.list = mock_return
            mock_client.return_value = cfy_mock_client
            output = \
                self.assertRaises(
                    NonRecoverableError,
                    dep_workflow_in_state_pollster,
                    cfy_mock_client,
                    test_name,
                    'terminated',
                    0)
            self.assertIn('failed', output.message)

    # test that success=False raises exception
    def test_poll_workflow_after_execute_failed(self):
        with mock.patch(
                'cloudify_deployment_proxy.polling.poll_with_timeout') \
                as mocked_fn:
            mocked_fn.return_value = False
            output = \
                self.assertRaises(
                    NonRecoverableError,
                    poll_workflow_after_execute,
                    None, None, None, None, None, None)
            self.assertIn('Execution timeout', output.message)

    # test that success=True returns True
    def test_poll_workflow_after_execute_success(self):
        with mock.patch(
                'cloudify_deployment_proxy.polling.poll_with_timeout') \
                as mocked_fn:
            mocked_fn.return_value = True
            output = \
                poll_workflow_after_execute(
                    None, None, None, None, None, None)
            self.assertTrue(output)
