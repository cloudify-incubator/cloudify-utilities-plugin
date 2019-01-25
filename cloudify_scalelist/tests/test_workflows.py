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
from mock import Mock, patch, call

from cloudify.mocks import MockCloudifyContext
from cloudify.state import current_ctx
from cloudify.workflows.workflow_api import ExecutionCancelled

import cloudify_scalelist.workflows as workflows
# add filter check
import cloudify_common_sdk.filters as filters


class TestScaleList(unittest.TestCase):

    def tearDown(self):
        current_ctx.clear()
        super(TestScaleList, self).tearDown()

    def _gen_rest_client(self):
        instance_a = Mock()
        instance_a.id = 'a_id'
        instance_a.node_id = 'a_type'
        instance_a.runtime_properties = {
            'name': 'value',
            '_transaction': '1'
        }
        instance_b = Mock()
        instance_b.id = 'b_id'
        instance_b.node_id = 'b_type'
        instance_b.runtime_properties = {
            'name': 'other',
            '_transaction': '1'
        }
        instance_c = Mock()
        instance_c.id = 'c_id'
        instance_c.node_id = 'c_type'
        instance_c.runtime_properties = {
            'name': 'other',
            '_transaction': '-'
        }
        instance_d = Mock()
        instance_d.id = 'b_id'
        instance_d.node_id = 'c_type'
        instance_d.runtime_properties = {
            'name': 'other',
        }

        client = Mock()
        client.node_instances.list = Mock(return_value=[
            instance_a, instance_b, instance_c, instance_d])
        client.deployments.get = Mock(return_value={
            'groups': {
                'one_scale': {
                    'members': ['one', 'two']
                },
                'any': {
                    'members': ['one', 'two', "three"]
                },
                'alfa_types': {
                    'members': ['a_type', 'b_type']
                }
            }
        })

        # update instances
        target_node = Mock()
        target_node.id = 'target'
        target_node.version = 1
        target_node.state = 'deleted'
        target_node.runtime_properties = {'a': 'b', 'd': 'e'}

        client.node_instances.update = Mock()
        client.node_instances.get = Mock(return_value=target_node)

        return client

    def _gen_ctx(self, execution_cancelled=True, task_string=True):

        _ctx = MockCloudifyContext(
            deployment_id="deployment_id"
        )
        _ctx._subgraph = []

        def _subgraph(instance_id):
            _subgraph = Mock()
            _subgraph.instance_id = "subgraph" + instance_id
            _ctx._subgraph.append(_subgraph)
            return _subgraph

        _graph = Mock()
        _graph.id = 'i_am_graph'
        if not task_string:
            _task_mock = Mock()
            _task_mock.id = 'id'
            _task_mock.get_state.return_value = 'task_sent'
        else:
            _task_mock = Mock()
            _task_mock.id = 'task1'
            _task_mock.get_state.return_value = 'task_sent'
        _graph.tasks_iter = Mock(return_value=[_task_mock])
        _graph.remove_task = Mock(return_value=None)
        _graph.subgraph = _subgraph
        _graph._is_execution_cancelled.return_value = execution_cancelled
        _graph._terminated_tasks.return_value = [_task_mock]
        _ctx.nodes = []
        _ctx.graph_mode = Mock(return_value=_graph)
        _ctx._graph = _graph
        _ctx.wait_after_fail = 5
        _ctx.deployment.scaling_groups = {
            'one_scale': {
                'members': ['one'],
                'properties': {'current_instances': 10}
            },
            'alfa_types': {
                'members': ['a_type', 'b_type'],
                'properties': {'current_instances': 55}
            }
        }

        modification = Mock()
        modification.id = "transaction_id"
        modification.added.node_instances = []
        modification.removed.node_instances = []
        modification.rollback = Mock()
        modification.finish = Mock()
        _ctx.deployment.start_modification = Mock(return_value=modification)
        _ctx._get_modification = modification

        current_ctx.set(_ctx)
        return _ctx

    def test_update_runtime_properties(self):
        client = self._gen_rest_client()
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            workflows._update_runtime_properties(
                self._gen_ctx(),
                'target',
                {'a': 'c'}
            )

        client.node_instances.update.assert_called_with(
            node_instance_id='target',
            runtime_properties={'a': 'c', 'd': 'e'}, version=2)
        client.node_instances.get.assert_called_with('target')

    def test_cleanup_instances(self):
        client = self._gen_rest_client()
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            workflows._cleanup_instances(
                self._gen_ctx(), ['target']
            )
        client.node_instances.update.assert_called_with(
            node_instance_id='target', state='uninitialized',
            runtime_properties={}, version=2)
        client.node_instances.get.assert_called_with('target')

    def test_empty_scaleup_params(self):
        with self.assertRaises(ValueError):
            workflows.scaleuplist(ctx=Mock(),
                                  scalable_entity_properties=[])

    def test_empty_scaledown_params(self):
        # empty values
        with self.assertRaises(ValueError):
            workflows.scaledownlist(ctx=Mock())
        # no nodes with such value, all instances
        _ctx = self._gen_ctx()
        client = self._gen_rest_client()
        client.node_instances.list = Mock(return_value=[])
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            workflows.scaledownlist(
                ctx=_ctx,
                scale_transaction_field='_transaction',
                all_results=True,
                scale_node_name="node", scale_node_field="name",
                scale_node_field_value="value"
            )
            client.node_instances.list.assert_called_with(
                _include=['runtime_properties', 'node_id', 'id'],
                _get_all_results=True,
                deployment_id='deployment_id')
        # only first page
        client.node_instances.list = Mock(return_value=[])
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            workflows.scaledownlist(
                ctx=_ctx,
                scale_transaction_field='_transaction',
                scale_node_name="node", scale_node_field="name",
                scale_node_field_value="value"
            )
            client.node_instances.list.assert_called_with(
                _include=['runtime_properties', 'node_id', 'id'],
                deployment_id='deployment_id')

    def test_scaleup_group_to_settings(self):
        # scale groups names
        _ctx = self._gen_ctx()
        client = self._gen_rest_client()
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            self.assertEqual(
                workflows._scaleup_group_to_settings(
                    _ctx, {
                        'one_scale': {
                            'count': 1,
                            'values': [{'name': 'one'},
                                       {'name': 'two'}]
                        },
                        'second_scale': {
                            'count': 0,
                            'values': []
                        },

                    },
                    True
                ),
                {'one_scale': {'instances': 11}}
            )

        # node names
        _ctx = self._gen_ctx()
        client = self._gen_rest_client()
        fake_node_parent = Mock()
        fake_node_parent.number_of_instances = 34
        fake_node_parent.id = "id_34"
        fake_node = Mock()
        fake_node.host_node = fake_node_parent
        fake_node.number_of_instances = 43
        fake_node.id = "id_43"
        _ctx.get_node = Mock(return_value=fake_node)
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            # get parent host
            self.assertEqual(
                workflows._scaleup_group_to_settings(
                    _ctx, {
                        'one': {
                            'count': 1,
                            'values': [{'name': 'one'}]
                        }
                    },
                    True
                ),
                {'id_34': {'instances': 35}}
            )
            _ctx.get_node.assert_called_with('one')
            # get child
            self.assertEqual(
                workflows._scaleup_group_to_settings(
                    _ctx, {
                        'one': {
                            'count': 1,
                            'values': [{'name': 'one'}]
                        }
                    },
                    False
                ),
                {'id_43': {'instances': 44}}
            )
            # no such node
            _ctx.get_node = Mock(return_value=None)
            with self.assertRaises(ValueError):
                workflows._scaleup_group_to_settings(
                    _ctx, {
                        'one': {
                            'count': 1,
                            'values': [{'name': 'one'}]
                        }
                    },
                    False
                )

    def test_scaleuplist(self):
        _ctx = self._gen_ctx()

        client = self._gen_rest_client()
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            # can downscale without errors, stop on failure
            fake_run_scale = Mock(return_value=None)
            with patch(
                "cloudify_scalelist.workflows._run_scale_settings",
                fake_run_scale
            ):
                workflows.scaleuplist(
                    ctx=_ctx,
                    scale_compute=True,
                    scale_transaction_field="_transaction",
                    scale_transaction_value="transaction_value",
                    ignore_rollback_failure=False,
                    scalable_entity_properties={
                        'one': [{'name': 'one'}],
                    })
            fake_run_scale.assert_called_with(
                _ctx, {'one_scale': {'instances': 11}},
                {'one': [{'name': 'one'}]}, '_transaction',
                'transaction_value', False, False, node_sequence=None)
            # can downscale without errors, ignore failure
            fake_run_scale = Mock(return_value=None)
            with patch(
                "cloudify_scalelist.workflows._run_scale_settings",
                fake_run_scale
            ):
                workflows.scaleuplist(
                    ctx=_ctx,
                    scale_compute=True,
                    scale_transaction_field="_transaction",
                    scale_transaction_value="transaction_value",
                    scalable_entity_properties={
                        'one': [{'name': 'one'}],
                    })
            fake_run_scale.assert_called_with(
                _ctx, {'one_scale': {'instances': 11}},
                {'one': [{'name': 'one'}]}, '_transaction',
                'transaction_value', False, True, node_sequence=None)

    def test_run_scale_settings(self):
        _ctx = self._gen_ctx()

        client = self._gen_rest_client()
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            scale_settings = {'a': {
                'instances': 0,
                'removed_ids_include_hint': []}}
            # check run with empty instances list
            workflows._run_scale_settings(_ctx, scale_settings, {})
        _ctx.deployment.start_modification.assert_called_with(
            scale_settings
        )
        _ctx._get_modification.finish.assert_called_with()

    def test_run_scale_settings_correct_uninstall(self):
        _ctx = self._gen_ctx()

        client = self._gen_rest_client()

        delete_instance = Mock()
        delete_instance._node_instance.id = "a"
        delete_instance.modification = 'removed'
        related_instance = Mock()
        related_instance._node_instance.id = "f"
        related_instance.modification = 'related'
        _ctx._get_modification.removed.node_instances = [delete_instance,
                                                         related_instance]
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            scale_settings = {'a': {
                'instances': 0,
                'removed_ids_include_hint': []}}
            fake_uninstall_node_instances = Mock()
            with patch(
                "cloudify_scalelist.workflows.lifecycle"
                ".uninstall_node_instances",
                fake_uninstall_node_instances
            ):
                workflows._run_scale_settings(_ctx, scale_settings, {})
        fake_uninstall_node_instances.assert_called_with(
            graph=_ctx.graph_mode(),
            node_instances=set([delete_instance]),
            ignore_failure=False,
            related_nodes=set([related_instance])
        )
        _ctx.deployment.start_modification.assert_called_with(
            scale_settings
        )
        _ctx._get_modification.finish.assert_called_with()
        _ctx._get_modification.rollback.assert_not_called()

    def test_run_scale_settings_wrongids_uninstall(self):
        _ctx = self._gen_ctx()

        client = self._gen_rest_client()

        delete_instance = Mock()
        delete_instance._node_instance.id = "a"
        delete_instance.modification = 'removed'
        _ctx._get_modification.removed.node_instances = [delete_instance]
        _ctx.wait_after_fail = 0
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            scale_settings = {'a': {
                'instances': 0,
                'removed_ids_include_hint': ['b']}}
            fake_uninstall_node_instances = Mock()
            with patch(
                "cloudify_scalelist.workflows.lifecycle."
                "uninstall_node_instances",
                fake_uninstall_node_instances
            ):
                with self.assertRaises(Exception) as error:
                    workflows._run_scale_settings(_ctx, scale_settings, {},
                                                  instances_remove_ids=['b'])
                self.assertEqual(
                    "Instance 'a' not in proposed list ['b'].",
                    str(error.exception))
            fake_uninstall_node_instances.assert_not_called()
        _ctx.deployment.start_modification.assert_called_with(
            scale_settings
        )
        _ctx._get_modification.rollback.assert_called_with()
        _ctx._get_modification.finish.assert_not_called()

    def test_run_scale_settings_install_failed(self):
        _ctx = self._gen_ctx()

        client = self._gen_rest_client()

        added_instance = Mock()
        added_instance._node_instance.id = "a"
        added_instance.modification = 'added'
        related_instance = Mock()
        related_instance._node_instance.id = "f"
        related_instance.modification = 'related'
        _ctx._get_modification.added.node_instances = [added_instance,
                                                       related_instance]
        _ctx.wait_after_fail = 0
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            scale_settings = {'a': {'instances': 1}}
            fake_install_node_instances = Mock(
                side_effect=Exception('Failed install'))
            with patch(
                "cloudify_scalelist.workflows.lifecycle."
                "install_node_instances",
                fake_install_node_instances
            ):
                fake_uninstall_instances = Mock(return_value=None)
                with patch(
                    "cloudify_scalelist.workflows._uninstall_instances",
                    fake_uninstall_instances
                ):
                    with self.assertRaisesRegexp(
                        Exception,
                        "Failed install"
                    ):
                        workflows._run_scale_settings(
                            _ctx, scale_settings, {},
                            ignore_rollback_failure=False)
                fake_uninstall_instances.assert_called_with(
                    ctx=_ctx,
                    graph=_ctx.graph_mode(),
                    removed=set([added_instance]),
                    related=set([related_instance]),
                    ignore_failure=False,
                    node_sequence=None)
            fake_install_node_instances.assert_called_with(
                graph=_ctx.graph_mode(),
                node_instances=set([added_instance]),
                related_nodes=set([related_instance])
            )
        _ctx.deployment.start_modification.assert_called_with(
            scale_settings
        )
        _ctx._get_modification.rollback.assert_called_with()
        _ctx._get_modification.finish.assert_not_called()

    def test_run_scale_settings_install_failed_checking_cancelled(self):
        _ctx = self._gen_ctx(task_string=False)

        client = self._gen_rest_client()

        added_instance = Mock()
        added_instance._node_instance.id = "a"
        added_instance.modification = 'added'
        related_instance = Mock()
        related_instance._node_instance.id = "f"
        related_instance.modification = 'related'
        _ctx._get_modification.added.node_instances = [added_instance,
                                                       related_instance]
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            scale_settings = {'a': {'instances': 1}}
            fake_install_node_instances = Mock(
                side_effect=Exception('Failed install'))
            with patch(
                "cloudify_scalelist.workflows.lifecycle."
                "install_node_instances",
                fake_install_node_instances
            ):
                fake_uninstall_instances = Mock(return_value=None)
                with patch(
                    "cloudify_scalelist.workflows._uninstall_instances",
                    fake_uninstall_instances
                ):
                    with patch(
                        "cloudify.workflows.tasks_graph."
                        "TaskDependencyGraph._is_execution_cancelled",
                        return_value=True
                    ):
                        with self.assertRaises(ExecutionCancelled):
                            workflows._run_scale_settings(
                                _ctx, scale_settings, {},
                                ignore_rollback_failure=False)
        _ctx.deployment.start_modification.assert_called_with(
            scale_settings
        )
        _ctx._get_modification.rollback.assert_not_called()
        _ctx._get_modification.finish.assert_not_called()

    def test_run_scale_settings_install_failed_checking_tasks(self):
        _ctx = self._gen_ctx(False, task_string=False)

        client = self._gen_rest_client()

        added_instance = Mock()
        added_instance._node_instance.id = "a"
        added_instance.modification = 'added'
        related_instance = Mock()
        related_instance._node_instance.id = "f"
        related_instance.modification = 'related'
        _ctx._get_modification.added.node_instances = [added_instance,
                                                       related_instance]
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            scale_settings = {'a': {'instances': 1}}
            fake_install_node_instances = Mock(
                side_effect=Exception('Failed install'))
            with patch(
                "cloudify_scalelist.workflows.lifecycle."
                "install_node_instances",
                fake_install_node_instances
            ):
                fake_uninstall_instances = Mock(return_value=None)
                with patch(
                    "cloudify_scalelist.workflows._uninstall_instances",
                    fake_uninstall_instances
                ):
                    with self.assertRaises(Exception):
                        workflows._run_scale_settings(
                            _ctx, scale_settings, {},
                            ignore_rollback_failure=False)
                    _ctx.deployment.start_modification.assert_called_with(
                        scale_settings
                    )
                    _ctx._get_modification.rollback.assert_called_with()
                    _ctx._get_modification.finish.assert_not_called()

    def test_run_scale_settings_install_failed_handle_tasks(self):
        _ctx = self._gen_ctx(task_string=False)

        client = self._gen_rest_client()

        added_instance = Mock()
        added_instance._node_instance.id = "a"
        added_instance.modification = 'added'
        related_instance = Mock()
        related_instance._node_instance.id = "f"
        related_instance.modification = 'related'
        _ctx._get_modification.added.node_instances = [added_instance,
                                                       related_instance]
        mocked_task = Mock()
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            fake_install_node_instances = Mock(
                side_effect=Exception('Failed install'))
            with patch(
                "cloudify_scalelist.workflows.lifecycle."
                "install_node_instances",
                fake_install_node_instances
            ):
                fake_uninstall_instances = Mock(return_value=None)
                with patch(
                    "cloudify_scalelist.workflows._uninstall_instances",
                    fake_uninstall_instances
                ):
                    with patch(
                        "cloudify.workflows.tasks_graph."
                        "TaskDependencyGraph._is_execution_cancelled",
                        return_value=False
                    ):
                        with patch(
                            "cloudify.workflows.tasks_graph."
                            "TaskDependencyGraph._terminated_tasks",
                            return_value=[mocked_task]
                        ):
                            self.assertRaises(RuntimeError)

    def test_run_scale_settings_install(self):
        _ctx = self._gen_ctx()

        client = self._gen_rest_client()

        added_instance = Mock()
        added_instance._node_instance.id = "a"
        added_instance._node_instance.node_id = "type_a"
        added_instance.modification = 'added'
        related_instance = Mock()
        related_instance._node_instance.id = "f"
        related_instance._node_instance.node_id = "type_f"
        related_instance.modification = 'related'
        _ctx._get_modification.added.node_instances = [added_instance,
                                                       related_instance]
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            scale_settings = {'a': {'instances': 1}}
            fake_install_node_instances = Mock()
            with patch(
                "cloudify_scalelist.workflows.lifecycle."
                "install_node_instances",
                fake_install_node_instances
            ):
                fake_uninstall_instances = Mock(return_value=None)
                with patch(
                    "cloudify_scalelist.workflows._uninstall_instances",
                    fake_uninstall_instances
                ):
                    fake_update_instances = Mock(return_value=None)
                    with patch(
                        "cloudify_scalelist.workflows."
                        "_update_runtime_properties",
                        fake_update_instances
                    ):
                        workflows._run_scale_settings(
                            _ctx, scale_settings,
                            {"type_a": [{"c": "f"}]},
                            scale_transaction_field='_transaction'
                        )
                    fake_update_instances.assert_called_with(
                        _ctx, "a", {'c': 'f',
                                    '_transaction': 'transaction_id'})
                fake_uninstall_instances.assert_not_called()
            fake_install_node_instances.assert_called_with(
                graph=_ctx.graph_mode(),
                node_instances=set([added_instance]),
                related_nodes=set([related_instance])
            )
        _ctx.deployment.start_modification.assert_called_with(
            scale_settings
        )
        _ctx._get_modification.rollback.assert_not_called()
        _ctx._get_modification.finish.assert_called_with()

    def test_run_scale_settings_install_withtransacrtion_id(self):
        _ctx = self._gen_ctx()

        client = self._gen_rest_client()

        added_instance = Mock()
        added_instance._node_instance.id = "a"
        added_instance._node_instance.node_id = "type_a"
        added_instance.modification = 'added'
        related_instance = Mock()
        related_instance._node_instance.id = "f"
        related_instance._node_instance.node_id = "type_f"
        related_instance.modification = 'related'
        _ctx._get_modification.added.node_instances = [added_instance,
                                                       related_instance]
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            scale_settings = {'a': {'instances': 1}}
            fake_install_node_instances = Mock()
            with patch(
                "cloudify_scalelist.workflows.lifecycle."
                "install_node_instances",
                fake_install_node_instances
            ):
                fake_uninstall_instances = Mock(return_value=None)
                with patch(
                    "cloudify_scalelist.workflows._uninstall_instances",
                    fake_uninstall_instances
                ):
                    fake_update_instances = Mock(return_value=None)
                    with patch(
                        "cloudify_scalelist.workflows."
                        "_update_runtime_properties",
                        fake_update_instances
                    ):
                        workflows._run_scale_settings(
                            _ctx, scale_settings,
                            {"type_a": [{"c": "f"}]},
                            scale_transaction_field='_transaction',
                            scale_transaction_value='value'
                        )
                    fake_update_instances.assert_called_with(
                        _ctx, "a", {'c': 'f', '_transaction': 'value'})
                fake_uninstall_instances.assert_not_called()
            fake_install_node_instances.assert_called_with(
                graph=_ctx.graph_mode(),
                node_instances=set([added_instance]),
                related_nodes=set([related_instance])
            )
        _ctx.deployment.start_modification.assert_called_with(
            scale_settings
        )
        _ctx._get_modification.rollback.assert_not_called()
        _ctx._get_modification.finish.assert_called_with()

    def test_run_scale_settings_install_scalelist(self):
        _ctx = self._gen_ctx()

        client = self._gen_rest_client()

        added_instance = Mock()
        added_instance._node_instance.id = "a"
        added_instance._node_instance.node_id = "type_a"
        added_instance.modification = 'added'
        related_instance = Mock()
        related_instance._node_instance.id = "f"
        related_instance._node_instance.node_id = "type_f"
        related_instance.modification = 'related'
        _ctx._get_modification.added.node_instances = [added_instance,
                                                       related_instance]
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            scale_settings = {'a': {'instances': 1}}
            fake_install_node_instances = Mock()
            with patch(
                "cloudify_scalelist.workflows._process_node_instances",
                fake_install_node_instances
            ):
                fake_uninstall_instances = Mock(return_value=None)
                with patch(
                    "cloudify_scalelist.workflows._uninstall_instances",
                    fake_uninstall_instances
                ):
                    fake_update_instances = Mock(return_value=None)
                    with patch(
                        "cloudify_scalelist.workflows."
                        "_update_runtime_properties",
                        fake_update_instances
                    ):
                        workflows._run_scale_settings(
                            _ctx, scale_settings,
                            {"type_a": [{"c": "f"}]},
                            scale_transaction_field='_transaction',
                            scale_transaction_value='value',
                            node_sequence=['a', 'b']
                        )
                    fake_update_instances.assert_called_with(
                        _ctx, "a", {'c': 'f', '_transaction': 'value'})
                fake_uninstall_instances.assert_not_called()

            call_func = workflows.lifecycle.install_node_instance_subgraph
            fake_install_node_instances.assert_called_with(
                ctx=_ctx,
                graph=_ctx.graph_mode(),
                ignore_failure=False,
                node_instance_subgraph_func=call_func,
                node_instances=set([added_instance]),
                node_sequence=['a', 'b']
            )
        _ctx.deployment.start_modification.assert_called_with(
            scale_settings
        )
        _ctx._get_modification.rollback.assert_not_called()
        _ctx._get_modification.finish.assert_called_with()

    def test_process_node_instances(self):
        _ctx = self._gen_ctx()

        call_func = Mock(return_value="subgraph")
        added_instance = Mock()
        added_instance._node_instance.id = "a"
        added_instance._node_instance.node_id = "type_a"
        added_instance.modification = 'added'
        related_instance = Mock()
        related_instance._node_instance.id = "f"
        related_instance._node_instance.node_id = "type_f"
        related_instance.modification = 'related'

        graph = _ctx.graph_mode()
        workflows._process_node_instances(
            ctx=_ctx,
            graph=graph,
            ignore_failure=False,
            node_instances=[added_instance, related_instance],
            node_instance_subgraph_func=call_func,
            node_sequence=["type_a", "type_f", "type_g"])

        graph.add_dependency.assert_has_calls([call('subgraph', 'subgraph')])
        call_func.assert_has_calls([
            call(added_instance, graph, ignore_failure=False),
            call(related_instance, graph, ignore_failure=False)])

    def test_scaledownlist_with_anytype_and_without_transaction(self):
        _ctx = self._gen_ctx()

        client = self._gen_rest_client()
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            # can downscale without errors
            fake_run_scale = Mock(return_value=None)
            with patch(
                "cloudify_scalelist.workflows._run_scale_settings",
                fake_run_scale
            ):
                workflows.scaledownlist(
                    ctx=_ctx,
                    scale_node_field="name",
                    scale_node_field_value=["value"]
                )
            fake_run_scale.assert_called_with(
                _ctx, {
                    'alfa_types': {
                        'instances': 54,
                        'removed_ids_include_hint': ['a_id']
                    }
                }, {}, instances_remove_ids=['a_id'],
                ignore_failure=False, node_sequence=None)

    def test_scaledownlist(self):
        _ctx = self._gen_ctx()

        client = self._gen_rest_client()
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            # can downscale without errors
            fake_run_scale = Mock(return_value=None)
            with patch(
                "cloudify_scalelist.workflows._run_scale_settings",
                fake_run_scale
            ):
                workflows.scaledownlist(
                    ctx=_ctx,
                    scale_transaction_field='_transaction',
                    scale_node_name="a_type", scale_node_field="name",
                    scale_node_field_value="value"
                )
            fake_run_scale.assert_called_with(
                _ctx, {
                    'alfa_types': {
                        'instances': 54,
                        'removed_ids_include_hint': ['a_id', 'b_id']
                    }
                }, {}, instances_remove_ids=['a_id', 'b_id'],
                ignore_failure=False, node_sequence=None)

            # we have downscale issues
            fake_run_scale = Mock(side_effect=ValueError("No Down Scale!"))
            a_instance = Mock()
            a_instance.id = "a_id"
            c_instance = Mock()
            c_instance.id = "c_id"
            a_node = Mock()
            a_node.instances = [a_instance, c_instance]
            b_instance = Mock()
            b_instance.id = "b_id"
            b_node = Mock()
            b_node.instances = [b_instance]
            _ctx.nodes = [a_node, b_node]

            with patch(
                "cloudify_scalelist.workflows._run_scale_settings",
                fake_run_scale
            ):
                fake_uninstall_instances = Mock(return_value=None)
                with patch(
                    "cloudify_scalelist.workflows._uninstall_instances",
                    fake_uninstall_instances
                ):
                    workflows.scaledownlist(
                        ctx=_ctx,
                        scale_transaction_field='_transaction',
                        scale_node_name="a_type", scale_node_field="name",
                        scale_node_field_value="value",
                        force_db_cleanup=True
                    )
                fake_uninstall_instances.assert_called_with(
                    ctx=_ctx,
                    graph=_ctx.graph_mode(),
                    removed=[a_instance, b_instance],
                    related=[],
                    ignore_failure=False, node_sequence=None)
            fake_run_scale.assert_called_with(
                _ctx, {
                    'alfa_types': {
                        'instances': 54,
                        'removed_ids_include_hint': ['a_id', 'b_id']
                    }
                }, {}, instances_remove_ids=['a_id', 'b_id'],
                ignore_failure=False, node_sequence=None)

    def test_deployments_get_groups(self):
        _ctx = self._gen_ctx()
        client = self._gen_rest_client()
        client.deployments.get = Mock(return_value={
            'groups': {
                'one_scale': {
                    'members': ['one', 'two']
                }
            }
        })
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            self.assertEqual(
                workflows._deployments_get_groups(ctx=_ctx),
                {
                    'one_scale': {
                        'members': ['one', 'two']
                    }
                })

    def test_get_scale_list(self):
        _ctx = self._gen_ctx()
        client = self._gen_rest_client()
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            # Check wrong type of scalable_entity_properties
            with self.assertRaises(ValueError):
                workflows._get_scale_list(
                    ctx=_ctx,
                    scalable_entity_properties=['a', 'b'],
                    property_type=dict)
            # Check wrong type of scalable_entity_properties item
            with self.assertRaises(ValueError):
                workflows._get_scale_list(
                    ctx=_ctx,
                    scalable_entity_properties={'a': {'b': 'c'}},
                    property_type=dict)
            # string instead dict
            with self.assertRaises(ValueError):
                workflows._get_scale_list(
                    ctx=_ctx,
                    scalable_entity_properties={'a': ['b', 'c']},
                    property_type=dict)
            # correct values
            result = workflows._get_scale_list(
                ctx=_ctx,
                scalable_entity_properties={
                    'one': [{'name': 'one'}],
                    'two': [{'name': 'two'}],
                    'not_in_group': [{'name': 'separate'}],
                },
                property_type=dict
            )
            for k in result:
                result[k]['values'].sort()
            self.assertEqual(
                result,
                {
                    'one_scale': {
                        'count': 1,
                        'values': [{'name': 'one'},
                                   {'name': 'two'}]
                    },
                    'not_in_group': {
                        'count': 1,
                        'values': [{'name': 'separate'}]
                    }
                })

    def test_scaledown_group_to_settings(self):
        # scale groups names
        _ctx = self._gen_ctx()
        client = self._gen_rest_client()
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            self.assertEqual(
                workflows._scaledown_group_to_settings(
                    _ctx, {
                        'one_scale': {
                            'count': 1,
                            'values': [{'name': 'one'},
                                       {'name': 'two'}]
                        },
                        'second_scale': {
                            'count': 0,
                            'values': []
                        },

                    },
                    True
                ),
                {'one_scale': {
                    'instances': 9,
                    'removed_ids_include_hint': [
                        {'name': 'one'}, {'name': 'two'}]}}
            )

        # node names
        _ctx = self._gen_ctx()
        client = self._gen_rest_client()
        fake_node_parent = Mock()
        fake_node_parent.number_of_instances = 34
        fake_node_parent.id = "id_34"
        fake_node = Mock()
        fake_node.host_node = fake_node_parent
        fake_node.number_of_instances = 43
        fake_node.id = "id_43"
        _ctx.get_node = Mock(return_value=fake_node)
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            # get parent host
            self.assertEqual(
                workflows._scaledown_group_to_settings(
                    _ctx, {
                        'one': {
                            'count': 1,
                            'values': [{'name': 'one'}]
                        }
                    },
                    True
                ),
                {'id_34': {'instances': 33,
                           'removed_ids_include_hint': [{'name': 'one'}]}}
            )
            _ctx.get_node.assert_called_with('one')
            # get child
            self.assertEqual(
                workflows._scaledown_group_to_settings(
                    _ctx, {
                        'one': {
                            'count': 1,
                            'values': [{'name': 'one'}]
                        }
                    },
                    False
                ),
                {'id_43': {'instances': 42,
                           'removed_ids_include_hint': [{'name': 'one'}]}}
            )
            # no such node
            _ctx.get_node = Mock(return_value=None)
            with self.assertRaises(ValueError):
                workflows._scaledown_group_to_settings(
                    _ctx, {
                        'one': {
                            'count': 1,
                            'values': [{'name': 'one'}]
                        }
                    },
                    False
                )

    def test_get_transaction_instances_nosuch(self):
        _ctx = self._gen_ctx()
        client = self._gen_rest_client()
        # get all instances
        client.node_instances.list = Mock(return_value=[])
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            self.assertEqual(
                workflows._get_transaction_instances(
                    ctx=_ctx,
                    all_results=True,
                    scale_transaction_field='_transaction',
                    scale_node_names="a_type",
                    scale_node_field_path=["name"],
                    scale_node_field_values=["value"]
                ), ({}, [])
            )
            client.node_instances.list.assert_called_with(
                _include=['runtime_properties', 'node_id', 'id'],
                _get_all_results=True,
                deployment_id='deployment_id')
        # get only first page
        client.node_instances.list = Mock(return_value=[])
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            self.assertEqual(
                workflows._get_transaction_instances(
                    ctx=_ctx,
                    scale_transaction_field='_transaction',
                    scale_node_names="a_type",
                    scale_node_field_path=["name"],
                    scale_node_field_values=["value"]
                ), ({}, [])
            )
            client.node_instances.list.assert_called_with(
                _include=['runtime_properties', 'node_id', 'id'],
                deployment_id='deployment_id')

    def test_get_transaction_instances_notransaction(self):
        _ctx = self._gen_ctx()
        client = self._gen_rest_client()

        instance_a = Mock()
        instance_a.id = 'a_id'
        instance_a.node_id = 'a_type'
        instance_a.runtime_properties = {
            'name': 'value'
        }
        # get all instances
        client.node_instances.list = Mock(return_value=[instance_a])
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            self.assertEqual(
                workflows._get_transaction_instances(
                    ctx=_ctx,
                    scale_transaction_field='_transaction',
                    all_results=True,
                    scale_node_names="a_type", scale_node_field_path=["name"],
                    scale_node_field_values=["value"]
                ), ({'a_type': ['a_id']}, ['a_id'])
            )
            client.node_instances.list.assert_called_with(
                _include=['runtime_properties', 'node_id', 'id'],
                _get_all_results=True,
                deployment_id='deployment_id')
        # get only first page
        client.node_instances.list = Mock(return_value=[instance_a])
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            self.assertEqual(
                workflows._get_transaction_instances(
                    ctx=_ctx,
                    scale_transaction_field='_transaction',
                    scale_node_names="a_type", scale_node_field_path=["name"],
                    scale_node_field_values=["value"]
                ), ({'a_type': ['a_id']}, ['a_id'])
            )
            client.node_instances.list.assert_called_with(
                _include=['runtime_properties', 'node_id', 'id'],
                deployment_id='deployment_id')

    def test_get_transaction_instances_notransaction_field(self):
        _ctx = self._gen_ctx()
        client = self._gen_rest_client()

        instance_a = Mock()
        instance_a.id = 'a_id'
        instance_a.node_id = 'a_type'
        instance_a.runtime_properties = {
            'name': 'value'
        }
        # get all instances
        client.node_instances.list = Mock(return_value=[instance_a])
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            self.assertEqual(
                workflows._get_transaction_instances(
                    ctx=_ctx,
                    all_results=True,
                    scale_transaction_field=None,
                    scale_node_names=None, scale_node_field_path=["name"],
                    scale_node_field_values=["value"]
                ), ({'a_type': ['a_id']}, ['a_id'])
            )
            client.node_instances.list.assert_called_with(
                _include=['runtime_properties', 'node_id', 'id'],
                _get_all_results=True,
                deployment_id='deployment_id')
        # get only first page
        client.node_instances.list = Mock(return_value=[instance_a])
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            self.assertEqual(
                workflows._get_transaction_instances(
                    ctx=_ctx,
                    scale_transaction_field=None,
                    scale_node_names=None, scale_node_field_path=["name"],
                    scale_node_field_values=["value"]
                ), ({'a_type': ['a_id']}, ['a_id'])
            )
            client.node_instances.list.assert_called_with(
                _include=['runtime_properties', 'node_id', 'id'],
                deployment_id='deployment_id')

    def test_get_transaction_instances(self):
        _ctx = self._gen_ctx()

        client = self._gen_rest_client()
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            self.assertEqual(
                workflows._get_transaction_instances(
                    ctx=_ctx,
                    scale_transaction_field='_transaction',
                    scale_node_names=["a_type"],
                    scale_node_field_path=["name"],
                    scale_node_field_values=["value"]
                ), ({
                    'a_type': ['a_id'],
                    'b_type': ['b_id'],
                }, ['a_id', 'b_id'])
            )

    def test_uninstall_instances_relationships(self):
        _ctx = self._gen_ctx()
        a_instance = Mock()
        a_instance._node_instance.id = "a_id"
        c_instance = Mock()
        c_instance._node_instance.id = "c_id"
        a_node = Mock()
        a_node.instances = [a_instance, c_instance]
        b_instance = Mock()
        b_instance._node_instance.id = "b_id"
        b_node = Mock()
        b_node.instances = [b_instance]
        _ctx.nodes = [a_node, b_node]

        fake_uninstall_node_instances = Mock()

        with patch(
            "cloudify_scalelist.workflows.lifecycle.uninstall_node_instances",
            fake_uninstall_node_instances
        ):
            fake_cleanup_instances = Mock()
            with patch(
                "cloudify_scalelist.workflows._cleanup_instances",
                fake_cleanup_instances
            ):
                workflows._uninstall_instances(_ctx, _ctx.graph_mode(),
                                               [a_instance, b_instance],
                                               [c_instance],
                                               True,
                                               node_sequence=[])
            fake_cleanup_instances.assert_called_with(_ctx, ["a_id", "b_id"])
        fake_uninstall_node_instances.assert_called_with(
            graph=_ctx.graph_mode(),
            node_instances=[a_instance, b_instance],
            ignore_failure=True,
            related_nodes=[c_instance]
        )
        _ctx.graph_mode().remove_task.assert_called_with(
            _ctx.graph_mode().tasks_iter()[0])

    def test_uninstall_instances_sequence_calls(self):
        _ctx = self._gen_ctx()
        a_instance = Mock()
        a_instance._node_instance.id = "a_id"
        c_instance = Mock()
        c_instance._node_instance.id = "c_id"
        a_node = Mock()
        a_node.instances = [a_instance, c_instance]
        b_instance = Mock()
        b_instance._node_instance.id = "b_id"
        b_node = Mock()
        b_node.instances = [b_instance]
        _ctx.nodes = [a_node, b_node]

        fake_process_node_instances = Mock()

        with patch(
            "cloudify_scalelist.workflows._process_node_instances",
            fake_process_node_instances
        ):
            fake_cleanup_instances = Mock()
            with patch(
                "cloudify_scalelist.workflows._cleanup_instances",
                fake_cleanup_instances
            ):
                workflows._uninstall_instances(_ctx, _ctx.graph_mode(),
                                               [a_instance, b_instance],
                                               [c_instance],
                                               True,
                                               node_sequence=['a', 'b'])
            fake_cleanup_instances.assert_called_with(_ctx, ["a_id", "b_id"])

        call_func = workflows.lifecycle.uninstall_node_instance_subgraph
        fake_process_node_instances.assert_called_with(
            ctx=_ctx,
            graph=_ctx.graph_mode(),
            ignore_failure=True,
            node_instance_subgraph_func=call_func,
            node_instances=[a_instance, b_instance],
            node_sequence=['b', 'a']
        )
        _ctx.graph_mode().remove_task.assert_called_with(
            _ctx.graph_mode().tasks_iter()[0])

    def test_get_field_value_recursive(self):
        logger = Mock()
        # check list
        self.assertEqual(
            'a',
            filters.get_field_value_recursive(
                logger, ['a'], ['0'])
        )
        # not in list
        self.assertEqual(
            None,
            filters.get_field_value_recursive(
                logger, ['a'], ['1'])
        )
        # check dict
        self.assertEqual(
            'a',
            filters.get_field_value_recursive(
                logger, {'0': 'a'}, ['0'])
        )
        # not in dict
        self.assertEqual(
            None,
            filters.get_field_value_recursive(
                logger, {'0': 'a'}, ['1'])
        )
        # check dict in list
        self.assertEqual(
            'b',
            filters.get_field_value_recursive(
                logger, [{'a': 'b'}], ['0', 'a'])
        )
        # check dict in list
        self.assertEqual(
            None,
            filters.get_field_value_recursive(
                logger, 'a', ['1', 'a'])
        )

    def test_filter_node_instances(self):
        # everything empty
        _ctx = self._gen_ctx()
        self.assertEqual(
            workflows._filter_node_instances(
                ctx=_ctx,
                node_ids=[],
                node_instance_ids=[],
                type_names=[],
                operation='a.b.c',
                node_field_path=['a'],
                node_field_value=['b']
            ),
            []
        )
        # no such operation
        node = Mock()
        node.type_hierarchy = ['a_type']
        node.operations = ["c.b.a"]
        node.id = 'a'
        instance = Mock()
        instance.id = 'a'
        instance._node_instance.runtime_properties = {}
        node.instances = [instance]
        _ctx.nodes = [node]
        self.assertEqual(
            workflows._filter_node_instances(
                ctx=_ctx,
                node_ids=[],
                node_instance_ids=[],
                type_names=[],
                operation='a.b.c',
                node_field_path=['a'],
                node_field_value=['b']
            ),
            []
        )
        # no such field
        node.operations = ['c.b.a', 'a.b.c']
        self.assertEqual(
            workflows._filter_node_instances(
                ctx=_ctx,
                node_ids=[],
                node_instance_ids=[],
                type_names=[],
                operation='a.b.c',
                node_field_path=['a'],
                node_field_value=['b']
            ),
            []
        )
        # we have such value
        instance._node_instance.runtime_properties = {'a': 'b'}
        self.assertEqual(
            workflows._filter_node_instances(
                ctx=_ctx,
                node_ids=[],
                node_instance_ids=[],
                type_names=[],
                operation='a.b.c',
                node_field_path=['a'],
                node_field_value=['b']
            ),
            [instance]
        )
        # we have such value, but wrong instance_id
        instance.id = 'c'
        self.assertEqual(
            workflows._filter_node_instances(
                ctx=_ctx,
                node_ids=[],
                node_instance_ids=['a'],
                type_names=[],
                operation='a.b.c',
                node_field_path=['a'],
                node_field_value=['b']
            ),
            []
        )
        # we have such value, but wrong node_id
        node.id = 'c'
        self.assertEqual(
            workflows._filter_node_instances(
                ctx=_ctx,
                node_ids=['a'],
                node_instance_ids=[],
                type_names=[],
                operation='a.b.c',
                node_field_path=['a'],
                node_field_value=['b']
            ),
            []
        )
        # we have such value, but wrong type
        node.type_hierarchy = ['c_type']
        self.assertEqual(
            workflows._filter_node_instances(
                ctx=_ctx,
                node_ids=[],
                node_instance_ids=[],
                type_names=['a_type'],
                operation='a.b.c',
                node_field_path=['a'],
                node_field_value=['b']
            ),
            []
        )

    def test_execute_operation(self):
        _ctx = self._gen_ctx()
        # fake instance
        node_a = Mock()
        node_a.type_hierarchy = ['a_type']
        node_a.operations = ["a.b.c"]
        node_a.id = 'a'
        node_b = Mock()
        node_b.type_hierarchy = ['b_type']
        node_b.operations = ["a.b.c"]
        node_b.id = 'b'
        # fake nodes
        instance_a = Mock()
        instance_a.id = 'a'
        instance_a._node_instance.runtime_properties = {'c': 'd'}
        instance_a.relationships = []
        node_a.instances = [instance_a]
        instance_b = Mock()
        instance_b.id = 'b'
        instance_b._node_instance.runtime_properties = {'a': 'b'}
        relation_b_a = Mock()
        relation_b_a.target_id = 'a'
        relation_b_a.source_id = 'b'
        instance_b.relationships = [relation_b_a]
        node_b.instances = [instance_b]
        # context lists
        _ctx.node_instances = [instance_a, instance_b]
        _ctx.nodes = [node_a, node_b]
        # run executions
        workflows.execute_operation(
            ctx=_ctx,
            operation='a.b.c',
            operation_kwargs={'c': 'f'},
            allow_kwargs_override=True,
            run_by_dependency_order=True,
            type_names=[],
            node_ids=[],
            node_instance_ids=[],
            node_field='a',
            node_field_value='b'
        )
        _ctx._graph.add_dependency.assert_called_with(_ctx._subgraph[1],
                                                      _ctx._subgraph[0])


if __name__ == '__main__':
    unittest.main()
