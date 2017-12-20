
#######
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

from cloudify import ctx
from cloudify.workflows import ctx as workflow_ctx
from cloudify.decorators import workflow

from cloudify import manager

import json

LIFECYCLE_OPERATION_UPDATE = 'cloudify.interfaces.lifecycle.update'
LIFECYCLE_OPERATION_CONFIGURE = 'cloudify.interfaces.lifecycle.configure'
LIFECYCLE_RELATIONSHIP_OPERATION_PRECONFIGURE = \
    'cloudify.interfaces.relationship_lifecycle.preconfigure'
LIFECYCLE_OPERATION_IS_ALIVE = \
    'cloudify.interfaces.lifecycle.is_alive'

PARAMS = 'params'
PARAMS_LIST = 'params_list'
OLD_PARAMS = 'old_params'
DIFF_PARAMS = 'diff_params'


def _merge_dicts(d1, d2):
    result = d1.copy()
    for key, new_val in d2.iteritems():
        current_val = result.get(key)
        if isinstance(current_val, dict) and isinstance(new_val, dict):
            result[key] = _merge_dicts(current_val, new_val)
        else:
            result[key] = new_val
    return result


def _handle_parameters(parameters):
    if isinstance(parameters, dict):
        return parameters
    else:
        return json.loads(parameters)


def load_configuration(parameters, merge_dicts, **kwargs):
    # load params
    params = _handle_parameters(parameters)

    # get previous params
    p = ctx.instance.runtime_properties.get(PARAMS, {})
    # update params
    if merge_dicts:
        p = _merge_dicts(p, params)
    else:
        p.update(params)
    ctx.instance.runtime_properties['params'] = p


def load_configuration_to_runtime_properties(source_config, **kwargs):
    old_params = ctx.source.instance.runtime_properties.get('params', {})
    # prevent recursion by removing old_params from old_params
    old_params['old_params'] = {}
    # retrive relevant parameters list from node properties
    params_list = ctx.source.node.properties['params_list']

    # populate params from main configuration with only relevant values
    params = {k: v for k, v in source_config.iteritems() if k in params_list}
    # override params with HARD coded node params
    params.update(ctx.source.node.properties['params'])

    # create in params old_params key with empty dict
    # so it wll match to the old_params
    params[OLD_PARAMS] = {}

    # find changed params between old params and populated params
    diff_params = [k for k, v in params.iteritems() if v != old_params.get(k)]

    # populate the old params into params
    params[OLD_PARAMS] = old_params

    # populate diff_params inot params
    params[DIFF_PARAMS] = diff_params

    ctx.logger.info("Show params for instance {}: {}"
                    .format(ctx.source.instance.id, params))
    ctx.logger.info("Show old params for instance {}: {}"
                    .format(ctx.source.instance.id, old_params))
    ctx.logger.info("Show diff params for instance {}: {}"
                    .format(ctx.source.instance.id, diff_params))

    # update params to runtime properties
    ctx.source.instance.runtime_properties[PARAMS] = params


@workflow
def update(params,
           configuration_node_id,
           node_types_to_update,
           merge_dict,
           **kwargs):
    ctx = workflow_ctx
    ctx.logger.info("Starting Update Workflow")

    restcli = manager.get_rest_client()

    node_types = set(node_types_to_update)
    # update interface on the config node
    graph = ctx.graph_mode()

    perform_availability_check(graph,
                               node_types,
                               configuration_node_id,
                               params,
                               ctx)

    configure_and_preconfigure(graph,
                               configuration_node_id,
                               params,
                               merge_dict,
                               node_types,
                               ctx)
    return update_on_nodes(graph,
                           node_types,
                           configuration_node_id,
                           params,
                           restcli,
                           ctx)


def perform_availability_check(graph,
                               node_types,
                               configuration_node_id,
                               params,
                               ctx):
    sequence = graph.sequence()

    execute_function_on_instance_connected_to_configuration(
        node_types,
        configuration_node_id,
        params,
        availability_check,
        {'sequence': sequence},
        ctx
    )

    return graph.execute()


def availability_check(sequence, instance, ctx):
    ctx.logger.info(
        "Checking availability of instance {0}".format(
            instance.id)
    )
    operation_task = instance.execute_operation(
        LIFECYCLE_OPERATION_IS_ALIVE
    )
    sequence.add(operation_task)


def update_on_nodes(graph,
                    node_types,
                    configuration_node_id,
                    params,
                    restcli,
                    ctx):
    sequence = graph.sequence()

    execute_function_on_instance_connected_to_configuration(
        node_types,
        configuration_node_id,
        params,
        execute_update,
        {'restcli': restcli, 'sequence': sequence},
        ctx
    )

    return graph.execute()


def execute_update(restcli, sequence, instance, ctx):
    currentinstance = restcli.node_instances.get(instance.id)
    params = currentinstance.runtime_properties[PARAMS]
    ctx.logger.info(
        "Updating instance ID: {} with diff_params {}".format(
            instance.id, params[DIFF_PARAMS]
        )
    )
    operation_task = instance.execute_operation(
        LIFECYCLE_OPERATION_UPDATE
    )
    sequence.add(operation_task)


def configure_and_preconfigure(graph,
                               configuration_node_id,
                               params,
                               merge_dict,
                               node_types,
                               ctx):

    sequence = graph.sequence()
    execute_function_on_configuration_node(
        configuration_node_id,
        configure,
        {'sequence': sequence, 'parameters': params, 'merge_dict': merge_dict},
        ctx
    )

    execute_function_on_instances_relationship_connected_to_configuration(
        node_types,
        configuration_node_id,
        preconfigure,
        {'sequence': sequence},
        params,
        ctx
    )
    graph.execute()


def configure(sequence, parameters, merge_dict, instance, ctx):
    ctx.logger.info('Execute configure operation on instance ' + instance.id)
    load_config_task = instance.execute_operation(
        LIFECYCLE_OPERATION_CONFIGURE,
        allow_kwargs_override=True,
        kwargs={'parameters': parameters, 'merge_dict': merge_dict}
    )
    sequence.add(load_config_task)


def preconfigure(sequence, relationship, ctx):
    ctx.logger.info('Execute preconfigure operation on node '
                    + relationship.target_node_instance.node_id)
    operation_task = \
        relationship.execute_target_operation(
            LIFECYCLE_RELATIONSHIP_OPERATION_PRECONFIGURE
        )
    sequence.add(operation_task)


def needs_to_get_updated(params, instance):
    params_list = instance.node.properties[PARAMS_LIST]
    return any(p in params_list for p in params)


def execute_function_on_configuration_node(
        configuration_node_id,
        func,
        func_kwargs,
        ctx):
    for node in ctx.nodes:
        if configuration_node_id == node.id:
            for instance in node.instances:
                func(instance=instance, ctx=ctx, **func_kwargs)


def execute_function_on_instances_relationship_connected_to_configuration(
        node_types,
        configuration_node_id,
        func,
        func_kwargs,
        params,
        ctx):
    for node in ctx.nodes:
        if node_types.intersection(set(node.type_hierarchy)):
            for instance in node.instances:
                for relationship in instance.relationships:
                    if configuration_node_id == relationship\
                            .target_node_instance.node_id:
                        if needs_to_get_updated(params, instance):
                            func(relationship=relationship,
                                 ctx=ctx,
                                 **func_kwargs)


def execute_function_on_instance_connected_to_configuration(
        node_types,
        configuration_node_id,
        params,
        func,
        func_kwargs,
        ctx):
    for node in ctx.nodes:
        if node_types.intersection(set(node.type_hierarchy)):
            for instance in node.instances:
                if any(configuration_node_id == relationship
                        .target_node_instance.node_id
                       for relationship in instance.relationships) \
                        and needs_to_get_updated(params, instance):
                    func(instance=instance, ctx=ctx, **func_kwargs)


