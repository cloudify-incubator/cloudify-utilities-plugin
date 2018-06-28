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


def _get_transaction_instances(ctx, scale_transaction_field,
                               scale_node_name, scale_node_field,
                               scale_node_field_value):
    client = get_rest_client()
    # search transaction ids
    instances = client.node_instances.list(deployment_id=ctx.deployment.id,
                                           node_id=scale_node_name,
                                           _include=['runtime_properties'])
    transaction_ids = []

    for instance in instances:
        runtime_properties = instance.runtime_properties
        if not runtime_properties.get(scale_transaction_field):
            continue

        if runtime_properties.get(scale_node_field) == scale_node_field_value:
            transaction_ids.append(
                runtime_properties.get(scale_transaction_field))

    ctx.logger.debug("Transaction ids: {}".format(repr(instances)))

    if not transaction_ids:
        return {}, []

    # search instances for remove
    node_instances = {}
    instance_ids = []
    instances = client.node_instances.list(deployment_id=ctx.deployment.id,
                                           _include=['runtime_properties',
                                                     'id', 'node_id'])

    for instance in instances:
        runtime_properties = instance.runtime_properties
        transaction_id = runtime_properties.get(scale_transaction_field)
        if transaction_id not in transaction_ids:
            continue
        if not node_instances.get(instance.node_id):
            node_instances[instance.node_id] = []
        node_instances[instance.node_id].append(instance.id)
        instance_ids.append(instance.id)

    ctx.logger.info("List instances: {}".format(repr(node_instances)))
    return node_instances, instance_ids


def _get_scale_list(ctx, scalable_entity_properties):
    scalable_entity_dict = {}
    scaling_groups = ctx.deployment.scaling_groups
    groups = _deployments_get_groups(ctx)

    for node_name in scalable_entity_properties:
        # get node counts
        node_amount = len(scalable_entity_properties[node_name])

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


def _uninstall_instances(ctx, graph, instance_ids, related_ids,
                         ignore_failure):

    # cleanup tasks
    for task in graph.tasks_iter():
        graph.remove_task(task)

    # hacks for remove
    removed = []
    related = []
    for node in ctx.nodes:
        for instance in node.instances:
            if instance.id in instance_ids:
                removed.append(instance)
            if instance.id in related_ids:
                related.append(instance)

    if removed:
        lifecycle.uninstall_node_instances(
            graph=graph,
            node_instances=removed,
            related_nodes=related,
            ignore_failure=ignore_failure)

    # clean up properties
    _cleanup_instances(ctx, instance_ids)


def _run_scale_settings(ctx, scale_settings, scalable_entity_properties,
                        scale_transaction_field=None,
                        scale_transaction_value=None,
                        ignore_failure=False,
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
                _uninstall_instances(
                    ctx, graph, [
                        node_instance._node_instance.id
                        for node_instance in added
                    ], [
                        node_instance._node_instance.id
                        for node_instance in related
                    ], ignore_failure)
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
                  scale_node_name="",
                  scale_node_field="",
                  scale_node_field_value="",
                  **kwargs):
    if (
        not scale_transaction_field or
        not scale_node_name or
        not scale_node_field
    ):
        raise ValueError('You should provide {} for correct downscale.'
                         .format(repr(
                            ["scale_transaction_field",
                             "scale_node_name",
                             "scale_node_field"])))

    instances, instance_ids = _get_transaction_instances(
        ctx, scale_transaction_field, scale_node_name, scale_node_field,
        scale_node_field_value)

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
        _uninstall_instances(ctx, ctx.graph_mode(), instance_ids, [],
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
                scale_transaction_field="",
                scale_transaction_value="",
                **kwargs):

    if not scalable_entity_properties:
        raise ValueError('Empty list of scale nodes')

    scale_settings = _scaleup_group_to_settings(
        ctx, _get_scale_list(ctx, scalable_entity_properties), scale_compute)

    _run_scale_settings(ctx, scale_settings, scalable_entity_properties,
                        scale_transaction_field, scale_transaction_value,
                        ignore_failure)
