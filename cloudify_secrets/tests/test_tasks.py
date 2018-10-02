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
import mock
import copy

from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext
from cloudify_secrets import tasks


class TestTasks(unittest.TestCase):

    @staticmethod
    def _secret_resource(key, value):
        return {
            'key': key,
            'value': value,
            'created_at': '2019-02-11 11:47:21.105634',
            'updated_at': '2019-02-11 11:47:21.105634',
            'visibility': 'global',
            'is_hidden_value': False
        }

    def _mock_secrets(self):
        self.first_key = 'some_key_1'
        self.first_value = 'Test str'
        self.first_value_updated = 'Test str UPDATED'
        self.second_key = 'some_key_2'
        self.second_value = 12
        self.third_key = 'some_key_3'
        self.third_value = False
        self.fourth_key = 'some_key_4'
        self.fourth_value = {
            'test': {
                'test1': 'test',
                'test2': ['a', 'b']
            }
        }

        self.secrets = {
            self.first_key: self.first_value,
            self.second_key: self.second_value,
            self.third_key: self.third_value,
            self.fourth_key: self.fourth_value
        }

        self.secrets_with_details = {
            self.first_key:
                self._secret_resource(self.first_key, self.first_value),
            self.second_key:
                self._secret_resource(self.second_key, self.second_value),
            self.third_key:
                self._secret_resource(self.third_key, self.third_value),
            self.fourth_key:
                self._secret_resource(self.fourth_key, self.fourth_value)
        }

        self.secrets_with_details_updated = {
            self.first_key:
                self._secret_resource(
                    self.first_key,
                    self.first_value_updated
                ),
            self.second_key:
                self._secret_resource(self.second_key, self.second_value),
            self.third_key:
                self._secret_resource(self.third_key, self.third_value),
            self.fourth_key:
                self._secret_resource(self.fourth_key, self.fourth_value)
        }

    def _mock_writer_ctx(self, do_not_delete=False):
        properties = {
            'entries': {
                self.first_key: self.first_value,
                self.second_key: self.second_value,
                self.third_key: self.third_value,
                self.fourth_key: self.fourth_value
            },
            'variant': 'Lab_1',
            'separator': '---',
            'do_not_delete': do_not_delete
        }

        ctx = MockCloudifyContext(
            node_id='test_writer',
            properties=properties
        )

        current_ctx.set(ctx)
        return ctx

    def _mock_reader_ctx(self):
        properties = {
            'keys': ['some_key_1', 'some_key_2', 'some_key_3', 'some_key_4'],
            'variant': 'Lab_1',
            'separator': '---'
        }

        ctx = MockCloudifyContext(
            node_id='test_reader',
            properties=properties
        )

        current_ctx.set(ctx)
        return ctx

    def _mock_secrets_sdk(self):
        self.secrets_sdk_create_mock = mock.Mock(
            return_value=self.secrets_with_details
        )
        self.secrets_sdk_update_mock = mock.Mock(
            return_value=self.secrets_with_details_updated
        )
        self.secrets_sdk_delete_mock = mock.Mock()
        self.secrets_sdk_read_mock = mock.Mock(
            return_value=self.secrets_with_details
        )
        self.secrets_sdk_mock = mock.Mock()

        self.secrets_sdk_mock.create = \
            self.secrets_sdk_create_mock
        self.secrets_sdk_mock.update = \
            self.secrets_sdk_update_mock
        self.secrets_sdk_mock.delete = \
            self.secrets_sdk_delete_mock
        self.secrets_sdk_mock.read = \
            self.secrets_sdk_read_mock

        self.secrets_sdk_class_mock = mock.Mock(
            return_value=self.secrets_sdk_mock
        )

    def _mock_get_rest_client(self):
        self.get_rest_client_mock = mock.Mock()

    def setUp(self):
        self._mock_get_rest_client()
        self._mock_secrets()
        self._mock_secrets_sdk()

        tasks.get_rest_client = self.get_rest_client_mock
        tasks.SecretsSDK = self.secrets_sdk_class_mock

    def _do_test_create_delete(self, ctx, expected_do_not_delete=False):
        # given
        update_inputs = {
            'entries': {
                self.first_key: self.first_value_updated
            }
        }

        # when (create)
        tasks.create(ctx)

        # then (create)
        self.assertTrue('do_not_delete' in ctx.instance.runtime_properties)
        self.assertTrue('data' in ctx.instance.runtime_properties)

        self.assertEquals(
            ctx.instance.runtime_properties['do_not_delete'],
            expected_do_not_delete
        )
        self.assertEquals(
            ctx.instance.runtime_properties['data'],
            self.secrets_with_details
        )

        self.secrets_sdk_create_mock.assert_called_once_with(
            **ctx.node.properties
        )

        # when (update)
        tasks.update(ctx, **update_inputs)

        # then (update)
        self.assertTrue('do_not_delete' in ctx.instance.runtime_properties)
        self.assertTrue('data' in ctx.instance.runtime_properties)

        self.assertEquals(
            ctx.instance.runtime_properties['do_not_delete'],
            expected_do_not_delete
        )
        self.assertEquals(
            ctx.instance.runtime_properties['data'],
            self.secrets_with_details_updated
        )

        called_with = copy.deepcopy(ctx.node.properties)
        called_with['entries'] = {
            self.first_key: self.first_value_updated
        }
        self.secrets_sdk_update_mock.assert_called_once_with(
            **called_with
        )

    def test_create_update_delete(self):
        ctx = self._mock_writer_ctx()
        self._do_test_create_delete(ctx)

        # when (delete)
        tasks.delete(ctx)

        # then (delete)
        self.assertTrue(
            'do_not_delete' not in ctx.instance.runtime_properties
        )
        self.assertTrue('data' not in ctx.instance.runtime_properties)

        self.secrets_sdk_delete_mock.assert_called_once_with(
            self.secrets_with_details_updated,
            **ctx.node.properties
        )

    def test_create_update_delete__with_do_not_delete(self):
        ctx = self._mock_writer_ctx(True)
        self._do_test_create_delete(ctx, True)

        # when (delete)
        tasks.delete(ctx)

        # then (delete)
        self.assertTrue(
            'do_not_delete' not in ctx.instance.runtime_properties
        )
        self.assertTrue('data' not in ctx.instance.runtime_properties)

        self.assertFalse(self.secrets_sdk_delete_mock.called)

    def test_read(self):
        # given
        ctx = self._mock_reader_ctx()

        # when
        tasks.read(ctx)

        # then (create)
        self.assertTrue('do_not_delete' not in ctx.instance.runtime_properties)
        self.assertTrue('data' in ctx.instance.runtime_properties)

        self.assertEquals(
            ctx.instance.runtime_properties['data'],
            self.secrets_with_details
        )

        self.secrets_sdk_read_mock.assert_called_once_with(
            **ctx.node.properties
        )
