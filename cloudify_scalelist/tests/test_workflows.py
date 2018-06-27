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

    def _gen_ctx(self):
        _ctx = MockCloudifyContext(
            deployment_id="deployment_id"
        )
        _ctx.deployment.scaling_groups = {
            'one_scale': {
                'members': ['one'],
                'properties': {'current_instances': 10}
            }
        }
        current_ctx.set(_ctx)
        return _ctx

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

    def test_scale_group_to_settings(self):
        _ctx = self._gen_ctx()
        client = self._gen_rest_client()
        with patch(
            "cloudify_scalelist.workflows.get_rest_client",
            Mock(return_value=client)
        ):
            self.assertEqual(
                workflows._scale_group_to_settings(
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
                }
            }
        })
        return client

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


if __name__ == '__main__':
    unittest.main()
