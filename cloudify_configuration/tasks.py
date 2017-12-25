
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


def _merge_dicts(d1, d2):
    result = d1.copy()
    for key, new_val in d2.iteritems():
        current_val = result.get(key)
        if isinstance(current_val, dict) and isinstance(new_val, dict):
            result[key] = _merge_dicts(current_val, new_val)
        else:
            result[key] = new_val
    return result


def load_configuration(parameters, merge_dicts, **kwargs):
    # load params
    if isinstance(parameters, dict):
        params = parameters
    else:
        params = json.loads(parameters)

    # get previous params
    p = ctx.instance.runtime_properties.get('params', {})
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
    params['old_params'] = {}

    # find changed params between old params and populated params
    diff_params = [k for k, v in params.iteritems() if v != old_params.get(k)]

    # populate the old params into params
    params['old_params'] = old_params

    # populate diff_params inot params
    params['diff_params'] = diff_params

    ctx.logger.info("Show params: {}".format(params))
    ctx.logger.info("Show old params: {}".format(old_params))
    ctx.logger.info("Show diff params: {}".format(diff_params))

    # update params to runtime properties
    ctx.source.instance.runtime_properties['params'] = params


@workflow
def update(params, configuration_node_type, node_types_to_update, **kwargs):
    ctx = workflow_ctx
    ctx.logger.info("Starting Update Workflow")

    restcli = manager.get_rest_client()

    node_types = set(node_types_to_update)
    # update interface on the config node
    graph = ctx.graph_mode()

    sequence = graph.sequence()
    for node in ctx.nodes:
        if configuration_node_type in node.type_hierarchy:
            for instance in node.instances:
                load_config_task = instance.execute_operation(
                    'cloudify.interfaces.lifecycle.configure',
                    allow_kwargs_override=True, kwargs={'parameters': params}
                )
                sequence.add(load_config_task)

    for node in ctx.nodes:
        if node_types.intersection(set(node.type_hierarchy)):
            for instance in node.instances:
                for relationship in instance.relationships:
                    operation_task = relationship.execute_target_operation(
                        'cloudify.interfaces.relationship_lifecycle'
                        '.preconfigure'
                    )
                    sequence.add(operation_task)

    graph.execute()

    sequence = graph.sequence()

    for node in ctx.nodes:
        if node_types.intersection(set(node.type_hierarchy)):
            for instance in node.instances:
                currentinstance = restcli.node_instances.get(instance.id)
                params = currentinstance.runtime_properties['params']
                if len(params['diff_params']) > 0:
                    ctx.logger.info(
                        "Updating instance ID: {} with diff_params {}".format(
                            instance.id, params['diff_params']
                        )
                    )
                    operation_task = instance.execute_operation(
                        'cloudify.interfaces.lifecycle.update'
                    )
                    sequence.add(operation_task)

    return graph.execute()
