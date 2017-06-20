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

from .client_mock import MockCloudifyRestClient
from .base import DeploymentProxyTestBase
from ..tasks import execute_start
from ..constants import EXTERNAL_RESOURCE, NIP_TYPE, DEP_TYPE

REST_CLIENT_EXCEPTION = \
    mock.MagicMock(side_effect=CloudifyClientError('Mistake'))


class TestExecute(DeploymentProxyTestBase):

    sleep_mock = None

    def setUp(self):
        super(TestExecute, self).setUp()
        mock_sleep = mock.MagicMock()
        self.sleep_mock = mock.patch('time.sleep', mock_sleep)
        self.sleep_mock.start()

    def tearDown(self):
        if self.sleep_mock:
            self.sleep_mock.stop()
            self.sleep_mock = None
        super(TestExecute, self).tearDown()

    def test_execute_start_rest_client_error(self):
        # Tests that execute start fails on rest client error

        test_name = 'test_execute_start_rest_client_error'
        _ctx = self.get_mock_ctx(test_name)
        current_ctx.set(_ctx)
        _ctx.instance.runtime_properties['deployment'] = {}

        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            cfy_mock_client = MockCloudifyRestClient()
            cfy_mock_client.executions.start = REST_CLIENT_EXCEPTION
            mock_client.return_value = cfy_mock_client
            error = self.assertRaises(NonRecoverableError,
                                      execute_start,
                                      deployment_id=test_name,
                                      workflow_id='install')
            self.assertIn('action start failed',
                          error.message)

    def test_execute_start_timeout(self):
        # Tests that execute start fails on timeout

        test_name = 'test_execute_start_timeout'
        _ctx = self.get_mock_ctx(test_name)
        current_ctx.set(_ctx)
        _ctx.instance.runtime_properties['deployment'] = {}

        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            mock_client.return_value = MockCloudifyRestClient()
            poll_with_timeout_test = \
                'cloudify_deployment_proxy.polling.poll_with_timeout'
            with mock.patch(poll_with_timeout_test) as poll:
                poll.return_value = False
                error = self.assertRaises(NonRecoverableError,
                                          execute_start,
                                          deployment_id=test_name,
                                          workflow_id='install',
                                          timeout=.001)
                self.assertIn(
                    'Execution timeout',
                    error.message)

    def test_execute_start_succeeds(self):
        # Tests that execute start succeeds

        test_name = 'test_execute_start_succeeds'
        _ctx = self.get_mock_ctx(test_name)
        current_ctx.set(_ctx)
        _ctx.instance.runtime_properties['deployment'] = {}

        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            mock_client.return_value = MockCloudifyRestClient()
            poll_with_timeout_test = \
                'cloudify_deployment_proxy.polling.poll_with_timeout'
            with mock.patch(poll_with_timeout_test) as poll:
                poll.return_value = True
                output = execute_start(deployment_id=test_name,
                                       workflow_id='install',
                                       timeout=.001)
                self.assertTrue(output)

    def test_execute_deployment_not_ready(self):
        # Tests that execute start succeeds

        test_name = 'test_execute_deployment_not_ready'
        _ctx = self.get_mock_ctx(test_name)
        current_ctx.set(_ctx)
        _ctx.instance.runtime_properties['deployment'] = {}
        _ctx.instance.runtime_properties['resource_config'] = {
            'deployment': {
                EXTERNAL_RESOURCE: True
            }
        }
        _ctx.instance.runtime_properties['reexecute'] = True

        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            cfy_mock_client = MockCloudifyRestClient()

            list_response = cfy_mock_client.deployments.list()
            list_response[0]['id'] = test_name
            list_response[0]['is_system_workflow'] = False
            list_response[0]['status'] = 'started'
            list_response[0]['deployment_id'] = test_name

            def mock_return(*args, **kwargs):
                del args, kwargs
                return list_response

            cfy_mock_client.executions.list = mock_return

            mock_client.return_value = cfy_mock_client

            output = execute_start(deployment_id=test_name,
                                   workflow_id='install',
                                   timeout=.001)
            self.assertIsNone(output)

    def test_execute_start_succeeds_not_finished(self):
        # Tests that execute start succeeds

        test_name = 'test_execute_start_succeeds_not_finished'
        _ctx = self.get_mock_ctx(test_name)
        current_ctx.set(_ctx)
        _ctx.instance.runtime_properties['deployment'] = {}

        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            mock_client.return_value = MockCloudifyRestClient()
            poll_with_timeout_test = \
                'cloudify_deployment_proxy.DeploymentProxyBase.' \
                'verify_execution_successful'
            with mock.patch(poll_with_timeout_test) as poll:
                poll.return_value = False
                output = execute_start(deployment_id=test_name,
                                       workflow_id='install',
                                       timeout=.001)
                self.assertTrue(output)

    def test_execute_start_succeeds_node_instance_proxy(self):
        # Tests that execute start succeeds

        test_name = 'test_execute_start_succeeds_node_instance_proxy'
        _ctx = self.get_mock_ctx(test_name)
        current_ctx.set(_ctx)
        _ctx.node.type = NIP_TYPE
        ni = {}
        _ctx.node.properties['resource_config']['node_instance'] = ni
        _ctx.instance.runtime_properties['deployment'] = {}

        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            mock_client.return_value = MockCloudifyRestClient()
            poll_with_timeout_test = \
                'cloudify_deployment_proxy.polling.poll_with_timeout'
            with mock.patch(poll_with_timeout_test) as poll:
                poll.return_value = True
                output = execute_start(deployment_id=test_name,
                                       workflow_id='install',
                                       timeout=.001)
                self.assertTrue(output)

    def test_execute_start_succeeds_weird_node_type(self):
        # Tests that execute start succeeds

        test_name = 'test_execute_start_succeeds_weird_node_type'
        _ctx = self.get_mock_ctx(test_name)
        current_ctx.set(_ctx)
        _ctx.node.type = 'cloudify.nodes.WeirdNodeType'
        _ctx.instance.runtime_properties['deployment'] = {}

        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            mock_client.return_value = MockCloudifyRestClient()
            poll_with_timeout_test = \
                'cloudify_deployment_proxy.polling.poll_with_timeout'
            with mock.patch(poll_with_timeout_test) as poll:
                poll.return_value = True
                output = execute_start(deployment_id=test_name,
                                       workflow_id='install',
                                       timeout=.001)
                self.assertFalse(output)

    def test_post_execute_client_error(self):
        # Tests that execute client error ignored

        test_name = 'test_post_execute_client_error'
        _ctx = self.get_mock_ctx(test_name)
        _ctx.node.type = DEP_TYPE
        current_ctx.set(_ctx)
        _ctx.instance.runtime_properties['deployment'] = dict()

        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            mock_client.return_value = None

            cfy_mock_client = MockCloudifyRestClient()

            def mock_return(*args, **kwargs):
                raise CloudifyClientError('Mistake')

            cfy_mock_client.deployments.outputs.get = mock_return
            poll_with_timeout_test = \
                'cloudify_deployment_proxy.DeploymentProxyBase.' \
                'verify_execution_successful'

            with mock.patch(
                'cloudify_deployment_proxy.CloudifyClient'
            ) as mock_local_client:
                mock_local_client.return_value = cfy_mock_client

                with mock.patch(poll_with_timeout_test) as poll:
                    poll.return_value = False
                    output = execute_start(deployment_id=test_name,
                                           workflow_id='install',
                                           client={'host': 'localhost'},
                                           timeout=.001)
                self.assertTrue(output)

    def test_execute_start_succeeds_node_instance_proxy_matches(self):
        # Tests that execute start succeeds

        test_name = 'test_execute_start_succeeds_node_instance_proxy'
        _ctx = self.get_mock_ctx(test_name)
        current_ctx.set(_ctx)
        _ctx.node.type = NIP_TYPE
        ni = {'id': test_name}
        _ctx.node.properties['resource_config']['node_instance'] = ni
        _ctx.instance.runtime_properties['deployment'] = {}

        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            mock_client.return_value = MockCloudifyRestClient()
            poll_with_timeout_test = \
                'cloudify_deployment_proxy.polling.poll_with_timeout'
            with mock.patch(poll_with_timeout_test) as poll:
                poll.return_value = True
                output = execute_start(deployment_id=test_name,
                                       workflow_id='install',
                                       timeout=.001)
                self.assertTrue(output)
