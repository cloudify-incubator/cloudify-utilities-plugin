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
from mock import MagicMock, patch, call

from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError, OperationRetry

import cloudify_terminal.tasks as tasks


class TestTasks(unittest.TestCase):

    def tearDown(self):
        current_ctx.clear()
        super(TestTasks, self).tearDown()

    def _gen_ctx(self):
        _ctx = MockCloudifyContext(
            'node_name',
            properties={},
            runtime_properties={}
        )

        _ctx._execution_id = "execution_id"
        _ctx.instance.host_ip = None

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

    def test_run_without_calls(self):
        self._gen_ctx()
        tasks.run()

    def test_run_without_auth(self):
        self._gen_ctx()
        with self.assertRaises(NonRecoverableError):
            tasks.run(calls=[{'action': 'ls'}])

    def test_run_auth(self):
        self._gen_ctx()
        ssh_mock = MagicMock()
        ssh_mock.connect = MagicMock(side_effect=OSError("e"))
        with patch("paramiko.SSHClient", MagicMock(return_value=ssh_mock)):
            with self.assertRaises(OperationRetry):
                tasks.run(
                    calls=[{'action': 'ls'}],
                    terminal_auth={'ip': 'ip', 'user': 'user',
                                   'password': 'password'}
                )
        ssh_mock.connect.assert_called_with(
            'ip', allow_agent=False, look_for_keys=False, password='password',
            port=22, timeout=5, username='user')

    def test_run_auth_relationship(self):
        self._gen_relation_ctx()
        ssh_mock = MagicMock()
        ssh_mock.connect = MagicMock(side_effect=OSError("e"))
        with patch("paramiko.SSHClient", MagicMock(return_value=ssh_mock)):
            with self.assertRaises(OperationRetry):
                tasks.run(
                    calls=[{'action': 'ls'}],
                    terminal_auth={'ip': 'ip', 'user': 'user',
                                   'password': 'password'}
                )
        ssh_mock.connect.assert_called_with(
            'ip', allow_agent=False, look_for_keys=False, password='password',
            port=22, timeout=5, username='user')

    def test_run_auth_with_host_ip(self):
        _ctx = self._gen_ctx()
        ssh_mock = MagicMock()
        ssh_mock.connect = MagicMock(side_effect=OSError("e"))
        with patch("paramiko.SSHClient", MagicMock(return_value=ssh_mock)):
            with self.assertRaises(OperationRetry):
                _ctx.instance.host_ip = 'ip'
                tasks.run(
                    calls=[{'action': 'ls'}],
                    terminal_auth={'user': 'user',
                                   'password': 'password'}
                )
        ssh_mock.connect.assert_called_with(
            'ip', allow_agent=False, look_for_keys=False, password='password',
            port=22, timeout=5, username='user')

    def test_run_auth_several_ips(self):
        self._gen_ctx()
        ssh_mock = MagicMock()
        ssh_mock.connect = MagicMock(side_effect=OSError("e"))
        with patch("paramiko.SSHClient", MagicMock(return_value=ssh_mock)):
            with self.assertRaises(OperationRetry):
                tasks.run(
                    calls=[{'action': 'ls'}],
                    terminal_auth={'ip': ['ip1', 'ip2'], 'user': 'user',
                                   'password': 'password'}
                )
        ssh_mock.connect.assert_has_calls([call(
            'ip1', allow_agent=False, look_for_keys=False, password='password',
            port=22, timeout=5, username='user'), call(
            'ip2', allow_agent=False, look_for_keys=False, password='password',
            port=22, timeout=5, username='user')])

    def test_run_auth_enabled_logs(self):
        _ctx = self._gen_ctx()
        connection_mock = MagicMock()
        connection_mock.connect = MagicMock(side_effect=OSError("e"))
        with patch("cloudify_terminal.terminal_connection.connection",
                   MagicMock(return_value=connection_mock)):
            with self.assertRaises(OperationRetry):
                tasks.run(
                    calls=[{'action': 'ls'}],
                    terminal_auth={'ip': 'ip', 'user': 'user',
                                   'password': 'password', 'store_logs': True}
                )
        connection_mock.connect.assert_called_with(
            'ip', 'user', 'password', None, 22, None,
            log_file_name='/tmp/terminal-execution_id_node_name_None.log',
            logger=_ctx.logger)

    def test_run_without_any_real_calls(self):
        self._gen_ctx()
        connection_mock = MagicMock()
        connection_mock.connect = MagicMock(return_value="")
        connection_mock.run = MagicMock(return_value="")

        with patch("cloudify_terminal.terminal_connection.connection",
                   MagicMock(return_value=connection_mock)):
            tasks.run(
                calls=[{}],
                terminal_auth={'ip': 'ip', 'user': 'user',
                               'password': 'password', 'store_logs': True}
            )

        connection_mock.run.assert_not_called()

    def test_run_run_without_save(self):
        _ctx = self._gen_ctx()
        connection_mock = MagicMock()
        connection_mock.connect = MagicMock(return_value="")
        connection_mock.run = MagicMock(return_value="localhost")

        with patch("cloudify_terminal.terminal_connection.connection",
                   MagicMock(return_value=connection_mock)):
            tasks.run(
                calls=[{'action': 'hostname'}],
                terminal_auth={'ip': 'ip', 'user': 'user',
                               'password': 'password', 'store_logs': True}
            )

        connection_mock.run.assert_called_with('hostname', None, None, [])

        self.assertIsNone(
            _ctx.instance.runtime_properties.get('place_for_save'))

    def test_run_run_with_template(self):
        _ctx = self._gen_ctx()
        connection_mock = MagicMock()
        connection_mock.connect = MagicMock(return_value="")
        connection_mock.run = MagicMock(return_value="localhost")
        _ctx.get_resource = MagicMock(side_effect=[False, "bb", "{{ aa }}"])

        with patch("cloudify_terminal.terminal_connection.connection",
                   MagicMock(return_value=connection_mock)):
            tasks.run(
                calls=[{'template': '1.txt'},
                       {'template': '2.txt'},
                       {'template': '3.txt', 'params': {'aa': 'gg'}}],
                terminal_auth={'ip': 'ip', 'user': 'user',
                               'password': 'password'}
            )

        connection_mock.run.assert_has_calls([call('bb', None, None, []),
                                              call('gg', None, None, [])])

        self.assertIsNone(
            _ctx.instance.runtime_properties.get('place_for_save'))

    def test_run_run_with_text_template(self):
        _ctx = self._gen_ctx()
        connection_mock = MagicMock()
        connection_mock.connect = MagicMock(return_value="")
        connection_mock.run = MagicMock(return_value="localhost")

        with patch("cloudify_terminal.terminal_connection.connection",
                   MagicMock(return_value=connection_mock)):
            tasks.run(
                calls=[{'template_text': ""},
                       {'template_text': "bb"},
                       {'template_text': "{{ aa }}", 'params': {'aa': 'gg'}}],
                terminal_auth={'ip': 'ip', 'user': 'user',
                               'password': 'password'}
            )

        connection_mock.run.assert_has_calls([call('bb', None, None, []),
                                              call('gg', None, None, [])])

        self.assertIsNone(
            _ctx.instance.runtime_properties.get('place_for_save'))

    def test_run_with_save(self):
        _ctx = self._gen_ctx()
        connection_mock = MagicMock()
        connection_mock.connect = MagicMock(return_value="")
        connection_mock.run = MagicMock(return_value="localhost")

        with patch("cloudify_terminal.terminal_connection.connection",
                   MagicMock(return_value=connection_mock)):
            tasks.run(
                calls=[{'action': 'hostname\n \nls',
                        'save_to': 'place_for_save'}],
                terminal_auth={'ip': 'ip', 'user': 'user',
                               'password': 'password', 'store_logs': True}
            )

        connection_mock.run.assert_has_calls([call('hostname', None, None, []),
                                              call('ls', None, None, [])])

        self.assertEqual(
            _ctx.instance.runtime_properties.get('place_for_save'),
            'localhost\nlocalhost')

    def test_run_with_save_responses(self):
        _ctx = self._gen_ctx()
        connection_mock = MagicMock()
        connection_mock.connect = MagicMock(return_value="")
        connection_mock.run = MagicMock(return_value="localhost")

        with patch("cloudify_terminal.terminal_connection.connection",
                   MagicMock(return_value=connection_mock)):
            tasks.run(
                calls=[{'action': 'hostname', 'save_to': 'place_for_save',
                        'responses': [{'question': 'yes?', 'answer': 'no'}],
                        'errors': ['error'], 'promt_check': ['#']}],
                terminal_auth={'ip': 'ip', 'user': 'user',
                               'password': 'password', 'store_logs': True}
            )

        connection_mock.run.assert_called_with(
            'hostname', ['#'], ['error'],
            [{'question': 'yes?', 'answer': 'no'}])

        self.assertEqual(
            _ctx.instance.runtime_properties.get('place_for_save'),
            'localhost')

    def test_run_run_with_close(self):
        _ctx = self._gen_ctx()
        connection_mock = MagicMock()
        connection_mock.connect = MagicMock(return_value="")
        connection_mock.run = MagicMock(return_value="localhost")
        connection_mock.is_closed = MagicMock(side_effect=[False, True])

        with patch("cloudify_terminal.terminal_connection.connection",
                   MagicMock(return_value=connection_mock)):
            tasks.run(
                calls=[{}],
                terminal_auth={'ip': 'ip', 'user': 'user',
                               'password': 'password', 'store_logs': True}
            )

        connection_mock.run.assert_has_calls([call('exit', None, None)])

        self.assertIsNone(
            _ctx.instance.runtime_properties.get('place_for_save')
        )


if __name__ == '__main__':
    unittest.main()
