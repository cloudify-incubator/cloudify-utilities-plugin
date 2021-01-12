# Copyright (c) 2016-2019 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

from mock import Mock, patch

from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext

import cloudify_rollback_workflow.workflows as workflows
import cloudify_rollback_workflow.lifecycle as lifecycle


def mock_send_event(event):
    return event


def mock_set_state(state):
    return 'set state :{state}'.format(state=state)


def mock_call_for_forkjoin(*args):
    return list(args)


class TestRollbackWorkflow(unittest.TestCase):

    def tearDown(self):
        current_ctx.clear()
        super(TestRollbackWorkflow, self).tearDown()

    def _gen_ctx(self):
        _ctx = MockCloudifyContext(
            deployment_id="deployment_id"
        )
        _ctx._subgraph = []

        def _subgraph(instance_id):
            _subgraph = Mock()
            _subgraph.instance_id = "subgraph" + instance_id
            sequence = Mock()
            _subgraph.sequence = sequence
            _ctx._subgraph.append(_subgraph)
            return _subgraph

        _graph = Mock()
        _graph.id = u'test_graph'
        _graph.subgraph = _subgraph
        _ctx.nodes = []
        _ctx.node_instances = []
        _ctx.graph_mode = Mock(return_value=_graph)
        _ctx._graph = _graph
        _ctx.refresh_node_instances = Mock(return_value=None)
        current_ctx.set(_ctx)
        return _ctx

    def gen_mock_instance(self, ctx, state, instance_id=u"a_id"):
        a_instance = Mock()
        a_instance.id = instance_id
        a_instance.state = state
        a_instance.send_event = mock_send_event
        a_instance.set_state = mock_set_state
        a_instance.node.operations = []
        a_instance.node.type_hierarchy = [u"test_type"]
        a_node = Mock()
        a_node.id = u"a_node_id"
        a_node.instances = [a_instance]
        ctx.nodes.append(a_node)
        ctx.node_instances.append(a_instance)
        return a_instance

    def test_find_all_unresolved_node_instances(self):
        _ctx = self._gen_ctx()
        a_instance = Mock()
        a_instance.id = u"a_id"
        a_instance.state = u"started"
        c_instance = Mock()
        c_instance.id = u"c_id"
        c_instance.state = u"starting"
        a_node = Mock()
        a_node.id = u"a_node_id"
        a_node.instances = [a_instance, c_instance]
        b_instance = Mock()
        b_instance.id = u"b_id"
        b_instance.state = u"configuring"
        b_node = Mock()
        b_node.instances = [b_instance]
        _ctx.nodes = [a_node, b_node]
        unresolved_nodes = workflows._find_all_unresolved_node_instances(
            _ctx,
            node_ids=[],
            node_instance_ids=[],
            type_names=[])
        self.assertListEqual(unresolved_nodes, [c_instance, b_instance])

        unresolved_nodes = workflows._find_all_unresolved_node_instances(
            _ctx,
            node_ids=[],
            node_instance_ids=[u"c_id"],
            type_names=[])
        self.assertListEqual(unresolved_nodes, [c_instance])

        unresolved_nodes = workflows._find_all_unresolved_node_instances(
            _ctx,
            node_ids=[u"a_node_id"],
            node_instance_ids=[],
            type_names=[])
        self.assertListEqual(unresolved_nodes, [c_instance])

    def test_rollback_call(self):
        ctx = self._gen_ctx()
        instance_a = self.gen_mock_instance(ctx, u"starting")
        instance_b = self.gen_mock_instance(ctx,
                                            state=u"started",
                                            instance_id=u"b_id")
        with patch(
                'cloudify_rollback_workflow.workflows.utilitieslifecycle'
                '.rollback_node_instances')as mock_lifecycle_rollback:
            workflows.rollback(ctx,
                               type_names=[],
                               node_ids=[],
                               node_instance_ids=[],
                               full_rollback=False)
            mock_lifecycle_rollback.assert_called_with(
                graph=ctx.graph_mode(),
                node_instances=set([instance_a]),
                related_nodes=set([instance_b]))

    def test_rollback_node_instance_subgraph_resolved_state(self):
        ctx = self._gen_ctx()
        instance = self.gen_mock_instance(ctx, u"started")
        lifecycle.rollback_node_instance_subgraph(instance,
                                                  ctx.graph_mode(),
                                                  False)
        tasks = [
            'Validating node instance after deletion: nothing to do',
            'Rollback Stop: nothing to do, instance state is started',
            'Rollback Delete: nothing to do, instance state is started'
        ]
        ctx._subgraph[0].sequence.return_value.add.assert_called_with(*tasks)

    def test_rollback_node_instance_subgraph_starting_state(self):
        ctx = self._gen_ctx()
        instance = self.gen_mock_instance(ctx, u"starting")

        with patch(
                'cloudify_rollback_workflow.lifecycle.forkjoin') as \
                fake_forkjoin:
            with patch(
                    'cloudify_rollback_workflow.lifecycle'
                    '._skip_nop_operations') as fake_skip_nop:
                fake_skip_nop.return_value = [
                    'tasks from _skip_nop_operations call']
                fake_forkjoin.side_effect = mock_call_for_forkjoin
                lifecycle.rollback_node_instance_subgraph(instance,
                                                          ctx.graph_mode(),
                                                          False)
                # For stop and monitoring_stop return value is ['tasks from
                # _skip_nop_operations call']
                tasks = [['set state :stopping', 'Stopping node instance'],
                         'Validating node instance after deletion: nothing '
                         'to do',
                         'tasks from _skip_nop_operations call',
                         'tasks from _skip_nop_operations call',
                         'set state :configured',
                         'Rollback Delete: nothing to do, instance state is '
                         'starting',
                         'Rollbacked node instance']
                ctx._subgraph[0].sequence.return_value.add.assert_called_with(
                    *tasks)
                # For stop and monitoring_stop
                self.assertEqual(fake_skip_nop.call_count, 2)

    def test_rollback_node_instance_subgraph_creating_state(self):
        ctx = self._gen_ctx()
        instance = self.gen_mock_instance(ctx, u"creating")
        with patch(
                'cloudify_rollback_workflow.lifecycle.forkjoin') as \
                fake_forkjoin:
            with patch(
                    'cloudify_rollback_workflow.lifecycle'
                    '._skip_nop_operations') as fake_skip_nop:
                with patch(
                        'cloudify_rollback_workflow.lifecycle'
                        '._relationships_operations'):
                    fake_skip_nop.return_value = [
                        'tasks from _skip_nop_operations call']
                    fake_forkjoin.side_effect = mock_call_for_forkjoin
                    lifecycle.rollback_node_instance_subgraph(instance,
                                                              ctx.graph_mode(),
                                                              False)

                    # For delete and unlink return value is ['tasks from
                    # _skip_nop_operations call']
                    tasks = [
                        'Validating node instance after deletion: nothing to '
                        'do',
                        'Rollback Stop: nothing to do, instance state is '
                        'creating',
                        'tasks from _skip_nop_operations call',
                        'tasks from _skip_nop_operations call',
                        'set state :uninitialized',
                        'Rollbacked node instance']
                    ctx._subgraph[
                        0].sequence.return_value.add.assert_called_with(*tasks)
                    # For delete and unlink
                    self.assertEqual(fake_skip_nop.call_count, 2)
