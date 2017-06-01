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
import unittest
from mock import MagicMock, patch

from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext

import cloudify_configuration.tasks as tasks


class TestTasks(unittest.TestCase):

    def tearDown(self):
        current_ctx.clear()
        super(TestTasks, self).tearDown()

    def test_load_configuration(self):
        _ctx = MockCloudifyContext(
            'node_name',
            properties={},
            runtime_properties={}
        )
        current_ctx.set(_ctx)
        tasks.load_configuration({'a': 'b'})
        self.assertEqual(_ctx.instance.runtime_properties, {
            'params': {
                'a': 'b'
            }
        })

    def test_load_json_configuration(self):
        _ctx = MockCloudifyContext(
            'node_name',
            properties={},
            runtime_properties={}
        )
        current_ctx.set(_ctx)
        tasks.load_configuration('{"a": "b"}')
        self.assertEqual(_ctx.instance.runtime_properties, {
            'params': {
                'a': 'b'
            }
        })

    def test_load_configuration_to_runtime_properties(self):
        _source_ctx = MockCloudifyContext(
            'source_name',
            properties={'params_list': ['a', 'c'],
                        'params': {'a': 'e', 'c': 'g'}},
            runtime_properties={
                'params': {'a': 'n', 'c': 'g'}
            }
        )
        _target_ctx = MockCloudifyContext(
            'source_name',
            properties={},
            runtime_properties={}
        )
        _ctx = MockCloudifyContext(
            deployment_id='relationship_name',
            properties={},
            source=_source_ctx,
            target=_target_ctx,
            runtime_properties={}
        )
        current_ctx.set(_ctx)
        tasks.load_configuration_to_runtime_properties(
            source_config={"a": "b", 'c': 'g'}
        )

        self.assertEqual(_ctx.source.instance.runtime_properties, {
            'params': {
                'a': 'e',
                'diff_params': ['a'],
                'c': 'g',
                'old_params': {'a': 'n', 'c': 'g', 'old_params': {}}
            }
        })

    def test_update(self):
        _ctx = MagicMock()
        _node = MagicMock()
        _nodes_config = MagicMock()
        _instance = MagicMock()
        _instance_config = MagicMock()
        _currentinstance = MagicMock()
        _relationship_config = MagicMock()

        _node.type_hierarchy = ['configuration_loader', 'cloudify.nodes.Root']
        _node.instances = [_instance]

        _nodes_config.type_hierarchy = ['juniper_node_config',
                                        'cloudify.nodes.Root']
        _nodes_config.instances = [_instance_config]
        _instance_config.relationships = [_relationship_config]
        _instance_config.id = 'id_for_search'
        _currentinstance.runtime_properties = {
            'params': {
                'diff_params': ['a']
            }
        }

        _ctx.nodes = [_node, _nodes_config]

        _workflow_ctx = MagicMock()
        _workflow_ctx.get_ctx = MagicMock(return_value=_ctx)

        _manager_client = MagicMock()
        _manager_client.node_instances.get = MagicMock(
            return_value=_currentinstance
        )

        with patch('cloudify.state.current_workflow_ctx', _workflow_ctx):
            with patch(
                'cloudify.manager.get_rest_client',
                MagicMock(return_value=_manager_client)
            ):
                tasks.update(
                    {'a': 'b'}, 'configuration_loader',
                    ['juniper_node_config', 'fortinet_vnf_type'])

        _relationship_config.execute_target_operation.assert_called_with(
            'cloudify.interfaces.relationship_lifecycle.preconfigure'
        )

        _manager_client.node_instances.get.assert_called_with('id_for_search')

        _instance.execute_operation.assert_called_with(
            'cloudify.interfaces.lifecycle.configure',
            allow_kwargs_override=True, kwargs={'parameters': {'a': 'b'}})

        _instance_config.execute_operation.assert_called_with(
            'cloudify.interfaces.lifecycle.update'
        )


if __name__ == '__main__':
    unittest.main()
