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
from ..tasks import upload_blueprint
from ..constants import EXTERNAL_RESOURCE

REST_CLIENT_EXCEPTION = \
    mock.MagicMock(side_effect=CloudifyClientError('Mistake'))


class TestBlueprint(DeploymentProxyTestBase):

    def test_upload_blueprint_rest_client_error(self):
        # Tests that upload blueprint fails on rest client error

        test_name = 'test_upload_blueprint_rest_client_error'
        _ctx = self.get_mock_ctx(test_name)
        current_ctx.set(_ctx)

        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            cfy_mock_client = MockCloudifyRestClient()
            cfy_mock_client.blueprints._upload = REST_CLIENT_EXCEPTION
            mock_client.return_value = cfy_mock_client
            error = self.assertRaises(NonRecoverableError,
                                      upload_blueprint,
                                      blueprint_id=test_name)
            self.assertIn('_upload failed',
                          error.message)

        # Test that if the blueprint ID exists
    def test_upload_blueprint_exists(self):

        test_name = 'test_upload_blueprint_exists'
        _ctx = self.get_mock_ctx(test_name)
        current_ctx.set(_ctx)

        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            cfy_mock_client = MockCloudifyRestClient()
            list_response = cfy_mock_client.blueprints.list()
            list_response[0]['id'] = test_name

            def mock_return(*args, **kwargs):
                del args, kwargs
                return list_response

            cfy_mock_client.blueprints.list = mock_return
            mock_client.return_value = cfy_mock_client
            output = upload_blueprint(operation='upload_blueprint',
                                      blueprint_id=test_name)
            self.assertFalse(output)

    def test_upload_blueprint_success(self):
        # Test that upload blueprint succeeds

        test_name = 'test_upload_blueprint_success'
        _ctx = self.get_mock_ctx(test_name)
        current_ctx.set(_ctx)

        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            mock_client.return_value = MockCloudifyRestClient()
            output = upload_blueprint(operation='upload_blueprint',
                                      blueprint_id=test_name)
            self.assertTrue(output)

    def test_upload_blueprint_use_external(self):
        # Test that upload blueprint succeeds

        test_name = 'test_upload_blueprint_success'
        _ctx = self.get_mock_ctx(test_name)
        current_ctx.set(_ctx)

        _ctx.instance.runtime_properties['resource_config'] = {
            'blueprint': {
                EXTERNAL_RESOURCE: True
            }
        }

        with mock.patch('cloudify.manager.get_rest_client') as mock_client:
            mock_client.return_value = MockCloudifyRestClient()
            output = upload_blueprint(operation='upload_blueprint',
                                      blueprint_id=test_name)
            self.assertFalse(output)
