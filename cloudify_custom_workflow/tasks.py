########
# Copyright (c) 2014-2021 Cloudify Platform Ltd. All rights reserved
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

from cloudify import ctx

from cloudify.decorators import workflow
from cloudify.workflows import ctx as workflow_ctx
from cloudify.exceptions import NonRecoverableError

from cloudify_common_sdk.utils import create_deployments, install_deployments

from .batch_utils import (
    generate_labels_from_inputs,
    generate_group_id_from_blueprint,
    generate_inputs_from_deployments,
    generate_deployment_ids_from_group_id
)


def log(**kwargs):
    ctx.logger.info("Log interface: {}".format(repr(kwargs)))


@workflow
def customwf(nodes_to_runon, operations_to_execute, **kwargs):

    ctx = workflow_ctx
    ctx.logger.info("Starting Custom Workflow")

    try:
        nodes = json.loads(nodes_to_runon)
    except TypeError:
        ctx.logger.info("Nodes not in Json trying directly")
        nodes = nodes_to_runon

    try:
        operations = json.loads(operations_to_execute)
    except TypeError:
        ctx.logger.info("operations not in Json trying directly")
        operations = operations_to_execute

    ctx.logger.info("Nodes {} on Operations {}".format(nodes, operations))
    # update interface on the config node
    graph = ctx.graph_mode()
    # If ctx is left in the kwargs it will cause exceptions
    # It will be injected for the operation being executed anyway
    kwargs.pop('ctx')
    sequence = graph.sequence()
    for opnode in nodes:
        for node in ctx.nodes:
            if node.id == opnode:
                for instance in node.instances:
                    for operation in operations:
                        # add to run operation
                        sequence.add(
                            instance.send_event(
                                'Starting to {} on instance {} of node {}'
                                .format(operation, instance.id, node.id)),
                            instance.execute_operation(operation,
                                                       kwargs=kwargs),
                            instance.send_event('Done {}'.format(operation)))

    graph.execute()


@workflow
def batch_deploy_and_install(blueprint_id,
                             parent_deployments,
                             group_id=None,
                             new_deployment_ids=None,
                             inputs=None,
                             labels=None,
                             add_parent_labels=False,
                             **_):
    """
    Create deployments for a batch from a single blueprint.
    :param blueprint_id: The blueprint, which has already been uploaded.
    :type blueprint_id: str
    :param parent_deployments: A list of parent deployments.
    :type parent_deployments: list
    :param group_id: the new group ID.
    :type group_id: str
    :param new_deployment_ids: a list of new deployment names.
    :type new_deployment_ids: list
    :param inputs: A list of inputs to the new deployments.
    :type inputs: list
    :param labels: A list of labels to the new deployments.
    :type labels: list
    :return: None
    :rtype: NoneType
    """
    group_id = batch_deploy(blueprint_id,
                            parent_deployments,
                            group_id,
                            new_deployment_ids,
                            inputs,
                            labels,
                            add_parent_labels,
                            **_)

    batch_install(group_id)


@workflow
def batch_deploy(blueprint_id,
                 parent_deployments,
                 group_id=None,
                 new_deployment_ids=None,
                 inputs=None,
                 labels=None,
                 add_parent_labels=False,
                 **kwargs):
    """
    Create deployments for a batch from a single blueprint.
    :param blueprint_id: The blueprint, which has already been uploaded.
    :type blueprint_id: str
    :param parent_deployments: A list of parent deployments.
    :type parent_deployments: list
    :param group_id: the new group ID.
    :type group_id: str
    :param new_deployment_ids: a list of new deployment names.
    :type new_deployment_ids: list
    :param inputs: A list of inputs to the new deployments.
    :type inputs: list
    :param labels: A list of labels to the new deployments.
    :type labels: list
    :return: group_id
    :rtype: str
    """

    labels = labels or []

    local_ctx = kwargs.get('ctx')

    if not isinstance(parent_deployments, list):
        # If someone sends a list in the CLI,
        # it will not be properly formatted.
        try:
            parent_deployments = json.loads(parent_deployments)
        except json.JSONDecodeError:
            raise NonRecoverableError(
                'The parent_deployments parameter is not properly formatted. '
                'Proper format is a list, a {t} was provided: {v}.'.format(
                    t=type(parent_deployments), v=parent_deployments))

    group_id = group_id or generate_group_id_from_blueprint(
        blueprint_id)
    new_deployment_ids = new_deployment_ids or \
        generate_deployment_ids_from_group_id(group_id, parent_deployments)
    inputs = generate_inputs_from_deployments(inputs, parent_deployments)
    if add_parent_labels:
        labels.extend(labels or generate_labels_from_inputs(inputs))

    create_dep_params = (
        group_id,
        blueprint_id,
        new_deployment_ids,
        inputs,
        labels)

    if local_ctx:

        local_ctx.logger.debug(
            'Sending these params to create_deployments: {}'.format(
                json.dumps(create_dep_params)))

    create_deployments(*create_dep_params)

    return group_id


@workflow
def batch_install(group_id, **_):
    """
    Create deployments for a batch from a single blueprint.
    :param group_id: the new group ID.
    :type group_id: str
    :return: None
    :rtype: NoneType
    """

    install_deployments(group_id)
