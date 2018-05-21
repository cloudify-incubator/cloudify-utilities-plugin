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
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import unittest
from mock import MagicMock, patch, call

from cloudify.state import current_ctx

import cloudify_suspend.workflows as workflows


class TestSuspend(unittest.TestCase):

    def tearDown(self):
        current_ctx.clear()
        super(TestSuspend, self).tearDown()

    def _gen_ctx(self):
        _ctx = MagicMock()

        _graph_mock = MagicMock()
        _graph_mock.execute = MagicMock()

        _sequence = MagicMock()
        _sequence.add = MagicMock()
        _graph_mock._sequence = _sequence
        _graph_mock.sequence = MagicMock(return_value=_sequence)

        _node = MagicMock()
        _node.operations = {
            # deprecated calls
            'cloudify.interfaces.lifecycle.suspend': {},
            'cloudify.interfaces.lifecycle.resume': {},
            # upstream calls
            'cloudify.interfaces.freeze.suspend': {},
            'cloudify.interfaces.freeze.resume': {},
        }

        _instance = MagicMock()
        _instance.id = "correct_id"
        _instance.send_event = MagicMock(
            return_value='event')
        _instance.execute_operation = MagicMock(
            return_value='execute_operation')

        _node.instances = [_instance]

        _workflow_ctx = MagicMock()
        _workflow_ctx.nodes = [_node]
        _workflow_ctx.graph_mode = MagicMock(return_value=_graph_mock)
        _workflow_ctx.get_ctx = MagicMock(return_value=_ctx)
        return _workflow_ctx, _graph_mock, _instance

    def test_suspend(self):
        # enabled actions
        _workflow_ctx, _graph_mock, _instance = self._gen_ctx()

        with patch('cloudify.state.current_workflow_ctx', _workflow_ctx):
            workflows.suspend(ctx=_workflow_ctx)

        _workflow_ctx.graph_mode.assert_called_with()
        _graph_mock.execute.assert_called_with()
        _graph_mock._sequence.add.assert_called_with('event',
                                                     'execute_operation',
                                                     'event')
        _instance.execute_operation.assert_has_calls([
            call('cloudify.interfaces.lifecycle.suspend', kwargs={}),
            call('cloudify.interfaces.freeze.suspend', kwargs={})
        ])

    def test_suspend_skipped(self):
        # skipped actions
        _workflow_ctx, _graph_mock, _instance = self._gen_ctx()

        _workflow_ctx.nodes[0].properties["skip_actions"] = [
            'cloudify.interfaces.lifecycle.suspend'
        ]

        with patch('cloudify.state.current_workflow_ctx', _workflow_ctx):
            workflows.suspend(ctx=_workflow_ctx)

        _workflow_ctx.graph_mode.assert_called_with()
        _graph_mock.execute.assert_called_with()
        _graph_mock._sequence.add.assert_called_with('event',
                                                     'execute_operation',
                                                     'event')
        _instance.execute_operation.assert_has_calls([
            call('cloudify.interfaces.freeze.suspend', kwargs={})
        ])

    def test_resume(self):
        # resume all
        _workflow_ctx, _graph_mock, _instance = self._gen_ctx()
        with patch('cloudify.state.current_workflow_ctx', _workflow_ctx):
            workflows.resume(ctx=_workflow_ctx)

        _workflow_ctx.graph_mode.assert_called_with()
        _graph_mock.execute.assert_called_with()
        _graph_mock._sequence.add.assert_called_with('event',
                                                     'execute_operation',
                                                     'event')
        _instance.execute_operation.assert_has_calls([
            call('cloudify.interfaces.freeze.resume', kwargs={}),
            call('cloudify.interfaces.lifecycle.resume', kwargs={})
        ])
        # resume only selected
        _workflow_ctx, _graph_mock, _instance = self._gen_ctx()
        with patch('cloudify.state.current_workflow_ctx', _workflow_ctx):
            workflows.resume(ctx=_workflow_ctx,
                             include_instances=["correct_id"])

        _workflow_ctx.graph_mode.assert_called_with()
        _graph_mock.execute.assert_called_with()
        _graph_mock._sequence.add.assert_called_with('event',
                                                     'execute_operation',
                                                     'event')
        _instance.execute_operation.assert_has_calls([
            call('cloudify.interfaces.freeze.resume', kwargs={
                "include_instances": ["correct_id"]
            }),
            call('cloudify.interfaces.lifecycle.resume', kwargs={
                "include_instances": ["correct_id"]
            })
        ])
        # no instances for resume
        _workflow_ctx, _graph_mock, _instance = self._gen_ctx()
        with patch('cloudify.state.current_workflow_ctx', _workflow_ctx):
            workflows.resume(ctx=_workflow_ctx,
                             include_instances=["wrong_id"])

        _workflow_ctx.graph_mode.assert_called_with()
        _graph_mock.execute.assert_called_with()
        _graph_mock._sequence.add.assert_not_called()
        _instance.execute_operation.assert_not_called()


if __name__ == '__main__':
    unittest.main()
