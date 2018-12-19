# Should be removed after full split code to cloudify-utilities-plugins-sdk

########
# Copyright (c) 2014-2018 Cloudify Platform Ltd. All rights reserved
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
from cloudify_rest_sdk import utility
import json


class TestSdk(unittest.TestCase):

    def test__check_if_v2(self):
        self.assertTrue(utility._check_if_v2([[['id'], ['params', 'id']],
                                              [['type', '{{actor}}', 'id'],
                                               ['aktorowe', 'id']]]))

    def test_translate_and_save_v2(self):
        response_translation = \
            [[['id'], ['params', 'id']], [['payload', 'pages'], ['pages']]]
        jl = json.loads('''{
            "id": "6857017661",
            "payload": {
                "pages": [
                    {
                        "page_name": "marvin",
                        "action": "edited",
                        "properties" :
                        {
                            "color" : "blue"
                        }
                    },
                    {
                        "page_name": "cool_wool",
                        "action": "saved",
                        "properties" :
                        {
                            "color" : "red"
                        }
                    }
                ]
            }
        }''')
        runtime_props = {}
        response_translation = [[
            ['payload', 'pages', ['page_name']],
            ['pages', ['page_name']]
        ]]
        utility._translate_and_save_v2(jl, response_translation, runtime_props)

    def test_prepare_runtime_props_path_for_list(self):
        self.assertListEqual(
            utility._prepare_runtime_props_path_for_list(
                ['key1', ['k2', 'k3']], 2),
            ['key1', 2, 'k2', 'k3'])

        self.assertListEqual(
            utility._prepare_runtime_props_path_for_list(
                ['key1', 'k2', 'k3'],
                1),
            ['key1', 'k2', 'k3', 1])

        self.assertListEqual(
            utility._prepare_runtime_props_path_for_list(
                ['key1', ['k2', ['k3']]],
                2),
            ['key1', 2, 'k2', ['k3']])

        self.assertListEqual(
            utility._prepare_runtime_props_path_for_list(
                ['key1', 'k2', ['k3']], 1),
            ['key1', 'k2', 1, 'k3'])

    def test_prepare_runtime_props_for_list(self):
        runtime_props = {}
        utility._prepare_runtime_props_for_list(runtime_props,
                                                ['key1', ['k2', 'k3']], 2)
        self.assertDictEqual(runtime_props, {'key1': [{}, {}]})

        runtime_props = {}
        utility._prepare_runtime_props_for_list(runtime_props,
                                                ['k1', 'k2', 'k3'], 5)

        self.assertDictEqual(runtime_props, {
            'k1': {'k2': {'k3': [{}, {}, {}, {}, {}]}}})
