# Should be removed after full split code to cloudify-utilities-plugins-sdk

# Copyright (c) 2017-2018 Cloudify Platform Ltd. All rights reserved
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
from mock import (
    MagicMock,
    patch,
    mock_open,
    Mock,
    call)


from cloudify_common_sdk import exceptions
from cloudify_common_sdk._compat import PY2
import cloudify_terminal_sdk.terminal_connection as terminal_connection


class TestTasks(unittest.TestCase):

    sleep_mock = None

    def setUp(self):
        super(TestTasks, self).setUp()
        mock_sleep = MagicMock()
        self.sleep_mock = patch('time.sleep', mock_sleep)
        self.sleep_mock.start()

    def tearDown(self):
        if self.sleep_mock:
            self.sleep_mock.stop()
            self.sleep_mock = None
        super(TestTasks, self).tearDown()

    def test_empty_send(self):
        conn = terminal_connection.RawConnection()
        conn._conn_send("")

    def test_send(self):
        conn = terminal_connection.RawConnection()
        conn.conn = MagicMock()
        conn.conn.send = MagicMock(return_value=4)
        conn.conn.closed = False
        conn.conn.log_file_name = False

        conn._conn_send("abcd")

        conn.conn.send.assert_called_with("abcd")

    def test_send_closed_connection(self):
        conn = terminal_connection.RawConnection()
        conn.conn = MagicMock()
        conn.conn.send = MagicMock(return_value=3)
        conn.conn.closed = True
        conn.conn.log_file_name = False

        conn._conn_send("abcd")

        conn.conn.send.assert_called_with("abcd")

    def test_send_troubles(self):
        conn = terminal_connection.RawConnection()
        conn.conn = MagicMock()
        conn.logger = MagicMock()
        conn.conn.send = MagicMock(return_value=-1)
        conn.conn.closed = True
        conn.conn.log_file_name = False

        conn._conn_send("abcd")

        conn.logger.info.assert_called_with("We have issue with send!")
        conn.conn.send.assert_called_with("abcd")

    def test_send_byte_by_byte(self):
        conn = terminal_connection.RawConnection()
        conn.conn = MagicMock()
        conn.logger = MagicMock()
        conn.conn.send = Mock(return_value=2)
        conn.conn.closed = False
        conn.conn.log_file_name = False

        conn._conn_send("abcd")

        conn.conn.send.assert_has_calls([call('abcd'), call('cd')])

    def test_recv(self):
        conn = terminal_connection.RawConnection()
        conn.conn = MagicMock()
        conn.logger = MagicMock()
        conn.conn.recv = MagicMock(return_value="AbCd")
        conn.conn.log_file_name = False

        self.assertEqual(conn._conn_recv(4), "AbCd")

        conn.conn.recv.assert_called_with(4)

    def test_recv_empty(self):
        conn = terminal_connection.RawConnection()
        conn.conn = MagicMock()
        conn.logger = MagicMock()
        conn.conn.recv = MagicMock(return_value="")
        conn.conn.log_file_name = False

        self.assertEqual(conn._conn_recv(4), "")

        conn.logger.warn.assert_called_with('We have empty response.')
        conn.conn.recv.assert_called_with(4)

    def test_find_any_in(self):
        conn = terminal_connection.RawConnection()

        self.assertEqual(conn._find_any_in("abcd\n$abc", ["$", "#"]), 5)
        self.assertEqual(conn._find_any_in("abcd\n>abc", ["$", "#"]), -1)

    def test_delete_backspace(self):
        conn = terminal_connection.RawConnection()
        # simple case
        self.assertEqual(conn._delete_backspace("abc\bd\n$a\bbc"), "abd\n$bc")
        # \b in begging of line
        self.assertEqual(conn._delete_backspace("\bcd\n$a\bbc"), "cd\n$bc")
        # \b at the end
        self.assertEqual(conn._delete_backspace("abc\b\b\b\b\b"), "")

    def test_send_response(self):
        conn = terminal_connection.RawConnection()
        # no responses
        self.assertEqual(conn._send_response("abcd?", []), -1)
        # wrong question
        self.assertEqual(
            conn._send_response(
                "abcd?", [{
                    'question': 'yes?',
                    'answer': 'no'
                }]), -1
        )
        # correct question
        conn.conn = MagicMock()
        conn.logger = MagicMock()
        conn.conn.send = Mock(return_value=2)
        conn.conn.closed = False
        conn.conn.log_file_name = False
        self.assertEqual(
            conn._send_response(
                "continue, yes?", [{
                    'question': 'yes?',
                    'answer': 'no'
                }]), 14
        )
        conn.conn.send.assert_called_with("no")
        # question with new line response
        conn.conn.send = Mock(return_value=1)
        self.assertEqual(
            conn._send_response(
                "continue, yes?", [{
                    'question': 'yes?',
                    'answer': 'n',
                    'newline': True
                }]), 14
        )
        conn.conn.send.assert_has_calls([call("n"), call('\n')])

    def test_is_closed(self):
        conn = terminal_connection.RawConnection()

        conn.conn = MagicMock()

        conn.conn.closed = False
        self.assertFalse(conn.is_closed())

        conn.conn.closed = True
        self.assertTrue(conn.is_closed())

        conn.conn = None
        self.assertTrue(conn.is_closed())

    def test_close(self):
        conn = terminal_connection.RawConnection()

        conn_conn = MagicMock()
        conn_conn.close = MagicMock()
        conn.conn = conn_conn

        conn_ssh = MagicMock()
        conn_ssh.close = MagicMock()
        conn.ssh = conn_ssh

        conn.close()

        conn_conn.close.assert_called_with()
        conn_ssh.close.assert_called_with()

    def test_write_to_log_no_logfile(self):
        conn = terminal_connection.RawConnection()
        conn.log_file_name = None
        conn.logger = MagicMock()

        conn._write_to_log("Some_text")
        conn.logger.debug.assert_not_called()

    def test_write_to_log_write_file_output(self):
        conn = terminal_connection.RawConnection()
        conn.log_file_name = '/proc/read_only_file'
        conn.logger = MagicMock()

        with patch("os.path.isdir", MagicMock(return_value=True)):
            fake_file = mock_open()
            if PY2:
                # python 2
                with patch(
                        '__builtin__.open', fake_file
                ):
                    conn._write_to_log("Some_text")
            else:
                # python 3
                with patch(
                        'builtins.open', fake_file
                ):
                    conn._write_to_log("Some_text")
            fake_file.assert_called_once_with('/proc/read_only_file', 'a+')
            fake_file().write.assert_called_with('Some_text')

    def test_write_to_log_write_file_input(self):
        conn = terminal_connection.RawConnection()
        conn.log_file_name = '/proc/read_only_file'
        conn.logger = MagicMock()

        with patch("os.path.isdir", MagicMock(return_value=True)):
            fake_file = mock_open()
            if PY2:
                # python 2
                with patch(
                        '__builtin__.open', fake_file
                ):
                    conn._write_to_log("Some_text", False)
            else:
                # python 3
                with patch(
                        'builtins.open', fake_file
                ):
                    conn._write_to_log("Some_text", False)

            fake_file.assert_called_once_with('/proc/read_only_file.in', 'a+')
            fake_file().write.assert_called_with('Some_text')
            conn.logger.debug.assert_not_called()

    def test_write_to_log_cantcreate_dir(self):
        conn = terminal_connection.RawConnection()
        conn.log_file_name = '/proc/read_only/file'
        conn.logger = MagicMock()

        with patch("os.path.isdir", MagicMock(return_value=False)):
            with patch("os.makedirs", MagicMock(side_effect=Exception(
                "[Errno 13] Permission denied: '/proc/read_only'"
            ))):
                conn._write_to_log("Some_text")
        conn.logger.info.assert_called_with(
            'Can\'t write to log: Exception("[Errno 13] Permission denied:'
            ' \'/proc/read_only\'",)'
        )

    def test_connect_with_password(self):
        ssh_mock = MagicMock()
        ssh_mock.connect = MagicMock(side_effect=OSError("e"))
        with patch("paramiko.SSHClient", MagicMock(return_value=ssh_mock)):
            with self.assertRaises(OSError):
                conn = terminal_connection.RawConnection(
                    logger="logger", log_file_name="log_file_name")
                conn.connect("ip", "user", "password", None, port=44,
                             prompt_check="prompt_check")

        ssh_mock.connect.assert_called_with(
            'ip', allow_agent=False, look_for_keys=False, password='password',
            port=44, timeout=5, username='user')

        self.assertEqual(conn.logger, "logger")
        self.assertEqual(conn.log_file_name, "log_file_name")

    def test_connect_with_key(self):
        ssh_mock = MagicMock()
        ssh_mock.connect = MagicMock(side_effect=OSError("e"))
        with patch("paramiko.RSAKey.from_private_key",
                   MagicMock(return_value="key_value")):
            with patch("paramiko.SSHClient", MagicMock(return_value=ssh_mock)):
                with self.assertRaises(OSError):
                    conn = terminal_connection.RawConnection(
                        logger="logger", log_file_name="log_file_name")
                    conn.connect("ip", "user", None, "key",
                                 prompt_check=None,)

        ssh_mock.connect.assert_called_with(
            'ip', allow_agent=False, pkey='key_value', port=22, timeout=5,
            username='user')

        self.assertEqual(conn.logger, "logger")
        self.assertEqual(conn.log_file_name, "log_file_name")

    def test_connect(self):
        conn_mock = MagicMock()
        conn_mock.recv = MagicMock(return_value="some_prompt#")
        ssh_mock = MagicMock()
        ssh_mock.connect = MagicMock()
        ssh_mock.invoke_shell = MagicMock(return_value=conn_mock)
        conn = terminal_connection.RawConnection(
            logger=MagicMock(), log_file_name=None)
        with patch("paramiko.SSHClient", MagicMock(return_value=ssh_mock)):
            self.assertEqual(
                conn.connect("ip", "user", "password", None, port=44,
                             prompt_check=None),
                "some_prompt"
            )

    def test_cleanup_response_empty(self):
        conn = terminal_connection.RawConnection()

        self.assertEqual(
            conn._cleanup_response(
                text=" text ",
                prefix=":",
                warning_examples=[],
                error_examples=[],
                critical_examples=[]
            ),
            "text")

    def test_cleanup_response_with_prompt(self):
        conn = terminal_connection.RawConnection()

        conn.logger = MagicMock()

        self.assertEqual(
            conn._cleanup_response(
                text="prompt> text ",
                prefix="prompt>",
                warning_examples=[],
                error_examples=['error'],
                critical_examples=[]
            ),
            "text"
        )

        conn.logger.info.assert_not_called()

    def test_cleanup_response_without_prompt(self):
        conn = terminal_connection.RawConnection()
        conn.logger = MagicMock()

        self.assertEqual(
            conn._cleanup_response(
                text="prmpt> text ",
                prefix="prompt>",
                warning_examples=[],
                error_examples=['error'],
                critical_examples=[]
            ),
            "prmpt> text"
        )

        conn.logger.debug.assert_called_with(
            "Have not found 'prompt>' in response: ''prmpt> text ''")

    def test_cleanup_response_mess_before_prompt(self):
        conn = terminal_connection.RawConnection()
        conn.logger = MagicMock()

        self.assertEqual(
            conn._cleanup_response(
                text="..prompt> text\n some",
                prefix="prompt>",
                warning_examples=[],
                error_examples=['error'],
                critical_examples=[]
            ),
            "some"
        )

        conn.logger.debug.assert_called_with(
            "Some mess before 'prompt>' in response: ''..prompt> "
            "text\\n some''")

    def test_cleanup_response_error(self):
        conn = terminal_connection.RawConnection()
        conn.logger = MagicMock()

        # check with closed connection
        with self.assertRaises(exceptions.RecoverableError) as error:
            conn._cleanup_response(
                text="prompt> text\n some\nerror",
                prefix="prompt>",
                warning_examples=[],
                error_examples=['error'],
                critical_examples=[]
            )

        conn.logger.info.assert_not_called()

        self.assertEqual(
            str(error.exception),
            'Looks as we have error in response:  text\n some\nerror'
        )

        # check with alive connection
        conn.conn = MagicMock()
        conn.conn.closed = False

        # save mocks
        _conn_mock = conn.conn

        # warnings?
        with self.assertRaises(
            exceptions.RecoverableWarning
        ) as error:
            conn._cleanup_response(
                text="prompt> text\n some\nerror",
                prefix="prompt>",
                warning_examples=['error'],
                error_examples=[],
                critical_examples=[]
            )
        _conn_mock.close.assert_not_called()

        # errors?
        with self.assertRaises(exceptions.RecoverableError) as error:
            conn._cleanup_response(
                text="prompt> text\n some\nerror",
                prefix="prompt>",
                warning_examples=[],
                error_examples=['error'],
                critical_examples=[]
            )
        _conn_mock.close.assert_called_with()
        self.assertFalse(conn.conn)
        conn.conn = _conn_mock

        # critical?
        conn.conn.close = MagicMock()
        # save mocks
        _conn_mock = conn.conn
        # check with close
        with self.assertRaises(
            exceptions.NonRecoverableError
        ) as error:
            conn._cleanup_response(
                text="prompt> text\n some\nerror",
                prefix="prompt>",
                warning_examples=[],
                error_examples=[],
                critical_examples=['error']
            )
        _conn_mock.close.assert_called_with()

    def test_run_with_closed_connection(self):
        conn = terminal_connection.RawConnection()
        conn.logger = MagicMock()
        conn.conn = MagicMock()
        conn.conn.closed = True
        conn.conn.send = MagicMock(return_value=5)

        self.assertEqual(conn.run("test"), "")

        conn.conn.send.assert_called_with("test\n")

    def test_run_with_closed_connection_after_twice_check(self):
        conn = terminal_connection.RawConnection()
        conn.logger = MagicMock()
        conn.conn = MagicMock()
        conn.conn.closed = False

        conn.conn.call_count = 0

        def _recv(size):

            if conn.conn.call_count == 1:
                conn.conn.closed = True

            conn.conn.call_count += 1

            return "+"

        conn.conn.send = MagicMock(return_value=5)
        conn.conn.recv = _recv

        self.assertEqual(conn.run("test"), "++")

        conn.conn.send.assert_called_with("test\n")

    def test_run_with_closed_connection_after_third_check(self):
        conn = terminal_connection.RawConnection()
        conn.logger = MagicMock()

        class _fake_conn(object):

            call_count = 0

            def send(self, text):
                return len(text)

            def recv(self, size):
                return "+\n"

            def close(self):
                pass

            @property
            def closed(self):
                self.call_count += 1

                return (self.call_count >= 4)

        conn.conn = _fake_conn()

        self.assertEqual(conn.run("test"), "+")

    def test_run_return_without_delay(self):
        conn = terminal_connection.RawConnection()
        conn.logger = MagicMock()
        conn.conn = MagicMock()
        conn.conn.closed = False
        conn.conn.send = MagicMock(return_value=5)
        conn.conn.recv = MagicMock(return_value="\nmessage\n#")

        self.assertEqual(conn.run("test"), "message")

        conn.conn.send.assert_called_with("test\n")

    def test_run_return_without_delay_with_responses(self):
        conn = terminal_connection.RawConnection()
        conn.logger = MagicMock()
        conn.conn = MagicMock()
        conn.conn.closed = False
        conn.conn.send = MagicMock(side_effect=[5, 2])
        conn.conn.recv = MagicMock(side_effect=["\nmessage, yes?", "ok\n#"])

        self.assertEqual(
            conn.run("test", responses=[{
                'question': 'yes?',
                'answer': 'no'
            }]),
            "message, yes?ok"
        )

        conn.conn.send.assert_has_calls([call("test\n"), call('no')])


if __name__ == '__main__':
    unittest.main()
