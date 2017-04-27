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

from cloudify_deployment_proxy.tasks import EXT_RES

import mock
import testtools

from cloudify.mocks import MockCloudifyContext
from cloudify.state import current_ctx
from cloudify.exceptions import NonRecoverableError

from .constants import (
    deployment_proxy_properties,
    EXECUTIONS_MOCK,
    EXECUTIONS_CREATE,
    DEPLOYMENTS_MOCK,
    DEPLOYMENTS_DELETE,
    DEPLOYMENTS_CREATE,
    DEPLOYMENTS_OUTPUTS,
    DEPLOYMENTS_OUTPUTS_GET,
    DEPLOYMENTS_LIST,
    BLUEPRINTS_MOCK,
    BLUEPRINTS_LIST,
    BLUEPRINTS_UPLOAD,
    REST_CLIENT_EXCEPTION
)


class TestDeploymentProxy(testtools.TestCase):

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
        _ctx.instance.runtime_properties[EXT_RES] = False
        _ctx.instance.runtime_properties['deployment'] = {}

        # Tests that execute start fails on rest client error
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            setattr(EXECUTIONS_MOCK, 'start', REST_CLIENT_EXCEPTION)
            setattr(mock_client, 'executions', EXECUTIONS_MOCK)
            error = self.assertRaises(NonRecoverableError,
                                      execute_start,
                                      deployment_id='test_execute_start',
                                      workflow_id='install')
            self.assertIn('action start failed',
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
        _ctx.instance.runtime_properties[EXT_RES] = False
        # Tests that deployments delete fails on rest client error
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            setattr(DEPLOYMENTS_MOCK, 'delete', REST_CLIENT_EXCEPTION)
            setattr(mock_client, 'deployments', DEPLOYMENTS_MOCK)
            error = self.assertRaises(NonRecoverableError,
                                      delete_deployment,
                                      deployment_id='test_deployments_delete',
                                      timeout=.01)
            self.assertIn('action delete failed',
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

        # Tests that deployments delete checks all_deps_by_id
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
        _ctx.instance.runtime_properties['deployment']['outputs'] = {}

        # Tests that deployments create fails on rest client error
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            setattr(DEPLOYMENTS_MOCK, 'create', REST_CLIENT_EXCEPTION)
            setattr(mock_client, 'deployments', DEPLOYMENTS_MOCK)
            error = self.assertRaises(NonRecoverableError,
                                      create_deployment,
                                      deployment_id='test_deployments_create',
                                      blueprint_id='test_deployments_create',
                                      timeout=.01)
            self.assertIn('action create failed',
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
                self.assertIn('Execution not finished. Timeout',
                              error.message)

        # Tests that deployments create succeeds
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            setattr(DEPLOYMENTS_OUTPUTS, 'get', DEPLOYMENTS_OUTPUTS_GET)
            setattr(DEPLOYMENTS_MOCK, 'outputs', DEPLOYMENTS_OUTPUTS)
            setattr(DEPLOYMENTS_MOCK, 'create', DEPLOYMENTS_CREATE)
            setattr(mock_client, 'deployments', DEPLOYMENTS_MOCK)
            poll_with_timeout_test = \
                'cloudify_deployment_proxy.tasks.poll_with_timeout'
            with mock.patch(poll_with_timeout_test) as poll:
                poll.return_value = True
                output = create_deployment(timeout=.01)
                self.assertTrue(output)

    def test_upload_blueprint(self):
        from cloudify_deployment_proxy.tasks import upload_blueprint

        test_name = 'test_upload_blueprint'
        _ctx = self.get_mock_ctx(test_name,
                                 deployment_proxy_properties)
        current_ctx.set(_ctx)

        # Tests that blueprints upload fails on rest client error
        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            setattr(BLUEPRINTS_MOCK, '_upload', REST_CLIENT_EXCEPTION)
            setattr(BLUEPRINTS_MOCK, 'list', BLUEPRINTS_LIST)
            setattr(mock_client, 'blueprints', BLUEPRINTS_MOCK)
            error = self.assertRaises(NonRecoverableError,
                                      upload_blueprint,
                                      blueprint_id='test_upload_blueprint')
            self.assertIn('_upload failed',
                          error.message)

        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            setattr(BLUEPRINTS_MOCK, '_upload', BLUEPRINTS_UPLOAD)
            setattr(mock_client, 'blueprints', BLUEPRINTS_MOCK)
            output = upload_blueprint(blueprint_id='test_upload_blueprint')
            self.assertTrue(output)

    def test_poll_with_timeout(self):
        from cloudify_deployment_proxy.tasks import poll_with_timeout

        test_name = 'test_poll_with_timeout'
        test_properties = {
            'resource_config': {
                'deployment': {
                    'id': test_name,
                }
            }
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
