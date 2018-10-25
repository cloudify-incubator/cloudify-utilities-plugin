########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
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
from cloudify.exceptions import RecoverableError, NonRecoverableError
from cloudify.mocks import MockCloudifyContext
from cloudify.state import current_ctx
import unittest
import requests_mock
import json
import os

from cloudify_rest import tasks
from mock import MagicMock
import logging


class TestPlugin(unittest.TestCase):
    def test_execute_http_no_exception(self):
        _ctx = MockCloudifyContext('node_name',
                                   properties={'hosts': ['--fake.cake--',
                                                         'test123.test'],
                                               'port': -1,
                                               'ssl': False,
                                               'verify': False},
                                   runtime_properties={})
        __location__ = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__)))
        with open(os.path.join(__location__, 'template1.yaml'), 'r') as f:
            template = f.read()
        _ctx.get_resource = MagicMock(return_value=template)
        _ctx.logger.setLevel(logging.DEBUG)
        current_ctx.set(_ctx)
        params = {'USER': 'testuser'}
        with requests_mock.mock(
                real_http=True) as m:  # real_http to check fake uri and get ex
            # call 1
            m.get('http://test123.test:80/testuser/test_rest/get',
                  json=json.load(
                      file(os.path.join(__location__, 'get_response1.json'),
                           'r')),
                  status_code=200)

            def _match_request_text(request):
                return '101' in (request.text or '')

            # call 2
            m.post('http://test123.test:80/test_rest/posts',
                   additional_matcher=_match_request_text,
                   request_headers={'Content-type': 'test/type'},
                   text='resp')

            # call 1
            m.get('http://test123.test:80/get',
                  json=json.load(
                      file(os.path.join(__location__, 'get_response2.json'),
                           'r')),
                  status_code=200)

            tasks.execute(params, 'mock_param')
            # _ctx = current_ctx.get_ctx()
            self.assertDictEqual(
                _ctx.instance.runtime_properties.get('result_properties'),
                {'nested_key0': u'nested_value1',
                 'nested_key1': u'nested_value2',
                 'id0': u'1',
                 'id1': u'101',
                 'owner1': {'id': 'Bob'},
                 'owner2': {'colour': 'red', 'name': 'bed', 'id': 'Carol'},
                 'owner0': {'colour': 'black', 'name': 'book'}})

    def test_execute_https_port_reco(self):
        _ctx = MockCloudifyContext('node_name',
                                   properties={'host': 'test123.test',
                                               'port': 12345,
                                               'ssl': 'true',
                                               'verify': True},
                                   runtime_properties={})
        __location__ = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__)))
        with open(os.path.join(__location__, 'template2.yaml'), 'r') as f:
            template = f.read()
        _ctx.get_resource = MagicMock(return_value=template)
        current_ctx.set(_ctx)
        with requests_mock.mock() as m:
            m.delete('https://test123.test:12345/v1/delete',
                     text='resp',
                     status_code=477)
            with self.assertRaises(RecoverableError) as context:
                tasks.execute({}, 'mock_param')
            self.assertTrue(
                'Response code 477 '
                'defined as recoverable' in context.exception.message)

    def test_execute_overwrite_host_response_expecation(self):
        _ctx = MockCloudifyContext('node_name',
                                   properties={'hosts': ['test123.test'],
                                               'port': 12345,
                                               'ssl': 'true',
                                               'verify': True},
                                   runtime_properties={})
        __location__ = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__)))
        with open(os.path.join(__location__, 'template3.yaml'), 'r') as f:
            template = f.read()
        _ctx.get_resource = MagicMock(return_value=template)
        _ctx.logger.setLevel(logging.DEBUG)
        current_ctx.set(_ctx)
        with requests_mock.mock() as m:
            m.put('https://hostfrom%20template.test:12345/v1/put_%20response3',
                  json=json.load(
                      file(os.path.join(__location__, 'put_response3.json'),
                           'r')),
                  status_code=200)
            with self.assertRaises(RecoverableError) as context:
                tasks.execute({}, 'mock_param')
            self.assertSequenceEqual(
                'Trying one more time...\n'
                "Response value:wrong_value "
                "does not match regexp: proper_value|good"
                " from response_expectation",
                str(context.exception.message))

    def test_execute_nonrecoverable_response(self):
        _ctx = MockCloudifyContext('node_name',
                                   properties={'hosts': ['test123.test'],
                                               'port': 12345,
                                               'ssl': 'true',
                                               'verify': True},
                                   runtime_properties={})
        __location__ = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__)))
        with open(os.path.join(__location__, 'template4.yaml'), 'r') as f:
            template = f.read()
        _ctx.get_resource = MagicMock(return_value=template)
        _ctx.logger.setLevel(logging.DEBUG)
        current_ctx.set(_ctx)
        with requests_mock.mock() as m:
            m.get('https://test123.test:12345/v1/get_response1',
                  json=json.load(
                      file(os.path.join(__location__, 'get_response1.json'),
                           'r')),
                  status_code=200)
            with self.assertRaises(NonRecoverableError) as context:
                tasks.execute({}, 'mock_param')
            self.assertSequenceEqual(
                'Giving up... \n'
                "Response value: active matches "
                "regexp:active from nonrecoverable_response. ",
                str(context.exception.message))

    def test_execute_http_xml(self):
        _ctx = MockCloudifyContext('node_name',
                                   properties={'hosts': ['test123.test'],
                                               'port': -1,
                                               'ssl': False,
                                               'verify': False},
                                   runtime_properties={})
        __location__ = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__)))
        with open(os.path.join(__location__, 'template5.yaml'), 'r') as f:
            template = f.read()
        _ctx.get_resource = MagicMock(return_value=template)
        _ctx.logger.setLevel(logging.DEBUG)
        current_ctx.set(_ctx)
        with requests_mock.mock() as m:
            m.get('http://test123.test:80/v1/get_response5',
                  text=file(os.path.join(__location__, 'get_response5.xml'),
                            'r').read(),
                  status_code=200)

            tasks.execute({}, 'mock_param')
            # _ctx = current_ctx.get_ctx()
            self.assertDictEqual(
                _ctx.instance.runtime_properties.get('result_properties'),
                {'UUID': '111111111111111111111111111111',
                 'CPUID': 'ABS:FFF222777'})

    def test_execute_jinja_block_parse(self):
        _ctx = MockCloudifyContext('node_name',
                                   properties={'hosts': ['test123.test'],
                                               'port': -1,
                                               'ssl': False,
                                               'verify': False},
                                   runtime_properties={})
        __location__ = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__)))
        with open(os.path.join(__location__, 'template6.yaml'), 'r') as f:
            template = f.read()
        _ctx.get_resource = MagicMock(return_value=template)
        _ctx.logger.setLevel(logging.DEBUG)
        current_ctx.set(_ctx)
        custom_list = [{'key1': 'val1'},
                       {'key2': 'val2'},
                       ['element1', 'element2']]
        params = {'custom_list': custom_list}

        with requests_mock.mock(
                real_http=True) as m:

            m.post('http://test123.test:80/v1/post_jinja_block',
                   text="resp")

            tasks.execute(params, 'mock_param')
            parsed_list = _ctx.instance.runtime_properties.get(
                'calls')[0].get('payload').get('jinja_block')
            self.assertListEqual(parsed_list, custom_list)
