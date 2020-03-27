# Copyright (c) 2017-2019 Cloudify Platform Ltd. All rights reserved
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
from mock import Mock, patch

import cloudify_hooks_workflow.tasks as tasks


class TestTasks(unittest.TestCase):

    def test_run_workflow_skip_uncofigured(self):
        # no settings
        _ctx = Mock()
        tasks.run_workflow(inputs={}, ctx=_ctx)
        _ctx.logger.error.assert_called_with("Deployment id is undefined")

        _ctx = Mock()
        tasks.run_workflow(inputs={'deployment_id': 'w_id'}, ctx=_ctx)
        _ctx.logger.error.assert_called_with("Workflow for run is undefined")

    def test_run_workflow_skip_no_deployment(self):
        _ctx = Mock()
        fake_client = Mock()
        fake_client.deployments.get = Mock(return_value={})
        mock_manager = Mock()
        mock_manager.get_rest_client = Mock(return_value=fake_client)
        with patch('cloudify_hooks_workflow.tasks.manager', mock_manager):
            tasks.run_workflow(inputs={'deployment_id': 'w_id'},
                               workflow_for_run="uninstall",
                               ctx=_ctx)
            _ctx.logger.error.assert_called_with('Deployment disappear.')

    def test_run_workflow_skip_wrong_filter_by(self):
        _ctx = Mock()
        fake_client = Mock()
        fake_client.deployments.get = Mock(return_value={'id': 'id'})
        mock_manager = Mock()
        mock_manager.get_rest_client = Mock(return_value=fake_client)
        with patch('cloudify_hooks_workflow.tasks.manager', mock_manager):
            tasks.run_workflow(inputs={'deployment_id': 'w_id'},
                               workflow_for_run="uninstall",
                               filter_by={'a': 'b'},
                               ctx=_ctx)
            _ctx.logger.error.assert_called_with(
                'Filter skiped by incorrect type of rules list.')

    def test_run_workflow_run_external_client(self):
        _ctx = Mock()
        fake_client = Mock()
        fake_client.deployments.get = Mock(return_value={'id': 'id'})
        with patch(
            'cloudify_hooks_workflow.tasks.CloudifyClient',
            Mock(return_value=fake_client)
        ):
            tasks.run_workflow(inputs={'deployment_id': 'w_id'},
                               workflow_for_run="uninstall",
                               client_config={'host': 'localhost'},
                               workflow_params={'force': True},
                               ctx=_ctx)
            fake_client.executions.start.assert_called_with(
                deployment_id='w_id', workflow_id='uninstall', force=True)


if __name__ == '__main__':
    unittest.main()
