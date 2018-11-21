# Copyright (c) 2017-2018 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import time

from cloudify.decorators import workflow
from cloudify import constants
from cloudify import exceptions as cfy_exc


def _check_type(node, include_node_types, exclude_node_types):
    """check that we have correct type for run action"""

    # check by include types
    if include_node_types:
        for node_type in include_node_types:
            if node_type not in node.type_hierarchy:
                return False

    # check by exclude types
    if exclude_node_types:
        for node_type in exclude_node_types:
            if node_type in node.type_hierarchy:
                return False

    return True


def _run_operation(ctx, sequence, operation, **kwargs):
    ctx.logger.debug("Run {}({})".format(operation, repr(kwargs)))

    include_node_types = kwargs.get('include_node_types', [])
    exclude_node_types = kwargs.get('exclude_node_types', [])
    include_instances = kwargs.get('include_instances', [])

    for node in ctx.nodes:
        # check by node type
        if not _check_type(node, include_node_types, exclude_node_types):
            continue

        # check for skipped actions
        skip_actions = node.properties.get("skip_actions", [])
        if skip_actions:
            if operation in skip_actions:
                continue

        if operation in node.operations:
            for instance in node.instances:
                # check for skip instances
                if include_instances:
                    if instance.id not in include_instances:
                        continue
                # add to run operation
                sequence.add(
                    instance.send_event('Starting to {}'.format(operation)),
                    instance.execute_operation(operation,
                                               kwargs=kwargs),
                    instance.send_event('Done {}'.format(operation)))


@workflow
def suspend(ctx, **kwargs):
    graph = ctx.graph_mode()
    sequence = graph.sequence()

    # deprecated
    _run_operation(ctx, sequence, 'cloudify.interfaces.lifecycle.suspend',
                   **kwargs)
    # new way
    _run_operation(ctx, sequence, 'cloudify.interfaces.freeze.suspend',
                   **kwargs)
    graph.execute()


@workflow
def resume(ctx, **kwargs):
    graph = ctx.graph_mode()
    sequence = graph.sequence()

    # new way
    _run_operation(ctx, sequence, "cloudify.interfaces.freeze.resume",
                   **kwargs)
    # deprecated
    _run_operation(ctx, sequence, "cloudify.interfaces.lifecycle.resume",
                   **kwargs)
    graph.execute()


@workflow
def statistics(ctx, **kwargs):
    graph = ctx.graph_mode()
    sequence = graph.sequence()

    _run_operation(ctx, sequence, "cloudify.interfaces.statistics.perfomance",
                   **kwargs)
    graph.execute()


def _fs_prepare(ctx, sequence, kwargs):
    """Freeze file system after action, called for services !COMPUTE_NODE_TYPE
    nodes, than for COMPUTE_NODE_TYPE nodes"""
    # stop all non compute nodes
    ctx.logger.debug("Freeze services")

    kwargs['exclude_node_types'] = [constants.COMPUTE_NODE_TYPE]
    kwargs['include_node_types'] = []
    _run_operation(ctx, sequence, "cloudify.interfaces.freeze.fs_prepare",
                   **kwargs)

    # stop all compute nodes
    ctx.logger.debug("Freeze computes")

    kwargs['exclude_node_types'] = []
    kwargs['include_node_types'] = [constants.COMPUTE_NODE_TYPE]
    _run_operation(ctx, sequence, "cloudify.interfaces.freeze.fs_prepare",
                   **kwargs)
    del kwargs['exclude_node_types']
    del kwargs['include_node_types']


def _fs_finalize(ctx, sequence, kwargs):
    """Unfreeze file system after action, called for COMPUTE_NODE_TYPE nodes,
    than for service !COMPUTE_NODE_TYPE nodes"""
    # start all compute nodes
    ctx.logger.debug("Unfreeze computes")

    kwargs['exclude_node_types'] = []
    kwargs['include_node_types'] = [constants.COMPUTE_NODE_TYPE]
    _run_operation(ctx, sequence, "cloudify.interfaces.freeze.fs_finalize",
                   **kwargs)

    # start all non compute nodes
    ctx.logger.debug("Unfreeze services")

    kwargs['exclude_node_types'] = [constants.COMPUTE_NODE_TYPE]
    kwargs['include_node_types'] = []
    _run_operation(ctx, sequence, "cloudify.interfaces.freeze.fs_finalize",
                   **kwargs)

    del kwargs['exclude_node_types']
    del kwargs['include_node_types']


@workflow
def backup(ctx, **kwargs):
    if not kwargs.get("snapshot_name"):
        kwargs["snapshot_name"] = "backup-{}".format(int(time.time()))

    if not kwargs.get("snapshot_type"):
        kwargs["snapshot_type"] = "irregular"

    if not kwargs.get("snapshot_rotation"):
        kwargs["snapshot_rotation"] = -1

    if 'snapshot_incremental' not in kwargs:
        kwargs['snapshot_incremental'] = True

    graph = ctx.graph_mode()
    sequence = graph.sequence()

    # suspend fs operations
    _fs_prepare(ctx, sequence, kwargs)

    # backup state
    ctx.logger.debug("Backing up")
    _run_operation(ctx, sequence, "cloudify.interfaces.snapshot.create",
                   **kwargs)
    # resume fs operations
    _fs_finalize(ctx, sequence, kwargs)

    graph.execute()

    ctx.logger.info("Backuped to {}".format(repr(kwargs["snapshot_name"])))


@workflow
def restore(ctx, **kwargs):
    if not kwargs.get("snapshot_name"):
        raise cfy_exc.NonRecoverableError(
            'Backup name must be provided.'
        )
    if 'snapshot_incremental' not in kwargs:
        kwargs['snapshot_incremental'] = True

    graph = ctx.graph_mode()
    sequence = graph.sequence()

    # suspend fs operations
    # need for correctly stop any io operations or shutdown vm if required
    _fs_prepare(ctx, sequence, kwargs)

    # restore fs
    ctx.logger.debug("Restoring")
    _run_operation(ctx, sequence, "cloudify.interfaces.snapshot.apply",
                   **kwargs)

    # resume fs operations
    # we need such for case if in backup stored "freeze state"
    _fs_finalize(ctx, sequence, kwargs)

    graph.execute()

    ctx.logger.info("Restored from {}".format(repr(kwargs["snapshot_name"])))


@workflow
def remove_backup(ctx, **kwargs):
    if not kwargs.get("snapshot_name"):
        raise cfy_exc.NonRecoverableError(
            'Backup name must be provided.'
        )
    if 'snapshot_incremental' not in kwargs:
        kwargs['snapshot_incremental'] = True

    graph = ctx.graph_mode()
    sequence = graph.sequence()

    _run_operation(ctx, sequence, "cloudify.interfaces.snapshot.delete",
                   **kwargs)
    graph.execute()

    ctx.logger.info("Removed {}".format(repr(kwargs["snapshot_name"])))
