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
from mock import MagicMock, patch

from cloudify.state import current_ctx

import cloudify_suspend.workflows as workflows


class TestStatistics(unittest.TestCase):

    def tearDown(self):
        current_ctx.clear()
        super(TestStatistics, self).tearDown()

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
            'cloudify.interfaces.statistics.perfomance': {}
        }

        _instance = MagicMock()
        _instance.send_event = MagicMock(
            return_value='event')
        _instance.execute_operation = MagicMock(
            return_value='execute_operation')

        _node.properties = {}
        _node.instances = [_instance]

        _workflow_ctx = MagicMock()
        _workflow_ctx.nodes = [_node]
        _workflow_ctx.graph_mode = MagicMock(return_value=_graph_mock)
        _workflow_ctx.get_ctx = MagicMock(return_value=_ctx)
        return _workflow_ctx, _graph_mock, _instance

    def test_statistics(self):
        _workflow_ctx, _graph_mock, _instance = self._gen_ctx()

        with patch('cloudify.state.current_workflow_ctx', _workflow_ctx):
            workflows.statistics(ctx=_workflow_ctx)

        _workflow_ctx.graph_mode.assert_called_with()
        _graph_mock.execute.assert_called_with()
        _graph_mock._sequence.add.assert_called_with('event',
                                                     'execute_operation',
                                                     'event')
        _instance.execute_operation.assert_called_with(
            'cloudify.interfaces.statistics.perfomance', kwargs={})


if __name__ == '__main__':
    unittest.main()
