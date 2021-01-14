# Copyright (c) 2018 Cloudify Platform Ltd. All rights reserved
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

from cloudify.workflows import api
from cloudify.workflows import tasks
from cloudify.plugins import lifecycle
from cloudify.decorators import workflow
from cloudify.manager import get_rest_client

from cloudify_common_sdk._compat import text_type
from cloudify_common_sdk.filters import (get_field_value_recursive,
                                         obfuscate_passwords, )


def _update_runtime_properties(ctx, instance_id, properties_updates):
    manager = get_rest_client()

    resulted_state = manager.node_instances.get(instance_id)
    ctx.logger.debug('State before update: {}'
                     .format(repr(obfuscate_passwords(resulted_state))))
    ctx.logger.info("Update node: {}".format(instance_id))
    runtime_properties = resulted_state.runtime_properties or {}
    runtime_properties.update(properties_updates)
    manager.node_instances.update(node_instance_id=instance_id,
                                  runtime_properties=runtime_properties,
                                  version=resulted_state.version + 1)
    resulted_state = manager.node_instances.get(instance_id)
    ctx.logger.debug('State after update: {}'
                     .format(repr(obfuscate_passwords(resulted_state))))


def _cleanup_instances(ctx, instance_ids):
    manager = get_rest_client()

    for instance_id in instance_ids:
        resulted_state = manager.node_instances.get(instance_id)
        ctx.logger.debug('State before update: {}'
                         .format(repr(obfuscate_passwords(resulted_state))))
        ctx.logger.info("Cleanup node: {}".format(instance_id))
        manager.node_instances.update(node_instance_id=instance_id,
                                      runtime_properties={},
                                      state='uninitialized',
                                      version=resulted_state.version + 1)
        resulted_state = manager.node_instances.get(instance_id)
        ctx.logger.debug('State after update: {}'
                         .format(repr(obfuscate_passwords(resulted_state))))


def _deployments_get_groups(ctx):
    client = get_rest_client()
    deployment = client.deployments.get(
        ctx.deployment.id, _include=['groups'])
    return deployment['groups']


def _get_transaction_instances(ctx, scale_transaction_field,
                               scale_node_names, scale_node_field_path,
                               scale_node_field_values, all_results=False):
    client = get_rest_client()
    # search transaction ids
    list_kwargs = {
        'deployment_id': ctx.deployment.id,
        '_include': ['runtime_properties', 'node_id', 'id']
    }
    if all_results:
        list_kwargs['_get_all_results'] = True
    instances = client.node_instances.list(**list_kwargs)
    transaction_ids = []
    node_instances = {}
    instance_ids = []

    for instance in instances:
        runtime_properties = instance.runtime_properties
        # check that we have correct node name
        if scale_node_names and instance.node_id not in scale_node_names:
            continue
        # check that we have such values in properties
        value = get_field_value_recursive(ctx.logger,
                                          runtime_properties,
                                          scale_node_field_path)
        if value not in scale_node_field_values:
            continue
        # save instances to scale "settings", for case when instances created
        # without transaction
        if not node_instances.get(instance.node_id):
            node_instances[instance.node_id] = []
        # save node type (instances without transaction)
        if instance.id not in node_instances[instance.node_id]:
            node_instances[instance.node_id].append(instance.id)
        # save exact instance id (instances without transaction)
        if instance.id not in instance_ids:
            instance_ids.append(instance.id)
        # ignore transaction
        if not scale_transaction_field:
            continue
        # check transactions
        if not runtime_properties.get(scale_transaction_field):
            continue
        # save transaction to list
        transaction_ids.append(
            runtime_properties.get(scale_transaction_field))

    # list will be empty if no scale_transaction_field
    if not transaction_ids:
        ctx.logger.debug("List nodes: {}".format(repr(node_instances)))
        ctx.logger.debug("List instances: {}".format(repr(instance_ids)))
        return node_instances, instance_ids

    ctx.logger.debug("Transaction ids: {}".format(repr(transaction_ids)))

    # search instances for remove
    instances = client.node_instances.list(**list_kwargs)

    for instance in instances:
        runtime_properties = instance.runtime_properties
        transaction_id = runtime_properties.get(scale_transaction_field)
        # not our transaction, skip
        if transaction_id not in transaction_ids:
            continue
        # no such group yet
        if not node_instances.get(instance.node_id):
            node_instances[instance.node_id] = []
        # maybe we already have such type
        if instance.id not in node_instances[instance.node_id]:
            node_instances[instance.node_id].append(instance.id)
        # maybe we already have such instance
        if instance.id not in instance_ids:
            instance_ids.append(instance.id)

    ctx.logger.debug("List nodes: {}".format(repr(node_instances)))
    ctx.logger.debug("List instances: {}".format(repr(instance_ids)))
    return node_instances, instance_ids


def _get_scale_list(ctx, scalable_entity_properties, property_type):
    # scalable_entity_properties - dictionary with such structure:
    # {
    #   node_name: [{runtime_properties}]
    # }
    # property_type - kind of values inside list of node names(types).
    scalable_entity_dict = {}
    scaling_groups = ctx.deployment.scaling_groups
    groups = _deployments_get_groups(ctx)

    ctx.logger.debug("Scale entities: {}"
                     .format(repr(scalable_entity_properties)))

    if not isinstance(scalable_entity_properties, dict):
        raise ValueError(
            "You use wrong value for 'scalable_entity_properties': {}"
            .format(repr(scalable_entity_properties)))

    for node_name in scalable_entity_properties:
        # get node counts
        node_amount = len(scalable_entity_properties[node_name])

        if not isinstance(scalable_entity_properties[node_name], list):
            raise ValueError(
                "You use wrong value for 'scalable_entity_properties' item: {}"
                .format(repr(scalable_entity_properties[node_name])))
        for el in scalable_entity_properties[node_name]:
            if not isinstance(el, property_type):
                raise ValueError(
                    "You use wrong value for runtime properties item: {}"
                    .format(repr(scalable_entity_properties[node_name])))
        # get parent group
        for scalegroup in groups:
            # check that we really have such scalling group
            if scalegroup not in scaling_groups:
                continue
            # check node in nodes group
            if node_name in groups[scalegroup]['members']:
                # not selected
                if scalegroup not in scalable_entity_dict:
                    scalable_entity_dict[scalegroup] = {
                        'count': 0,
                        'values': []
                    }
                # already have have such group, scale by max value
                if scalable_entity_dict[scalegroup]['count'] < node_amount:
                    scalable_entity_dict[scalegroup]['count'] = node_amount
                # save instance id's for scale down workflow
                # ignored for scale up
                scalable_entity_dict[scalegroup]['values'] += (
                    scalable_entity_properties[node_name]
                )
                break
        else:
            # no such group
            if node_name not in scalable_entity_dict:
                scalable_entity_dict[node_name] = {
                    'count': 0,
                    'values': []
                }
            scalable_entity_dict[node_name]['count'] = node_amount
            scalable_entity_dict[node_name]['values'] += (
                scalable_entity_properties[node_name]
            )

    ctx.logger.info("Scale rules: {}".format(
        repr(obfuscate_passwords(scalable_entity_dict))))
    return scalable_entity_dict


def _process_node_instances(ctx, graph, node_instances, ignore_failure,
                            node_instance_subgraph_func, node_sequence):
    ctx.logger.info("Scale sequence: {}".format(repr(node_sequence)))
    subgraphs = {}
    node_graphs = {}
    for node_instance in node_instances:
        node_id = node_instance._node_instance.node_id
        if node_id not in node_graphs:
            node_graphs[node_id] = []
        node_graphs[node_id].append(node_instance)
        subgraphs[node_instance.id] = node_instance_subgraph_func(
            node_instance, graph, ignore_failure=ignore_failure)

    ctx.logger.info("Scale levels: {}".format(repr(node_graphs)))
    previous_level = []
    for node_id in node_sequence:
        # use get for skip instances with unknow type
        if not node_graphs.get(node_id, []):
            continue
        current_level_instances = node_graphs[node_id]
        for target_instance in current_level_instances:
            for source_instance in previous_level:
                ctx.logger.info("Scale dependency: {}->{}"
                                .format(source_instance.id,
                                        target_instance.id))
                graph.add_dependency(subgraphs[source_instance.id],
                                     subgraphs[target_instance.id])
        # replace previous with current instances
        previous_level = current_level_instances
    graph.execute()


def _uninstall_instances(ctx, graph, removed, related, ignore_failure,
                         node_sequence):

    # cleanup tasks
    for task in graph.tasks_iter():
        graph.remove_task(task)

    if removed:
        if node_sequence:
            subgraph_func = lifecycle.uninstall_node_instance_subgraph
            _process_node_instances(
                ctx=ctx,
                graph=graph,
                node_instances=removed,
                ignore_failure=ignore_failure,
                node_instance_subgraph_func=subgraph_func,
                node_sequence=node_sequence[::-1])
        else:
            lifecycle.uninstall_node_instances(
                graph=graph,
                node_instances=removed,
                related_nodes=related,
                ignore_failure=ignore_failure)

        # clean up properties
        instance_ids = [node_instance._node_instance.id
                        for node_instance in removed]
        _cleanup_instances(ctx, instance_ids)


def _run_scale_settings(ctx, scale_settings, scalable_entity_properties,
                        scale_transaction_field=None,
                        scale_transaction_value=None,
                        ignore_failure=False,
                        ignore_rollback_failure=True,
                        instances_remove_ids=None,
                        node_sequence=None):
    modification = ctx.deployment.start_modification(scale_settings)
    ctx.refresh_node_instances()
    graph = ctx.graph_mode()
    try:
        ctx.logger.info('Deployment modification started. '
                        '[modification_id={0}]'.format(modification.id))
        if len(set(modification.added.node_instances)):
            ctx.logger.info('Added: {}'.format(repr([
                node_instance._node_instance.id
                for node_instance in modification.added.node_instances
                if node_instance.modification == 'added'
            ])))
            added_and_related = set(modification.added.node_instances)
            added = set(i for i in added_and_related
                        if i.modification == 'added')
            related = added_and_related - added
            try:
                for node_instance in added:
                    properties_updates = scalable_entity_properties.get(
                        node_instance._node_instance.node_id, {})
                    # save properties updates
                    properties = {}
                    if properties_updates:
                        # pop one dict for runtime properties
                        properties.update(properties_updates.pop())
                    # save transaction list
                    if scale_transaction_field:
                        # save original set of instances in scale up.
                        if scale_transaction_value:
                            properties.update({
                                scale_transaction_field:
                                    scale_transaction_value
                            })
                        else:
                            properties.update({
                                scale_transaction_field: modification.id
                            })
                    # check properties to update
                    if properties:
                        ctx.logger.debug(
                            "{}: Updating {} runtime properties by {}".format(
                                node_instance._node_instance.node_id,
                                node_instance._node_instance.id,
                                repr(obfuscate_passwords(properties))))
                        _update_runtime_properties(
                            ctx, node_instance._node_instance.id, properties)
                if node_sequence:
                    subgraph_func = lifecycle.install_node_instance_subgraph
                    _process_node_instances(
                        ctx=ctx,
                        graph=graph,
                        node_instances=added,
                        ignore_failure=ignore_failure,
                        node_instance_subgraph_func=subgraph_func,
                        node_sequence=node_sequence)
                else:
                    lifecycle.install_node_instances(
                        graph=graph,
                        node_instances=added,
                        related_nodes=related)
            except Exception as ex:
                ctx.logger.error('Scale out failed, scaling back in. {}'
                                 .format(repr(ex)))
                _wait_for_sent_tasks(ctx, graph)
                _uninstall_instances(ctx=ctx,
                                     graph=graph,
                                     removed=added,
                                     related=related,
                                     ignore_failure=ignore_rollback_failure,
                                     node_sequence=node_sequence)
                raise ex

        if len(set(modification.removed.node_instances)):
            ctx.logger.info('Removed: {}'.format(repr([
                node_instance._node_instance.id
                for node_instance in modification.removed.node_instances
                if node_instance.modification == 'removed'
            ])))
            removed_and_related = set(modification.removed.node_instances)
            removed = set(i for i in removed_and_related
                          if i.modification == 'removed')
            ctx.logger.info('Proposed: {}'
                            .format(repr(instances_remove_ids)))
            if instances_remove_ids:
                for instance in removed:
                    if instance._node_instance.id not in instances_remove_ids:
                        raise Exception(
                            "Instance {} not in proposed list {}.".format(
                                repr(instance._node_instance.id),
                                repr(instances_remove_ids)
                            )
                        )
            related = removed_and_related - removed
            _uninstall_instances(ctx=ctx,
                                 graph=graph,
                                 removed=removed,
                                 ignore_failure=ignore_failure,
                                 related=related,
                                 node_sequence=node_sequence)
    except Exception as ex:
        ctx.logger.warn('Rolling back deployment modification. '
                        '[modification_id={0}]: {1}'
                        .format(modification.id, repr(ex)))
        _wait_for_sent_tasks(ctx, graph)
        modification.rollback()
        raise ex
    else:
        modification.finish()


def _wait_for_sent_tasks(ctx, graph):
    """Wait for tasks that are in the SENT state to return"""
    for task in graph.tasks_iter():
        # Check type.
        ctx.logger.debug(
            'Parallel task to failed task: {0}. State: {1}'.format(
                task.id, task.get_state()))
    try:
        deadline = time.time() + ctx.wait_after_fail
    except AttributeError:
        deadline = time.time() + 1800
    while deadline > time.time():
        try:
            cancelled = api.has_cancel_request()
        except AttributeError:
            cancelled = graph._is_execution_cancelled()
        if cancelled:
            raise api.ExecutionCancelled()
        try:
            finished_tasks = graph._finished_tasks()
        except AttributeError:
            finished_tasks = graph._terminated_tasks()
        for task in finished_tasks:
            try:
                graph._handle_terminated_task(task)
            except RuntimeError:
                ctx.logger.error('Unhandled Failed task: {0}'.format(task))
        if not any(task.get_state() == tasks.TASK_SENT
                   for task in graph.tasks_iter()):
            break
        else:
            time.sleep(0.1)


def _scaledown_group_to_settings(ctx, list_scale_groups, scale_compute):
    scale_settings = {}
    for scalable_entity_name in list_scale_groups:
        delta = list_scale_groups[scalable_entity_name]['count']
        instances_remove = list_scale_groups[scalable_entity_name]['values']
        ctx.logger.info('Scale down {} by delta: {}'
                        .format(repr(scalable_entity_name),
                                repr(delta)))
        if delta == 0:
            ctx.logger.info('delta parameter is 0, so no scaling will '
                            'take place.')
            continue

        scaling_group = ctx.deployment.scaling_groups.get(scalable_entity_name)
        if scaling_group:
            curr_num_instances = (
                scaling_group['properties']['current_instances']
            )
            planned_num_instances = curr_num_instances - delta
            scale_id = scalable_entity_name
        else:
            node = ctx.get_node(scalable_entity_name)
            if not node:
                raise ValueError("No scalable entity named {0} was found"
                                 .format(scalable_entity_name))
            host_node = node.host_node
            scaled_node = host_node if (scale_compute and host_node) else node
            curr_num_instances = scaled_node.number_of_instances
            planned_num_instances = curr_num_instances - delta
            scale_id = scaled_node.id

        scale_settings[scale_id] = {
            'instances': planned_num_instances,
            'removed_ids_include_hint': instances_remove,
        }

    ctx.logger.info(
        'Scale settings: {}'.format(repr(obfuscate_passwords(scale_settings))))
    return scale_settings


@workflow
def scaledownlist(ctx, scale_compute=False,
                  ignore_failure=False,
                  force_db_cleanup=False,
                  scale_transaction_field=u'',
                  scale_node_name=None,
                  scale_node_field=u'',
                  scale_node_field_value=u'',
                  all_results=False,
                  node_sequence=None,
                  **_):
    if not scale_node_field:
        raise ValueError('You should provide `scale_node_field` for correct'
                         'downscale.')

    if isinstance(scale_node_field_value, text_type):
        scale_node_field_value = [scale_node_field_value]

    ctx.logger.debug("Filter by values list: {}.".format(
        repr(obfuscate_passwords(scale_node_field_value))))

    if not scale_node_name:
        scale_node_name = None
        ctx.logger.debug("Will be searched by all instances.")

    if isinstance(scale_node_name, text_type):
        scale_node_name = [scale_node_name]

    if isinstance(scale_node_field, text_type):
        scale_node_field = [scale_node_field]

    instances, instance_ids = _get_transaction_instances(
        ctx=ctx,
        scale_transaction_field=scale_transaction_field,
        scale_node_names=scale_node_name,
        scale_node_field_path=scale_node_field,
        scale_node_field_values=scale_node_field_value,
        all_results=all_results)

    if not instance_ids:
        ctx.logger.info("Empty list for instances for remove.")
        return

    # we have list of instances_id(string) as part of scale dictionary
    scale_settings = _scaledown_group_to_settings(
        ctx, _get_scale_list(ctx, instances, text_type), scale_compute)

    try:
        _run_scale_settings(ctx, scale_settings, {},
                            instances_remove_ids=instance_ids,
                            ignore_failure=ignore_failure,
                            node_sequence=node_sequence)
    except Exception as e:
        ctx.logger.info('Scale down based on transaction failed: {}'
                        .format(repr(e)))
        # check list for forced remove
        removed = []
        for node in ctx.nodes:
            for instance in node.instances:
                if instance.id in instance_ids:
                    removed.append(instance)
        _uninstall_instances(ctx=ctx,
                             graph=ctx.graph_mode(),
                             removed=removed,
                             related=[],
                             ignore_failure=ignore_failure,
                             node_sequence=node_sequence)

        # remove from DB
        if force_db_cleanup:
            ctx.logger.warn('Ignoring force_db_cleanup. Deprecated feature.')


def _scaleup_group_to_settings(ctx, scalable_entity_dict, scale_compute):
    scale_settings = {}
    for scalable_entity_name in scalable_entity_dict:
        delta = scalable_entity_dict[scalable_entity_name]['count']
        ctx.logger.info('Scale up {} by delta: {}'
                        .format(repr(scalable_entity_name),
                                repr(delta)))
        if delta == 0:
            ctx.logger.info('delta parameter is 0, so no scaling will '
                            'take place.')
            continue

        scaling_group = ctx.deployment.scaling_groups.get(scalable_entity_name)
        if scaling_group:
            curr_num_instances = (
                scaling_group['properties']['current_instances']
            )
            planned_num_instances = curr_num_instances + delta
            scale_id = scalable_entity_name
        else:
            node = ctx.get_node(scalable_entity_name)
            if not node:
                raise ValueError("No scalable entity named {0} was found"
                                 .format(scalable_entity_name))
            host_node = node.host_node
            scaled_node = host_node if (scale_compute and host_node) else node
            curr_num_instances = scaled_node.number_of_instances
            planned_num_instances = curr_num_instances + delta
            scale_id = scaled_node.id

        scale_settings[scale_id] = {
            'instances': planned_num_instances,
        }

    ctx.logger.info('Scale settings: {}'.format(
        repr(obfuscate_passwords(scale_settings))))
    return scale_settings


@workflow
def scaleuplist(ctx, scalable_entity_properties,
                scale_compute=False,
                ignore_failure=False,
                ignore_rollback_failure=True,
                scale_transaction_field="",
                scale_transaction_value="",
                node_sequence=None,
                **kwargs):

    if not scalable_entity_properties:
        raise ValueError('Empty list of scale nodes')

    # we have list of dictionaries with runtime properties for new instances as
    # part of scale dictionary
    scale_settings = _scaleup_group_to_settings(
        ctx, _get_scale_list(ctx, scalable_entity_properties, dict),
        scale_compute)

    _run_scale_settings(ctx, scale_settings, scalable_entity_properties,
                        scale_transaction_field, scale_transaction_value,
                        ignore_failure, ignore_rollback_failure,
                        node_sequence=node_sequence)


def _filter_node_instances(ctx, node_ids, node_instance_ids, type_names,
                           operation, node_field_path, node_field_value):
    filtered_node_instances = []
    for node in ctx.nodes:
        # no such action skip it
        if operation not in node.operations:
            continue
        # no such node_id, skip it
        if node_ids and node.id not in node_ids:
            continue
        # no such node type, skip it
        if type_names and not next((type_name for type_name in type_names if
                                    type_name in node.type_hierarchy), None):
            continue

        # look more deeply, what about instance id's and properties
        for instance in node.instances:
            # sorry no such id in list
            if node_instance_ids and instance.id not in node_instance_ids:
                continue
            # look to field value
            if node_field_path:
                # check that we have such values in properties
                runtime_properties = instance._node_instance.runtime_properties
                value = get_field_value_recursive(ctx.logger,
                                                  runtime_properties,
                                                  node_field_path)
                if value not in node_field_value:
                    continue
            # looks as good instance
            filtered_node_instances.append(instance)
    return filtered_node_instances


@workflow
def execute_operation(ctx, operation, operation_kwargs, allow_kwargs_override,
                      run_by_dependency_order, type_names, node_ids,
                      node_instance_ids, node_field, node_field_value,
                      **kwargs):
    """ A generic workflow for executing arbitrary operations on nodes """

    if isinstance(node_field_value, text_type):
        node_field_value = [node_field_value]

    ctx.logger.debug("Filter by values list: {}."
                     .format(repr(obfuscate_passwords(node_field_value))))

    graph = ctx.graph_mode()
    subgraphs = {}

    if isinstance(node_field, text_type):
        node_field = [node_field]

    # filtering node instances
    filtered_node_instances = _filter_node_instances(
        ctx=ctx,
        node_ids=node_ids,
        node_instance_ids=node_instance_ids,
        type_names=type_names,
        operation=operation,
        node_field_path=node_field,
        node_field_value=node_field_value)

    if run_by_dependency_order:
        # if run by dependency order is set, then create stub subgraphs for the
        # rest of the instances. This is done to support indirect
        # dependencies, i.e. when instance A is dependent on instance B
        # which is dependent on instance C, where A and C are to be executed
        # with the operation on (i.e. they're in filtered_node_instances)
        # yet B isn't.
        # We add stub subgraphs rather than creating dependencies between A
        # and C themselves since even though it may sometimes increase the
        # number of dependency relationships in the execution graph, it also
        # ensures their number is linear to the number of relationships in
        # the deployment (e.g. consider if A and C are one out of N instances
        # of their respective nodes yet there's a single instance of B -
        # using subgraphs we'll have 2N relationships instead of N^2).
        filtered_node_instances_ids = set(inst.id for inst in
                                          filtered_node_instances)
        for instance in ctx.node_instances:
            if instance.id not in filtered_node_instances_ids:
                subgraphs[instance.id] = graph.subgraph(instance.id)

    # preparing the parameters to the execute_operation call
    exec_op_params = {
        'kwargs': operation_kwargs,
        'operation': operation
    }
    if allow_kwargs_override is not None:
        exec_op_params['allow_kwargs_override'] = allow_kwargs_override

    # registering actual tasks to sequences
    for instance in filtered_node_instances:
        start_event_message = 'Starting operation {0}'.format(operation)
        if operation_kwargs:
            start_event_message += ' (Operation parameters: {0})'.format(
                repr(operation_kwargs))
        subgraph = graph.subgraph(instance.id)
        sequence = subgraph.sequence()
        sequence.add(
            instance.send_event(start_event_message),
            instance.execute_operation(**exec_op_params),
            instance.send_event('Finished operation {0}'.format(operation)))
        subgraphs[instance.id] = subgraph

    # adding tasks dependencies if required
    if run_by_dependency_order:
        for instance in ctx.node_instances:
            for rel in instance.relationships:
                graph.add_dependency(subgraphs[instance.id],
                                     subgraphs[rel.target_id])

    graph.execute()
