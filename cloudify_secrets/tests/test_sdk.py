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

import json
import unittest

import mock

from cloudify_secrets.sdk import SecretsSDK


class TestSecretsSDK(unittest.TestCase):

    def setUp(self):
        self.secret_resource = {
            'key': 'some_key',
            'value': 'some_value',
            'created_at': '2019-02-11 11:47:21.105634',
            'updated_at': '2019-02-11 11:47:21.105634',
            'visibility': 'global',
            'is_hidden_value': False
        }

        self.rest_client_secrets_create_mock = mock.Mock(
            return_value=self.secret_resource
        )
        self.rest_client_secrets_patch_mock = mock.Mock(
            return_value=self.secret_resource
        )
        self.rest_client_secrets_delete_mock = mock.Mock(
            return_value=self.secret_resource
        )
        self.rest_client_secrets_get_mock = mock.Mock(
            return_value=self.secret_resource
        )
        self.rest_client_secrets_mock = mock.Mock()

        self.rest_client_secrets_mock.create = \
            self.rest_client_secrets_create_mock
        self.rest_client_secrets_mock.patch = \
            self.rest_client_secrets_patch_mock
        self.rest_client_secrets_mock.delete = \
            self.rest_client_secrets_delete_mock
        self.rest_client_secrets_mock.get = \
            self.rest_client_secrets_get_mock

        self.rest_client_mock = mock.Mock()
        self.rest_client_mock.secrets = self.rest_client_secrets_mock

    def test_create(self):
        # given
        first_key = 'some_key_1'
        first_value = 'BlahBlah'

        second_key = 'some_key_2'
        second_value = 12

        third_key = 'some_key_3'
        third_value = False

        fourth_key = 'some_key_4'
        fourth_value = {
            'test': {
                'test1': 'test',
                'test2': ['a', 'b']
            }
        }

        properties = {
            'entries': {
                first_key: first_value,
                second_key: second_value,
                third_key: third_value,
                fourth_key: fourth_value
            },
            'variant': 'lab1',
            'separator': '---'

        }

        # when
        sdk = SecretsSDK(mock.Mock(), self.rest_client_mock, **properties)
        result = sdk.create(**properties)

        # then
        expected_first_key = 'some_key_1---lab1'
        expected_second_key = 'some_key_2---lab1'
        expected_third_key = 'some_key_3---lab1'
        expected_fourth_key = 'some_key_4---lab1'

        expected_calls = [
            mock.call(key=expected_first_key, value=first_value),
            mock.call(key=expected_second_key, value=str(second_value)),
            mock.call(key=expected_third_key, value=str(third_value)),
            mock.call(key=expected_fourth_key, value=json.dumps(fourth_value))
        ]

        self.rest_client_secrets_create_mock.assert_has_calls(
            expected_calls,
            any_order=True
        )
        self.assertTrue(result, self.secret_resource)

    def test_create_no_variant(self):
        # given
        first_key = 'some_key_1'
        first_value = 'BlahBlah'

        second_key = 'some_key_2'
        second_value = 12

        third_key = 'some_key_3'
        third_value = False

        fourth_key = 'some_key_4'
        fourth_value = {
            'test': {
                'test1': 'test',
                'test2': ['a', 'b']
            }
        }

        properties = {
            'entries': {
                first_key: first_value,
                second_key: second_value,
                third_key: third_value,
                fourth_key: fourth_value
            }
        }

        # when
        sdk = SecretsSDK(mock.Mock(), self.rest_client_mock, **properties)
        result = sdk.create(**properties)

        # then
        expected_first_key = 'some_key_1'
        expected_second_key = 'some_key_2'
        expected_third_key = 'some_key_3'
        expected_fourth_key = 'some_key_4'

        expected_calls = [
            mock.call(key=expected_first_key, value=first_value),
            mock.call(key=expected_second_key, value=str(second_value)),
            mock.call(key=expected_third_key, value=str(third_value)),
            mock.call(key=expected_fourth_key, value=json.dumps(fourth_value))
        ]

        self.rest_client_secrets_create_mock.assert_has_calls(
            expected_calls,
            any_order=True
        )
        self.assertTrue(result, self.secret_resource)

    def test_update(self):
        # given
        first_key = 'some_key_1'
        first_value = 'BlahBlah'

        second_key = 'some_key_2'
        second_value = 12

        third_key = 'some_key_3'
        third_value = False

        fourth_key = 'some_key_4'
        fourth_value = {
            'test': {
                'test1': 'test',
                'test2': ['a', 'b']
            }
        }

        properties = {
            'entries': {
                first_key: first_value,
                second_key: second_value,
                third_key: third_value,
                fourth_key: fourth_value
            },
            'variant': 'lab1',
            'separator': '---'

        }

        # when
        sdk = SecretsSDK(mock.Mock(), self.rest_client_mock, **properties)
        result = sdk.update(**properties)

        # then
        expected_first_key = 'some_key_1---lab1'
        expected_second_key = 'some_key_2---lab1'
        expected_third_key = 'some_key_3---lab1'
        expected_fourth_key = 'some_key_4---lab1'

        expected_calls = [
            mock.call(key=expected_first_key, value=first_value),
            mock.call(key=expected_second_key, value=str(second_value)),
            mock.call(key=expected_third_key, value=str(third_value)),
            mock.call(key=expected_fourth_key, value=json.dumps(fourth_value))
        ]

        self.rest_client_secrets_patch_mock.assert_has_calls(
            expected_calls,
            any_order=True
        )
        self.assertTrue(result, self.secret_resource)

    def test_delete(self):
        # given
        first_key = 'some_key_1'
        first_value = 'BlahBlah'

        second_key = 'some_key_2'
        second_value = 12

        third_key = 'some_key_3'
        third_value = False

        fourth_key = 'some_key_4'
        fourth_value = {
            'test': {
                'test1': 'test',
                'test2': ['a', 'b']
            }
        }

        properties = {
            'secrets': {
                first_key: first_value,
                second_key: second_value,
                third_key: third_value,
                fourth_key: fourth_value
            },
            'variant': 'lab1',
            'separator': '---'

        }

        # when
        sdk = SecretsSDK(mock.Mock(), self.rest_client_mock, **properties)
        sdk.delete(**properties)

        # then
        expected_first_key = 'some_key_1---lab1'
        expected_second_key = 'some_key_2---lab1'
        expected_third_key = 'some_key_3---lab1'
        expected_fourth_key = 'some_key_4---lab1'

        expected_calls = [
            mock.call(key=expected_first_key),
            mock.call(key=expected_second_key),
            mock.call(key=expected_third_key),
            mock.call(key=expected_fourth_key)
        ]

        self.rest_client_secrets_delete_mock.assert_has_calls(
            expected_calls,
            any_order=True
        )

    def test_read(self):
        # given
        first_key = 'some_key_1'
        second_key = 'some_key_2'
        third_key = 'some_key_3'
        fourth_key = 'some_key_4'

        properties = {
            'keys': [first_key, second_key, third_key, fourth_key],
            'variant': 'lab1',
            'separator': '---'
        }

        # when
        sdk = SecretsSDK(mock.Mock(), self.rest_client_mock, **properties)
        result = sdk.read(**properties)

        # then
        expected_first_key = 'some_key_1---lab1'
        expected_second_key = 'some_key_2---lab1'
        expected_third_key = 'some_key_3---lab1'
        expected_fourth_key = 'some_key_4---lab1'

        expected_result = {
            first_key: self.secret_resource,
            second_key: self.secret_resource,
            third_key: self.secret_resource,
            fourth_key: self.secret_resource
        }

        expected_calls = [
            mock.call(key=expected_first_key),
            mock.call(key=expected_second_key),
            mock.call(key=expected_third_key),
            mock.call(key=expected_fourth_key)
        ]

        self.rest_client_secrets_get_mock.assert_has_calls(
            expected_calls,
            any_order=True
        )

        self.assertEquals(result, expected_result)
