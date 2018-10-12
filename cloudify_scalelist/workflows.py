# Copyright (c) 2018 GigaSpaces Technologies Ltd. All rights reserved
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
from cloudify.decorators import workflow
from cloudify.plugins import lifecycle
from cloudify.manager import get_rest_client


def _update_runtime_properties(ctx, instance_id, properties_updates):
    manager = get_rest_client()

    resulted_state = manager.node_instances.get(instance_id)
    ctx.logger.debug('State before update: {}'
                     .format(repr(resulted_state)))
    ctx.logger.info("Update node: {}".format(instance_id))
    runtime_properties = resulted_state.runtime_properties or {}
    runtime_properties.update(properties_updates)
    manager.node_instances.update(node_instance_id=instance_id,
                                  runtime_properties=runtime_properties,
                                  version=resulted_state.version + 1)
    resulted_state = manager.node_instances.get(instance_id)
    ctx.logger.debug('State after update: {}'
                     .format(repr(resulted_state)))


def _cleanup_instances(ctx, instance_ids):
    manager = get_rest_client()

    for instance_id in instance_ids:
        resulted_state = manager.node_instances.get(instance_id)
        ctx.logger.debug('State before update: {}'
                         .format(repr(resulted_state)))
        ctx.logger.info("Cleanup node: {}".format(instance_id))
        manager.node_instances.update(node_instance_id=instance_id,
                                      runtime_properties={},
                                      state='uninitialized',
                                      version=resulted_state.version + 1)
        resulted_state = manager.node_instances.get(instance_id)
        ctx.logger.debug('State after update: {}'
                         .format(repr(resulted_state)))


def _deployments_get_groups(ctx):
    client = get_rest_client()
    deployment = client.deployments.get(
        ctx.deployment.id, _include=['groups'])
    return deployment['groups']


def _get_field_value_recursive(ctx, properties, path):
    if not path:
        return properties
    key = path[0]
    if isinstance(properties, list):
        try:
            return _get_field_value_recursive(
                ctx,
                properties[int(key)],
                path[1:]
            )
        except Exception as e:
            ctx.logger.debug('Can filter by {}'.format(repr(e)))
            return None
    elif isinstance(properties, dict):
        try:
            return _get_field_value_recursive(
                ctx,
                properties[key],
                path[1:]
            )
        except Exception as e:
            ctx.logger.debug('Can filter by {}'.format(repr(e)))
            return None
    else:
        return None


def _get_transaction_instances(ctx, scale_transaction_field,
                               scale_node_names, scale_node_field_path,
                               scale_node_field_values):
    client = get_rest_client()
    # search transaction ids
    instances = client.node_instances.list(deployment_id=ctx.deployment.id,
                                           _include=['runtime_properties',
                                                     'node_id', 'id'])
    transaction_ids = []
    node_instances = {}
    instance_ids = []

    for instance in instances:
        runtime_properties = instance.runtime_properties
        # check that we have correct node name
        if scale_node_names and instance.node_id not in scale_node_names:
            continue
        # check that we have such values in properties
        value = _get_field_value_recursive(ctx,
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
    instances = client.node_instances.list(deployment_id=ctx.deployment.id,
                                           _include=['runtime_properties',
                                                     'id', 'node_id'])

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


def _get_scale_list(ctx, scalable_entity_properties):
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

    ctx.logger.info("Scale rules: {}".format(repr(scalable_entity_dict)))
    return scalable_entity_dict


def _uninstall_instances(ctx, graph, removed, related, ignore_failure):

    # cleanup tasks
    for task in graph.tasks_iter():
        graph.remove_task(task)

    if removed:
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
                        instances_remove_ids=None):
    modification = ctx.deployment.start_modification(scale_settings)
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
                                repr(properties)))
                        _update_runtime_properties(
                            ctx, node_instance._node_instance.id, properties)
                lifecycle.install_node_instances(
                    graph=graph,
                    node_instances=added,
                    related_nodes=related)
            except Exception as ex:
                ctx.logger.error('Scale out failed, scaling back in. {}'
                                 .format(repr(ex)))
                _uninstall_instances(ctx, graph, added, related,
                                     ignore_rollback_failure)
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
            lifecycle.uninstall_node_instances(
                graph=graph,
                node_instances=removed,
                ignore_failure=ignore_failure,
                related_nodes=related)
    except Exception as ex:
        ctx.logger.warn('Rolling back deployment modification. '
                        '[modification_id={0}]: {1}'
                        .format(modification.id, repr(ex)))
        modification.rollback()
        raise ex
    else:
        modification.finish()


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
            # need to run sorted only for tests and have same sequence of id's
            'removed_ids_include_hint': sorted(instances_remove),
        }

    ctx.logger.info('Scale settings: {}'.format(repr(scale_settings)))
    return scale_settings


@workflow
def scaledownlist(ctx, scale_compute=False,
                  ignore_failure=False,
                  scale_transaction_field="",
                  scale_node_name=None,
                  scale_node_field="",
                  scale_node_field_value="",
                  **kwargs):
    if (
        not scale_node_field
    ):
        raise ValueError('You should provide `scale_node_field` for correct'
                         'downscale.')

    if isinstance(scale_node_field_value, basestring):
        scale_node_field_value = [scale_node_field_value]

    ctx.logger.debug("Filter by values list: {}."
                     .format(repr(scale_node_field_value)))

    if not scale_node_name:
        scale_node_name = None
        ctx.logger.debug("Will be searched by all instances.")

    if isinstance(scale_node_name, basestring):
        scale_node_name = [scale_node_name]

    if isinstance(scale_node_field, basestring):
        scale_node_field = [scale_node_field]

    instances, instance_ids = _get_transaction_instances(
        ctx=ctx,
        scale_transaction_field=scale_transaction_field,
        scale_node_names=scale_node_name,
        scale_node_field_path=scale_node_field,
        scale_node_field_values=scale_node_field_value)

    if not instance_ids:
        ctx.logger.info("Empty list for instances for remove.")
        return

    scale_settings = _scaledown_group_to_settings(
        ctx, _get_scale_list(ctx, instances), scale_compute)

    try:
        _run_scale_settings(ctx, scale_settings, {},
                            instances_remove_ids=instance_ids,
                            ignore_failure=ignore_failure)
    except Exception as e:
        ctx.logger.info('Scale down based on transaction failed: {}'
                        .format(repr(e)))
        # check list for forced remove
        removed = []
        for node in ctx.nodes:
            for instance in node.instances:
                if instance.id in instance_ids:
                    removed.append(instance)
        _uninstall_instances(ctx, ctx.graph_mode(), removed, [],
                             ignore_failure)


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

    ctx.logger.info('Scale settings: {}'.format(repr(scale_settings)))
    return scale_settings


@workflow
def scaleuplist(ctx, scalable_entity_properties,
                scale_compute=False,
                ignore_failure=False,
                ignore_rollback_failure=True,
                scale_transaction_field="",
                scale_transaction_value="",
                **kwargs):

    if not scalable_entity_properties:
        raise ValueError('Empty list of scale nodes')

    scale_settings = _scaleup_group_to_settings(
        ctx, _get_scale_list(ctx, scalable_entity_properties), scale_compute)

    _run_scale_settings(ctx, scale_settings, scalable_entity_properties,
                        scale_transaction_field, scale_transaction_value,
                        ignore_failure, ignore_rollback_failure)


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
                value = _get_field_value_recursive(ctx,
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

    if isinstance(node_field_value, basestring):
        node_field_value = [node_field_value]

    ctx.logger.debug("Filter by values list: {}."
                     .format(repr(node_field_value)))

    graph = ctx.graph_mode()
    subgraphs = {}

    if isinstance(node_field, basestring):
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
