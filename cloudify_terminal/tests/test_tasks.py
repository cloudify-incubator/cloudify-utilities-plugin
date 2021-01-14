# Copyright (c) 2017-2019 Cloudify Platform Ltd. All rights reserved
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
from mock import (
    Mock,
    patch,
    call,
    PropertyMock)

from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import (
    NonRecoverableError, RecoverableError, OperationRetry
)
from cloudify.manager import DirtyTrackingDict

from .. import tasks

from cloudify_common_sdk import exceptions


class TestTasks(unittest.TestCase):

    def tearDown(self):
        current_ctx.clear()
        super(TestTasks, self).tearDown()

    def _gen_ctx(self):
        _ctx = MockCloudifyContext(
            'node_name',
            properties={},
        )

        _ctx._execution_id = "execution_id"
        _ctx.instance.host_ip = None
        _ctx.instance._runtime_properties = DirtyTrackingDict({})

        current_ctx.set(_ctx)
        return _ctx

    def _gen_relation_ctx(self):
        _target_ctx = MockCloudifyContext(
            'node_name',
            properties={},
            runtime_properties={}
        )
        _target_ctx.instance.host_ip = None

        _ctx = MockCloudifyContext(
            target=_target_ctx
        )
        _ctx._execution_id = "execution_id"

        current_ctx.set(_ctx)
        return _ctx

    @patch('time.sleep', Mock())
    def test_run_without_calls(self):
        _ctx = self._gen_ctx()
        _ctx._operation = Mock()
        for operation, state in [
            # mark create as finished
            ("cloudify.interfaces.lifecycle.create", {
                '_finished_operations': {
                    'cloudify.interfaces.lifecycle.create': True}}),
            # mark configure as finished
            ("cloudify.interfaces.lifecycle.configure", {
                '_finished_operations': {
                    'cloudify.interfaces.lifecycle.create': True,
                    "cloudify.interfaces.lifecycle.configure": True}}),
            # mark start as finished
            ("cloudify.interfaces.lifecycle.start", {
                '_finished_operations': {
                    'cloudify.interfaces.lifecycle.create': True,
                    "cloudify.interfaces.lifecycle.configure": True,
                    "cloudify.interfaces.lifecycle.start": True}}),
            # mark start ready for rerun
            ("cloudify.interfaces.lifecycle.stop", {
                '_finished_operations': {
                    'cloudify.interfaces.lifecycle.create': True,
                    "cloudify.interfaces.lifecycle.configure": True,
                    "cloudify.interfaces.lifecycle.start": False,
                    "cloudify.interfaces.lifecycle.stop": True}}),
            # cleanup runtime properties
            ("cloudify.interfaces.lifecycle.delete", {}),
        ]:
            # check
            _ctx._operation.name = operation
            tasks.run(ctx=_ctx)
            self.assertEqual(_ctx.instance.runtime_properties, state)
            # check rerun
            tasks.run(ctx=_ctx)
            self.assertEqual(_ctx.instance.runtime_properties, state)

    @patch('time.sleep', Mock())
    def test_run_without_auth(self):
        _ctx = self._gen_ctx()
        with self.assertRaises(NonRecoverableError):
            tasks.run(ctx=_ctx, calls=[{'action': 'ls'}])

    @patch('time.sleep', Mock())
    def test_run_auth(self):
        _ctx = self._gen_ctx()
        ssh_mock = Mock()
        ssh_mock.connect = Mock(side_effect=OSError("e"))
        try:
            type(_ctx.instance).host_ip = PropertyMock(
                side_effect=NonRecoverableError('host_ip is undefined'))
            with patch("paramiko.SSHClient", Mock(return_value=ssh_mock)):
                with self.assertRaises(OperationRetry):
                    tasks.run(
                        ctx=_ctx,
                        calls=[{'action': 'ls'}],
                        terminal_auth=json.loads(json.dumps(
                            {'ip': 'ip', 'user': 'user',
                             'password': 'password'})))
            ssh_mock.connect.assert_called_with(
                'ip', allow_agent=False, look_for_keys=False,
                password='password', port=22, timeout=5, username='user')
        finally:
            type(_ctx.instance).host_ip = None

    @patch('time.sleep', Mock())
    def test_run_auth_relationship(self):
        _ctx = self._gen_relation_ctx()
        ssh_mock = Mock()
        ssh_mock.connect = Mock(side_effect=OSError("e"))
        try:
            type(_ctx.target.instance).host_ip = PropertyMock(
                side_effect=NonRecoverableError('host_ip is undefined'))
            with patch("paramiko.SSHClient", Mock(return_value=ssh_mock)):
                with self.assertRaises(OperationRetry):
                    tasks.run(
                        ctx=_ctx,
                        calls=[{'action': 'ls'}],
                        logger_file="/tmp/terminal.log",
                        terminal_auth=json.loads(json.dumps(
                            {'ip': 'ip', 'user': 'user',
                             'password': 'password'})))
            ssh_mock.connect.assert_called_with(
                'ip', allow_agent=False, look_for_keys=False,
                password='password', port=22, timeout=5, username='user')
        finally:
            type(_ctx.target.instance).host_ip = None

    @patch('time.sleep', Mock())
    def test_run_auth_workflow_impicit_input(self):
        # wrong context type
        _ctx = Mock()
        _ctx.type = '<unknown>'
        ssh_mock = Mock()
        ssh_mock.connect = Mock(side_effect=OSError("e"))
        with patch("paramiko.SSHClient", Mock(return_value=ssh_mock)):
            with self.assertRaises(NonRecoverableError):
                tasks.run_as_workflow(
                    {},
                    ctx=_ctx,
                    calls=[{'action': 'ls'}],
                    logger_file="/tmp/terminal.log",
                    terminal_auth=json.loads(json.dumps(
                        {'ip': 'ip', 'user': 'user',
                         'password': 'password'})))

        # correct context type
        _ctx = Mock()
        _ctx.type = 'deployment'
        ssh_mock = Mock()
        ssh_mock.connect = Mock(side_effect=OSError("e"))
        with patch("paramiko.SSHClient", Mock(return_value=ssh_mock)):
            with self.assertRaises(OperationRetry):
                tasks.run_as_workflow(
                    {},
                    ctx=_ctx,
                    calls=[{'action': 'ls'}],
                    logger_file="/tmp/terminal.log",
                    terminal_auth=json.loads(json.dumps(
                        {'ip': 'ip', 'user': 'user',
                         'password': 'password'})))
        ssh_mock.connect.assert_called_with(
            'ip', allow_agent=False, look_for_keys=False, password='password',
            port=22, timeout=5, username='user')

    @patch('time.sleep', Mock())
    def test_run_auth_workflow_explicit_input(self):
        _ctx = Mock()
        _ctx.type = 'deployment'
        ssh_mock = Mock()
        ssh_mock.connect = Mock(side_effect=OSError("e"))
        with patch("paramiko.SSHClient", Mock(return_value=ssh_mock)):
            with self.assertRaises(OperationRetry):
                tasks.run_as_workflow(
                    inputs={},
                    ctx=_ctx,
                    calls=[{'action': 'ls'}],
                    logger_file="/tmp/terminal.log",
                    terminal_auth=json.loads(json.dumps(
                        {'ip': 'ip', 'user': 'user',
                         'password': 'password'})))
        ssh_mock.connect.assert_called_with(
            'ip', allow_agent=False, look_for_keys=False, password='password',
            port=22, timeout=5, username='user')

    @patch('time.sleep', Mock())
    def test_run_auth_with_host_ip(self):
        _ctx = self._gen_ctx()
        ssh_mock = Mock()
        ssh_mock.connect = Mock(side_effect=OSError("e"))
        with patch("paramiko.SSHClient", Mock(return_value=ssh_mock)):
            with self.assertRaises(OperationRetry):
                _ctx.instance.host_ip = 'ip'
                tasks.run(
                    ctx=_ctx,
                    calls=[{'action': 'ls'}],
                    terminal_auth=json.loads(json.dumps(
                        {'user': 'user',
                         'password': 'password'})))
        ssh_mock.connect.assert_called_with(
            'ip', allow_agent=False, look_for_keys=False, password='password',
            port=22, timeout=5, username='user')

    @patch('time.sleep', Mock())
    def test_run_auth_several_ips(self):
        _ctx = self._gen_ctx()
        ssh_mock = Mock()
        ssh_mock.connect = Mock(side_effect=OSError("e"))
        with patch("paramiko.SSHClient", Mock(return_value=ssh_mock)):
            with self.assertRaises(OperationRetry):
                tasks.run(
                    ctx=_ctx,
                    calls=[{'action': 'ls'}],
                    terminal_auth=json.loads(json.dumps(
                        {'ip': ['ip1', 'ip2'], 'user': 'user',
                         'password': 'password'})))
        ssh_mock.connect.assert_has_calls([call(
            'ip1', allow_agent=False, look_for_keys=False, password='password',
            port=22, timeout=5, username='user'), call(
            'ip2', allow_agent=False, look_for_keys=False, password='password',
            port=22, timeout=5, username='user')])

    @patch('time.sleep', Mock())
    def test_run_auth_enabled_logs(self):
        _ctx = self._gen_ctx()
        connection_mock = Mock()
        connection_mock.connect = Mock(side_effect=OSError("e"))
        with patch("cloudify_terminal_sdk.terminal_connection.RawConnection",
                   Mock(return_value=connection_mock)):
            with self.assertRaises(OperationRetry):
                tasks.run(
                    ctx=_ctx,
                    calls=[{'action': 'ls'}],
                    terminal_auth=json.loads(json.dumps(
                        {'ip': 'ip', 'user': 'user',
                         'password': 'password', 'store_logs': True})))
        connection_mock.connect.assert_called_with(
            'ip', 'user', 'password', None, 22,
            prompt_check=None, responses=[])

    @patch('time.sleep', Mock())
    def test_run_without_any_real_calls(self):
        _ctx = self._gen_ctx()
        connection_mock = Mock()
        connection_mock.connect = Mock(return_value="")
        connection_mock.run = Mock(return_value="")

        with patch("cloudify_terminal_sdk.terminal_connection.RawConnection",
                   Mock(return_value=connection_mock)):
            tasks.run(
                ctx=_ctx,
                calls=[{}],
                terminal_auth=json.loads(json.dumps(
                    {'ip': 'ip', 'user': 'user',
                     'password': 'password', 'store_logs': True})))

        connection_mock.run.assert_not_called()

    @patch('time.sleep', Mock())
    def test_run_run_without_save(self):
        _ctx = self._gen_ctx()
        connection_mock = Mock()
        connection_mock.connect = Mock(return_value="")
        connection_mock.run = Mock(return_value="localhost")

        with patch("cloudify_terminal_sdk.terminal_connection.RawConnection",
                   Mock(return_value=connection_mock)):
            tasks.run(
                ctx=_ctx,
                calls=[{'action': 'hostname'}],
                terminal_auth=json.loads(json.dumps(
                    {'ip': 'ip', 'user': 'user',
                     'password': 'password', 'store_logs': True})))

        connection_mock.run.assert_called_with(
            command='hostname',
            prompt_check=None,
            warning_examples=[],
            error_examples=[],
            critical_examples=[],
            responses=[])

        self.assertIsNone(
            _ctx.instance.runtime_properties.get('place_for_save'))

    @patch('time.sleep', Mock())
    def test_run_run_without_save_smart(self):
        _ctx = self._gen_ctx()
        connection_mock = Mock()
        connection_mock.connect = Mock(return_value="")
        connection_mock.run = Mock(return_value="localhost")

        with patch("cloudify_terminal_sdk.terminal_connection.SmartConnection",
                   Mock(return_value=connection_mock)):
            tasks.run(
                ctx=_ctx,
                calls=[{'action': 'hostname'}],
                terminal_auth=json.loads(json.dumps(
                    {'ip': 'ip', 'user': 'user',
                     'password': 'password', 'store_logs': True,
                     'smart_device': True})))

        connection_mock.run.assert_called_with(
            command='hostname',
            prompt_check=None,
            warning_examples=[],
            error_examples=[],
            critical_examples=[],
            responses=[])

        self.assertIsNone(
            _ctx.instance.runtime_properties.get('place_for_save'))

    @patch('time.sleep', Mock())
    def test_run_run_with_template(self):
        _ctx = self._gen_ctx()
        connection_mock = Mock()
        connection_mock.connect = Mock(return_value="")
        connection_mock.run = Mock(return_value="localhost")
        _ctx.get_resource = Mock(side_effect=[False, b"bb", b"{{ aa }}"])

        with patch("cloudify_terminal_sdk.terminal_connection.RawConnection",
                   Mock(return_value=connection_mock)):
            tasks.run(
                ctx=_ctx,
                calls=[{'template': '1.txt'},
                       {'template': '2.txt'},
                       {'template': '3.txt', 'params': {'aa': 'gg'}}],
                terminal_auth=json.loads(json.dumps(
                    {'ip': 'ip', 'user': 'user',
                     'password': 'password'})))

        connection_mock.run.assert_has_calls([
            call(command='bb', prompt_check=None, warning_examples=[],
                 error_examples=[], critical_examples=[], responses=[]),
            call(command='gg', prompt_check=None, warning_examples=[],
                 error_examples=[], critical_examples=[], responses=[])])

        self.assertIsNone(
            _ctx.instance.runtime_properties.get('place_for_save'))

    @patch('time.sleep', Mock())
    def test_run_run_with_text_template(self):
        _ctx = self._gen_ctx()
        connection_mock = Mock()
        connection_mock.connect = Mock(return_value="")
        connection_mock.run = Mock(return_value="localhost")

        with patch("cloudify_terminal_sdk.terminal_connection.RawConnection",
                   Mock(return_value=connection_mock)):
            tasks.run(
                ctx=_ctx,
                calls=[{'template_text': ""},
                       {'template_text': "bb"},
                       {'template_text': "{{ aa }}", 'params': {'aa': 'gg'}}],
                terminal_auth=json.loads(json.dumps(
                    {'ip': 'ip', 'user': 'user',
                     'password': 'password'})))

        connection_mock.run.assert_has_calls([
            call(command='bb', prompt_check=None, warning_examples=[],
                 error_examples=[], critical_examples=[], responses=[]),
            call(command='gg', prompt_check=None, warning_examples=[],
                 error_examples=[], critical_examples=[], responses=[])])

        self.assertIsNone(
            _ctx.instance.runtime_properties.get('place_for_save'))

    @patch('time.sleep', Mock())
    def test_run_with_save(self):
        _ctx = self._gen_ctx()
        connection_mock = Mock()
        connection_mock.connect = Mock(return_value="")
        connection_mock.run = Mock(return_value="localhost")

        with patch("cloudify_terminal_sdk.terminal_connection.RawConnection",
                   Mock(return_value=connection_mock)):
            tasks.run(
                ctx=_ctx,
                calls=[{'action': 'hostname\n \nls',
                        'save_to': 'place_for_save'}],
                terminal_auth=json.loads(json.dumps(
                    {'ip': 'ip', 'user': 'user',
                     'password': 'password', 'store_logs': True})))

        connection_mock.run.assert_has_calls([
            call(command='hostname', prompt_check=None, warning_examples=[],
                 error_examples=[], critical_examples=[], responses=[]),
            call(command='ls', prompt_check=None, warning_examples=[],
                 error_examples=[], critical_examples=[], responses=[])])
        self.assertEqual(
            _ctx.instance.runtime_properties.get('place_for_save'),
            'localhost\nlocalhost')

    @patch('time.sleep', Mock())
    def test_run_with_save_responses(self):
        _ctx = self._gen_ctx()
        connection_mock = Mock()
        connection_mock.connect = Mock(return_value="")
        connection_mock.run = Mock(return_value="localhost")

        with patch("cloudify_terminal_sdk.terminal_connection.RawConnection",
                   Mock(return_value=connection_mock)):
            tasks.run(
                ctx=_ctx,
                calls=[{'action': 'hostname', 'save_to': 'place_for_save',
                        'responses': [{'question': 'yes?', 'answer': 'no'}],
                        'errors': ['error'], 'promt_check': ['#']}],
                terminal_auth=json.loads(json.dumps(
                    {'ip': 'ip', 'user': 'user',
                     'password': 'password', 'store_logs': True})))

        connection_mock.run.assert_called_with(
            command='hostname',
            prompt_check=['#'],
            warning_examples=[],
            error_examples=['error'],
            critical_examples=[],
            responses=[{'question': 'yes?', 'answer': 'no'}])

        self.assertEqual(
            _ctx.instance.runtime_properties.get('place_for_save'),
            'localhost')

    @patch('time.sleep', Mock())
    def test_run_run_with_close(self):
        _ctx = self._gen_ctx()
        connection_mock = Mock()
        connection_mock.connect = Mock(return_value="")
        connection_mock.run = Mock(return_value="localhost")
        connection_mock.is_closed = Mock(side_effect=[False, True])

        with patch("cloudify_terminal_sdk.terminal_connection.RawConnection",
                   Mock(return_value=connection_mock)):
            tasks.run(
                ctx=_ctx,
                calls=[{}],
                terminal_auth=json.loads(json.dumps(
                    {'ip': 'ip', 'user': 'user',
                     'password': 'password', 'store_logs': True})))

        connection_mock.run.assert_has_calls([
            call(command='exit', prompt_check=None, warning_examples=[],
                 error_examples=[], critical_examples=[])])

        self.assertIsNone(
            _ctx.instance.runtime_properties.get('place_for_save')
        )

    @patch('time.sleep', Mock())
    def test_rerun(self):
        _ctx = self._gen_ctx()

        # code always return RecoverableWarning
        with self.assertRaises(
            RecoverableError
        ) as error:
            tasks.rerun(
                ctx=_ctx,
                func=Mock(
                    side_effect=exceptions.RecoverableWarning('A')
                ),
                args=[],
                kwargs={})

        self.assertEqual(str(error.exception), 'Failed to rerun: []:{}')

        # code always return NonRecoverable and call once
        func_call = Mock(side_effect=NonRecoverableError('A'))
        with self.assertRaises(
            NonRecoverableError
        ) as error:
            tasks.rerun(
                ctx=_ctx,
                func=func_call,
                args=[],
                kwargs={})
        func_call.assert_has_calls([call()])
        self.assertEqual(str(error.exception), 'A')

        # code always return RecoverableError and call once
        func_call = Mock(
            side_effect=exceptions.RecoverableError('A'))
        with self.assertRaises(
            RecoverableError
        ) as error:
            tasks.rerun(
                ctx=_ctx,
                func=func_call,
                args=[],
                kwargs={})
        func_call.assert_has_calls([call()])
        self.assertEqual(str(error.exception), 'A')

        # code always return NonRecoverableError and call once
        func_call = Mock(
            side_effect=exceptions.NonRecoverableError('A'))
        with self.assertRaises(
            NonRecoverableError
        ) as error:
            tasks.rerun(
                ctx=_ctx,
                func=func_call,
                args=[],
                kwargs={})
        func_call.assert_has_calls([call()])
        self.assertEqual(str(error.exception), 'A')


if __name__ == '__main__':
    unittest.main()
