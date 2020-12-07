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
    call)

from cloudify import constants
from cloudify.state import current_ctx
from cloudify import exceptions as cfy_exc

from .. import workflows


class TestBackups(unittest.TestCase):

    def tearDown(self):
        current_ctx.clear()
        super(TestBackups, self).tearDown()

    def _gen_ctx(self, fs_check=False, node_types=[]):
        _ctx = MagicMock()

        _graph_mock = MagicMock()
        _graph_mock.execute = MagicMock()

        _sequence = MagicMock()
        _sequence.add = MagicMock()
        _graph_mock._sequence = _sequence
        _graph_mock.sequence = MagicMock(return_value=_sequence)

        _node = MagicMock()
        _node.type_hierarchy = node_types
        if fs_check:
            _node.operations = {
                'cloudify.interfaces.freeze.suspend': {},
                'cloudify.interfaces.freeze.resume': {},
                'cloudify.interfaces.snapshot.create': {},
                'cloudify.interfaces.snapshot.apply': {},
                'cloudify.interfaces.freeze.fs_prepare': {},
                'cloudify.interfaces.freeze.fs_finalize': {}
            }
        else:
            _node.operations = {
                'cloudify.interfaces.snapshot.create': {},
                'cloudify.interfaces.snapshot.apply': {},
                'cloudify.interfaces.snapshot.delete': {},
                'cloudify.interfaces.statistics.perfomance': {}
            }

        _instance = MagicMock()
        _instance.send_event = MagicMock(
            return_value='event')
        _instance.execute_operation = MagicMock(
            return_value='execute_operation')

        _node.properties = {}
        _node.instances = [_instance]

        _workflow_ctx = MagicMock()
        _workflow_ctx.nodes = [_node]
        _workflow_ctx.graph_mode = MagicMock(return_value=_graph_mock)
        _workflow_ctx.get_ctx = MagicMock(return_value=_ctx)
        return _workflow_ctx, _graph_mock, _instance

    def test_remove_backup(self):
        _workflow_ctx, _graph_mock, _instance = self._gen_ctx()

        with patch('cloudify.state.current_workflow_ctx', _workflow_ctx):
            workflows.remove_backup(ctx=_workflow_ctx,
                                    snapshot_name="backup_name")

        _workflow_ctx.graph_mode.assert_called_with()
        _graph_mock.execute.assert_called_with()
        _graph_mock._sequence.add.assert_called_with('event',
                                                     'execute_operation',
                                                     'event')
        _instance.execute_operation.assert_called_with(
            'cloudify.interfaces.snapshot.delete', kwargs={
                'snapshot_incremental': True,
                'snapshot_name': 'backup_name'})

        with patch('cloudify.state.current_workflow_ctx', _workflow_ctx):
            with self.assertRaises(cfy_exc.NonRecoverableError):
                workflows.remove_backup(ctx=_workflow_ctx)

    def test_restore(self):
        _workflow_ctx, _graph_mock, _instance = self._gen_ctx()

        with patch('cloudify.state.current_workflow_ctx', _workflow_ctx):
            workflows.restore(ctx=_workflow_ctx,
                              snapshot_name="backup_name")

        _workflow_ctx.graph_mode.assert_called_with()
        _graph_mock.execute.assert_called_with()
        _graph_mock._sequence.add.assert_called_with('event',
                                                     'execute_operation',
                                                     'event')
        _instance.execute_operation.assert_called_with(
            'cloudify.interfaces.snapshot.apply', kwargs={
                'snapshot_incremental': True,
                'snapshot_name': 'backup_name'})

        with patch('cloudify.state.current_workflow_ctx', _workflow_ctx):
            with self.assertRaises(cfy_exc.NonRecoverableError):
                workflows.restore(ctx=_workflow_ctx)

    def test_restore_fs(self):
        """Check restore with fs_freeze/unfreeze"""
        _workflow_ctx, _graph_mock, _instance = self._gen_ctx(
            fs_check=True, node_types=[constants.COMPUTE_NODE_TYPE])

        with patch('cloudify.state.current_workflow_ctx', _workflow_ctx):
            workflows.restore(ctx=_workflow_ctx,
                              snapshot_name="backup_name")

        _workflow_ctx.graph_mode.assert_called_with()
        _graph_mock.execute.assert_called_with()
        _graph_mock._sequence.add.assert_called_with('event',
                                                     'execute_operation',
                                                     'event')
        _instance.execute_operation.assert_has_calls([
            call('cloudify.interfaces.freeze.fs_prepare', kwargs={
                'snapshot_incremental': True, 'snapshot_name': 'backup_name',
                'include_node_types': [constants.COMPUTE_NODE_TYPE],
                'exclude_node_types': []}),
            call('cloudify.interfaces.snapshot.apply', kwargs={
                'snapshot_incremental': True, 'snapshot_name': 'backup_name'}),
            call('cloudify.interfaces.freeze.fs_finalize', kwargs={
                'snapshot_incremental': True, 'snapshot_name': 'backup_name',
                'include_node_types': [constants.COMPUTE_NODE_TYPE],
                'exclude_node_types': []})
        ])

    def test_backup_fs(self):
        """Check Backup with fs_freeze/unfreeze"""
        # with some name
        _workflow_ctx, _graph_mock, _instance = self._gen_ctx(fs_check=True)
        with patch('cloudify.state.current_workflow_ctx', _workflow_ctx):
            workflows.backup(ctx=_workflow_ctx,
                             snapshot_name="backup_name")
        _workflow_ctx.graph_mode.assert_called_with()
        _graph_mock.execute.assert_called_with()
        _graph_mock._sequence.add.assert_called_with('event',
                                                     'execute_operation',
                                                     'event')
        _instance.execute_operation.assert_has_calls([
            call('cloudify.interfaces.freeze.fs_prepare', kwargs={
                'snapshot_rotation': -1, 'snapshot_type': 'irregular',
                'snapshot_incremental': True, 'snapshot_name': 'backup_name',
                'include_node_types': [],
                'exclude_node_types': ['cloudify.nodes.Compute']}),
            call('cloudify.interfaces.snapshot.create', kwargs={
                'snapshot_rotation': -1, 'snapshot_incremental': True,
                'snapshot_name': 'backup_name', 'snapshot_type': 'irregular'}),
            call('cloudify.interfaces.freeze.fs_finalize', kwargs={
                'snapshot_rotation': -1, 'snapshot_type': 'irregular',
                'snapshot_incremental': True, 'snapshot_name': 'backup_name',
                'include_node_types': [],
                'exclude_node_types': ['cloudify.nodes.Compute']})
        ])

    def test_backup(self):
        # without name, all fields by default
        _workflow_ctx, _graph_mock, _instance = self._gen_ctx()
        with patch('cloudify.state.current_workflow_ctx', _workflow_ctx):
            with patch('time.time', MagicMock(return_value="1234")):
                workflows.backup(ctx=_workflow_ctx)
        _workflow_ctx.graph_mode.assert_called_with()
        _graph_mock.execute.assert_called_with()
        _graph_mock._sequence.add.assert_called_with('event',
                                                     'execute_operation',
                                                     'event')
        _instance.execute_operation.assert_called_with(
            'cloudify.interfaces.snapshot.create', kwargs={
                'snapshot_rotation': -1, 'snapshot_incremental': True,
                'snapshot_name': 'backup-1234', 'snapshot_type': 'irregular'})
        # with some name
        _workflow_ctx, _graph_mock, _instance = self._gen_ctx()
        with patch('cloudify.state.current_workflow_ctx', _workflow_ctx):
            workflows.backup(ctx=_workflow_ctx,
                             snapshot_name="backup_name")
        _workflow_ctx.graph_mode.assert_called_with()
        _graph_mock.execute.assert_called_with()
        _graph_mock._sequence.add.assert_called_with('event',
                                                     'execute_operation',
                                                     'event')
        _instance.execute_operation.assert_called_with(
            'cloudify.interfaces.snapshot.create', kwargs={
                'snapshot_rotation': -1, 'snapshot_incremental': True,
                'snapshot_name': 'backup_name', 'snapshot_type': 'irregular'})
        # all values from inputs
        _workflow_ctx, _graph_mock, _instance = self._gen_ctx()
        with patch('cloudify.state.current_workflow_ctx', _workflow_ctx):
            workflows.backup(ctx=_workflow_ctx,
                             snapshot_name="other_name",
                             snapshot_type="week",
                             snapshot_rotation=10,
                             snapshot_incremental=False)
        _workflow_ctx.graph_mode.assert_called_with()
        _graph_mock.execute.assert_called_with()
        _graph_mock._sequence.add.assert_called_with('event',
                                                     'execute_operation',
                                                     'event')
        _instance.execute_operation.assert_called_with(
            'cloudify.interfaces.snapshot.create', kwargs={
                'snapshot_rotation': 10, 'snapshot_incremental': False,
                'snapshot_name': 'other_name', 'snapshot_type': "week"})


if __name__ == '__main__':
    unittest.main()
