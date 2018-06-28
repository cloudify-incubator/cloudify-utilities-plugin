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
from mock import Mock, patch

from cloudify.mocks import MockCloudifyContext
from cloudify.state import current_ctx

import cloudify_scalelist.workflows as workflows


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

    def _gen_ctx(self):
        _ctx = MockCloudifyContext(
            deployment_id="deployment_id"
        )
        _graph = Mock()
        _graph.id = 'i_am_graph'
        _graph.tasks_iter = Mock(return_value=['task1'])
        _graph.remove_task = Mock(return_value=None)

        _ctx.graph_mode = Mock(return_value=_graph)
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

        # no noes with such value
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
                scale_node_name="node", scale_node_field="name",
                scale_node_field_value="value"
            )
            client.node_instances.list.assert_called_with(
                _include=['runtime_properties'],
                deployment_id='deployment_id',
                node_id='node')

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
            # can downscale without errors
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
                'transaction_value', False)

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
                with self.assertRaisesRegexp(
                    Exception,
                    "Instance 'a' not in proposed list \['b'\]."
                ):
                    workflows._run_scale_settings(_ctx, scale_settings, {},
                                                  instances_remove_ids=['b'])
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
                        workflows._run_scale_settings(_ctx, scale_settings,
                                                      {})
                fake_uninstall_instances.assert_called_with(_ctx,
                                                            _ctx.graph_mode(),
                                                            ['a'], ['f'],
                                                            False)
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
                    scale_node_name="a", scale_node_field="name",
                    scale_node_field_value="value"
                )
            fake_run_scale.assert_called_with(
                _ctx, {
                    'alfa_types': {
                        'instances': 54,
                        'removed_ids_include_hint': ['a_id', 'b_id']
                    }
                }, {}, instances_remove_ids=['a_id', 'b_id'],
                ignore_failure=False)

            # we have downscale issues
            fake_run_scale = Mock(side_effect=ValueError("No Down Scale!"))
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
                        scale_node_name="a", scale_node_field="name",
                        scale_node_field_value="value"
                    )
                fake_uninstall_instances.assert_called_with(_ctx,
                                                            _ctx.graph_mode(),
                                                            ['a_id', 'b_id'],
                                                            [],
                                                            False)
            fake_run_scale.assert_called_with(
                _ctx, {
                    'alfa_types': {
                        'instances': 54,
                        'removed_ids_include_hint': ['a_id', 'b_id']
                    }
                }, {}, instances_remove_ids=['a_id', 'b_id'],
                ignore_failure=False)

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
            result = workflows._get_scale_list(
                ctx=_ctx,
                scalable_entity_properties={
                    'one': [{'name': 'one'}],
                    'two': [{'name': 'two'}],
                    'not_in_group': [{'name': 'separate'}],
                }
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
        client.node_instances.list = Mock(return_value=[])
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            self.assertEqual(
                workflows._get_transaction_instances(
                    ctx=_ctx,
                    scale_transaction_field='_transaction',
                    scale_node_name="node", scale_node_field="name",
                    scale_node_field_value="value"
                ), ({}, [])
            )
            client.node_instances.list.assert_called_with(
                _include=['runtime_properties'],
                deployment_id='deployment_id',
                node_id='node')

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
                    scale_node_name="a", scale_node_field="name",
                    scale_node_field_value="value"
                ), ({
                    'a_type': ['a_id'],
                    'b_type': ['b_id'],
                }, ['a_id', 'b_id'])
            )

    def test_uninstall_instances(self):
        _ctx = self._gen_ctx()
        a_instance = Mock()
        a_instance.id = "a_id"
        a_node = Mock()
        c_instance = Mock()
        c_instance.id = "c_id"
        a_node = Mock()
        a_node.instances = [a_instance, c_instance]
        _ctx.nodes = [a_node]

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
                                               ["a_id", "b_id"], ["c_id"],
                                               True)
            fake_cleanup_instances.assert_called_with(_ctx, ["a_id", "b_id"])
        fake_uninstall_node_instances.assert_called_with(
            graph=_ctx.graph_mode(),
            node_instances=[a_instance],
            ignore_failure=True,
            related_nodes=[c_instance]
        )
        _ctx.graph_mode().remove_task.assert_called_with('task1')


if __name__ == '__main__':
    unittest.main()
