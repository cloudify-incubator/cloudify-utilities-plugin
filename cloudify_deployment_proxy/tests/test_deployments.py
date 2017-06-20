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
from ..tasks import create_deployment, delete_deployment

REST_CLIENT_EXCEPTION = \
    mock.MagicMock(side_effect=CloudifyClientError('Mistake'))


class TestDeployment(DeploymentProxyTestBase):

    sleep_mock = None

    def setUp(self):
        super(TestDeployment, self).setUp()
        mock_sleep = mock.MagicMock()
        self.sleep_mock = mock.patch('time.sleep', mock_sleep)
        self.sleep_mock.start()

    def tearDown(self):
        if self.sleep_mock:
            self.sleep_mock.stop()
            self.sleep_mock = None
        super(TestDeployment, self).tearDown()

    def test_delete_deployment_rest_client_error(self):

        test_name = 'test_delete_deployment_rest_client_error'
        _ctx = self.get_mock_ctx(test_name)
        current_ctx.set(_ctx)

        _ctx.instance.runtime_properties['deployment'] = {}
        _ctx.instance.runtime_properties['deployment']['id'] = test_name
        # Tests that deployments delete fails on rest client error
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            cfy_mock_client = MockCloudifyRestClient()
            cfy_mock_client.deployments.delete = REST_CLIENT_EXCEPTION
            mock_client.return_value = cfy_mock_client
            error = self.assertRaises(NonRecoverableError,
                                      delete_deployment,
                                      deployment_id=test_name,
                                      timeout=.01)
            self.assertIn('action delete failed',
                          error.message)

    def test_delete_deployment_success(self):
        # Tests that deployments delete succeeds

        test_name = 'test_delete_deployment_success'
        _ctx = self.get_mock_ctx(test_name)
        current_ctx.set(_ctx)

        current_ctx.set(_ctx)
        _ctx.instance.runtime_properties['deployment'] = {}
        _ctx.instance.runtime_properties['deployment']['id'] = test_name
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            mock_client.return_value = MockCloudifyRestClient()
            poll_with_timeout_test = \
                'cloudify_deployment_proxy.polling.poll_with_timeout'
            with mock.patch(poll_with_timeout_test) as poll:
                poll.return_value = True
                output = delete_deployment(
                    deployment_id='test_deployments_delete',
                    timeout=.001)
                self.assertTrue(output)

    def test_delete_deployment_any_dep_by_id(self):
        # Tests that deployments runs any_dep_by_id

        test_name = 'test_delete_deployment_any_dep_by_id'
        _ctx = self.get_mock_ctx(test_name)
        current_ctx.set(_ctx)

        current_ctx.set(_ctx)
        _ctx.instance.runtime_properties['deployment'] = {}
        _ctx.instance.runtime_properties['deployment']['id'] = test_name
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            mock_client.return_value = MockCloudifyRestClient()
            _ctx.instance.runtime_properties['deployment'] = {}
            _ctx.instance.runtime_properties['deployment']['id'] = test_name
            output = delete_deployment(deployment_id='test_deployments_delete',
                                       timeout=.01)
            self.assertTrue(output)

    def test_create_deployment_rest_client_error(self):
        # Tests that deployments create fails on rest client error

        test_name = 'test_create_deployment_rest_client_error'
        _ctx = self.get_mock_ctx(test_name)
        current_ctx.set(_ctx)
        _ctx.instance.runtime_properties['deployment'] = {}
        _ctx.instance.runtime_properties['deployment']['id'] = test_name
        _ctx.instance.runtime_properties['deployment']['outputs'] = {}

        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            cfy_mock_client = MockCloudifyRestClient()
            cfy_mock_client.deployments.create = REST_CLIENT_EXCEPTION
            mock_client.return_value = cfy_mock_client
            error = self.assertRaises(NonRecoverableError,
                                      create_deployment,
                                      deployment_id='test_deployments_create',
                                      blueprint_id='test_deployments_create',
                                      timeout=.01)
            self.assertIn('action create failed',
                          error.message)

    def test_create_deployment_timeout(self):
        # Tests that deployments create fails on timeout

        test_name = 'test_create_deployment_timeout'
        _ctx = self.get_mock_ctx(test_name)
        current_ctx.set(_ctx)
        _ctx.instance.runtime_properties['deployment'] = {}
        _ctx.instance.runtime_properties['deployment']['id'] = test_name
        _ctx.instance.runtime_properties['deployment']['outputs'] = {}
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            mock_client.return_value = MockCloudifyRestClient()
            poll_with_timeout_test = \
                'cloudify_deployment_proxy.polling.poll_with_timeout'
            with mock.patch(poll_with_timeout_test) as poll:
                poll.return_value = False
                error = self.assertRaises(NonRecoverableError,
                                          create_deployment,
                                          deployment_id='test',
                                          blueprint_id='test',
                                          timeout=.01)
                self.assertIn('Execution timeout',
                              error.message)

    def test_create_deployment_success(self):
        # Tests that create deployment succeeds

        test_name = 'test_create_deployment_success'
        _ctx = self.get_mock_ctx(test_name)
        current_ctx.set(_ctx)
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            mock_client.return_value = MockCloudifyRestClient()
            poll_with_timeout_test = \
                'cloudify_deployment_proxy.polling.poll_with_timeout'
            with mock.patch(poll_with_timeout_test) as poll:
                poll.return_value = True
                output = create_deployment(timeout=.01)
                self.assertTrue(output)

    def test_create_deployment_exists(self):
        # Tests that create deployment exists

        test_name = 'test_create_deployment_exists'
        _ctx = self.get_mock_ctx(test_name)
        current_ctx.set(_ctx)
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            cfy_mock_client = MockCloudifyRestClient()
            list_response = cfy_mock_client.deployments.list()
            list_response[0]['id'] = test_name

            def mock_return(*args, **kwargs):
                del args, kwargs
                return list_response

            cfy_mock_client.deployments.list = mock_return
            mock_client.return_value = cfy_mock_client
            output = create_deployment(timeout=.01)
            self.assertFalse(output)
