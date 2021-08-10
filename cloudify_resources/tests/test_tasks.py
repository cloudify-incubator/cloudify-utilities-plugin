########
# Copyright (c) 2014-2019 Cloudify Platform Ltd. All rights reserved
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

from cloudify.state import current_ctx
from cloudify.mocks import (
    MockCloudifyContext,
    MockNodeContext,
    MockNodeInstanceContext,
    MockRelationshipContext,
    MockRelationshipSubjectContext
)
from cloudify_resources import tasks
from cloudify_resources.constants import (
    RESOURCES_LIST_PROPERTY,
    FREE_RESOURCES_LIST_PROPERTY,
    RESERVATIONS_PROPERTY,
    SINGLE_RESERVATION_PROPERTY
)


class TestTasks(unittest.TestCase):

    def _mock_resource_list_ctx(self):
        properties = {
            'resource_config': [
                '10.0.1.0/24',
                '10.0.2.0/24',
                '10.0.3.0/24'
            ]
        }

        ctx = MockCloudifyContext(
            node_id='test_resources',
            node_type='cloudify.nodes.resources.List',
            properties=properties
        )

        current_ctx.set(ctx)
        return ctx

    def _mock_resource_list_item_ctx(self):
        ctx = MockCloudifyContext(
            node_id='test_item',
            node_type='cloudify.nodes.resources.ListItem'
        )

        current_ctx.set(ctx)
        return ctx

    def _mock_item_to_resources_list_rel_ctx(self):
        # target
        tar_rel_subject_ctx = MockRelationshipSubjectContext(
            node=MockNodeContext(
                id='test_resources',
                type='cloudify.nodes.resources.List',
                properties={
                    'resource_config': [
                        '10.0.1.0/24',
                        '10.0.2.0/24',
                        '10.0.3.0/24'
                    ]
                }
            ),
            instance=MockNodeInstanceContext(
                id='test_resources_123456',
                runtime_properties={},
            )
        )

        rel_ctx = MockRelationshipContext(
            type='cloudify.relationships.resources.reserve_list_item',
            target=tar_rel_subject_ctx
        )

        # source
        src_ctx = MockCloudifyContext(
            node_id='test_item_123456',
            node_type='cloudify.nodes.resources.ListItem',
            source=self,
            target=tar_rel_subject_ctx,
            relationships=rel_ctx
        )

        current_ctx.set(src_ctx)
        return src_ctx

    def test_create_delete_resources_list(self):
        ctx = self._mock_resource_list_ctx()

        # when (create)
        tasks.create_list(ctx)

        # then (create)
        self.assertTrue(
            RESOURCES_LIST_PROPERTY in ctx.instance.runtime_properties)
        self.assertTrue(
            FREE_RESOURCES_LIST_PROPERTY in ctx.instance.runtime_properties)
        self.assertTrue(
            RESERVATIONS_PROPERTY in ctx.instance.runtime_properties)

        self.assertEquals(
            ctx.instance.runtime_properties[RESOURCES_LIST_PROPERTY],
            ctx.node.properties['resource_config']
        )

        self.assertEquals(
            ctx.instance.runtime_properties[FREE_RESOURCES_LIST_PROPERTY],
            ctx.instance.runtime_properties[RESOURCES_LIST_PROPERTY]
        )

        self.assertEquals(
            ctx.instance.runtime_properties[RESERVATIONS_PROPERTY],
            {}
        )

        # when (delete)
        tasks.delete_list(ctx)

        # then (delete)
        self.assertEquals(
            ctx.instance.runtime_properties[RESOURCES_LIST_PROPERTY],
            []
        )

        self.assertEquals(
            ctx.instance.runtime_properties[FREE_RESOURCES_LIST_PROPERTY],
            []
        )

        self.assertEquals(
            ctx.instance.runtime_properties[RESERVATIONS_PROPERTY],
            {}
        )

    def test_create_delete_resources_list_item(self):
        ctx = self._mock_resource_list_item_ctx()
        # when (create)
        tasks.create_list_item(ctx)

        # then (create)
        self.assertTrue(
            SINGLE_RESERVATION_PROPERTY in ctx.instance.runtime_properties)

        self.assertEquals(
            ctx.instance.runtime_properties[SINGLE_RESERVATION_PROPERTY],
            ''
        )

        # when (delete)
        tasks.delete_list_item(ctx)

        # then (delete)
        self.assertEquals(
            ctx.instance.runtime_properties[SINGLE_RESERVATION_PROPERTY],
            ''
        )

    # def test_reserve_return_resource(self):
    #     ctx = self._mock_item_to_resources_list_rel_ctx()

    #     # when (reserve)
    #     tasks.reserve_list_item(ctx)

    #     # then (reserve)
    #     self.assertEquals(
    #         ctx.source.instance.runtime_properties.get(
    #             SINGLE_RESERVATION_PROPERTY),
    #         '10.0.1.0/24'
    #     )
    #     self.assertEquals(
    #         ctx.target.instance.runtime_properties.get(
    #             RESERVATIONS_PROPERTY),
    #         {
    #             'test_item_123456': '10.0.1.0/24'
    #         }
    #     )
    #     self.assertEquals(
    #         ctx.target.instance.runtime_properties.get(
    #             FREE_RESOURCES_LIST_PROPERTY),
    #         [
    #             '10.0.2.0/24',
    #             '10.0.3.0/24'
    #         ]
    #     )
    #     self.assertEquals(
    #         ctx.target.instance.runtime_properties.get(
    #             RESOURCES_LIST_PROPERTY),
    #         [
    #             '10.0.1.0/24',
    #             '10.0.2.0/24',
    #             '10.0.3.0/24'
    #         ]
    #     )

    #     # when (return)
    #     tasks.return_list_item(ctx)

    #     # then (return)
    #     self.assertEquals(
    #         ctx.source.instance.runtime_properties.get(
    #             SINGLE_RESERVATION_PROPERTY),
    #         ''
    #     )
    #     self.assertEquals(
    #         ctx.target.instance.runtime_properties.get(
    #             RESERVATIONS_PROPERTY),
    #         {}
    #     )
    #     self.assertEquals(
    #         ctx.target.instance.runtime_properties.get(
    #             FREE_RESOURCES_LIST_PROPERTY),
    #         [
    #             '10.0.1.0/24',
    #             '10.0.2.0/24',
    #             '10.0.3.0/24'
    #         ]
    #     )
    #     self.assertEquals(
    #         ctx.target.instance.runtime_properties.get(
    #             RESOURCES_LIST_PROPERTY),
    #         [
    #             '10.0.1.0/24',
    #             '10.0.2.0/24',
    #             '10.0.3.0/24'
    #         ]
    #     )
