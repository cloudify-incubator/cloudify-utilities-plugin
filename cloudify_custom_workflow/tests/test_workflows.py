# Copyright (c) 2017-2018 Cloudify Platform Ltd. All rights reserved
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

from cloudify.state import current_ctx

from .. import tasks


class TestWorkflow(unittest.TestCase):

    def tearDown(self):
        current_ctx.clear()
        super(TestWorkflow, self).tearDown()

    def _gen_ctx(self):
        _ctx = Mock()

        _graph_mock = Mock()
        _graph_mock.execute = Mock()

        _sequence = Mock()
        _sequence.add = Mock()
        _graph_mock._sequence = _sequence
        _graph_mock.sequence = Mock(return_value=_sequence)

        _node = Mock()
        _node.operations = {
            'operation1': {},
            'operation2': {},
        }

        _instance = Mock()
        _instance.id = "instance_id"
        _instance.send_event = Mock(
            return_value='event')
        _instance.execute_operation = Mock(
            return_value='execute_operation')

        _node.properties = {}
        _node.id = 'node_id'
        _node.instances = [_instance]

        _workflow_ctx = Mock()
        _workflow_ctx.nodes = [_node]
        _workflow_ctx.graph_mode = Mock(return_value=_graph_mock)
        _workflow_ctx.get_ctx = Mock(return_value=_ctx)
        return _workflow_ctx, _graph_mock, _instance

    def test_log(self):
        _ctx, _, _ = self._gen_ctx()
        _ctx.logger.info = Mock()
        current_ctx.set(_ctx)
        tasks.log(a="a")
        _ctx.logger.info.assert_called_with("Log interface: {'a': 'a'}")

    def test_customwf(self):
        _ctx, _, _instance = self._gen_ctx()
        # current_ctx.set(_ctx)
        with patch('cloudify.state.current_workflow_ctx', _ctx):
            with patch('cloudify_custom_workflow.tasks.workflow_ctx', _ctx):
                tasks.customwf(ctx=_ctx, nodes_to_runon=['node_id'],
                               operations_to_execute=['operation1'])
        _instance.execute_operation.assert_called_with('operation1',
                                                       kwargs={})


if __name__ == '__main__':
    unittest.main()
