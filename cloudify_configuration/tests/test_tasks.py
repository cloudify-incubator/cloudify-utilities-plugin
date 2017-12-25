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
        tasks.load_configuration({'a': 'b'}, False)
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
        tasks.load_configuration('{"a": "b"}', False)
        self.assertEqual(_ctx.instance.runtime_properties, {
            'params': {
                'a': 'b'
            }
        })

    def test_load_configuration_can_merge_dicts(self):
        _ctx = MockCloudifyContext(
            'node_name',
            properties={},
            runtime_properties={
              'params': {
                  'a': 'override_me',
                  'b': 'staying',
                  'dictionary': {
                      'key1': 'override_me',
                      'key2': 'i_should_stay'
                  }
                }
            }
        )
        current_ctx.set(_ctx)
        tasks.load_configuration({
            'a': 'overridden',
            'c': 'new',
            'dictionary': {
                'key1': 'overridden',
                'key3': 'new'
            }
        }, True)
        self.assertEqual(_ctx.instance.runtime_properties, {
            'params': {
                'a': 'overridden',
                'b': 'staying',
                'c': 'new',
                'dictionary': {
                    'key1': 'overridden',
                    'key2': 'i_should_stay',
                    'key3': 'new'
                }
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
        _currentinstance = MagicMock()

        _node = MagicMock()
        _instance = MagicMock()
        _relationship = MagicMock()

        _node_config = MagicMock()
        _instance_config = MagicMock()

        _node_config.id = 'configuration'
        _node_config.instances = [_instance_config]

        _instance.node = _node
        _instance.relationships = [_relationship]
        _relationship.target_id = _node_config.id
        _relationship.target_node_instance = _node_config
        _relationship.target_node_instance.node_id = _node_config.id
        _node.properties = {'params_list': ['a', 'c'],
                            'params': {'a': 'e', 'c': 'g'}}
        _node.type_hierarchy = ['juniper_node_config', 'cloudify.nodes.Root']
        _node.instances = [_instance]

        _currentinstance.runtime_properties = {
            'params': {
                'diff_params': ['a']
            }
        }

        _ctx.nodes = [_node, _node_config]

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
                    {'a': 'b'},
                    'configuration',
                    ['juniper_node_config', 'fortinet_vnf_type'],
                    False)

        _relationship.execute_target_operation.assert_called_with(
            tasks.LIFECYCLE_RELATIONSHIP_OPERATION_PRECONFIGURE
        )

        _instance_config.execute_operation.assert_called_with(
            tasks.LIFECYCLE_OPERATION_CONFIGURE,
            allow_kwargs_override=True,
            kwargs={'parameters': {'a': 'b'}, 'merge_dict': False}
        )

        _instance.execute_operation.assert_called_with(
            tasks.LIFECYCLE_OPERATION_UPDATE
        )


if __name__ == '__main__':
    unittest.main()
