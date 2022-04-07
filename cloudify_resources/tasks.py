########
# Copyright (c) 2014-2019 Cloudify Platform Ltd. All rights reserved
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

from cloudify import ctx, manager
from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError, RecoverableError
from cloudify.utils import id_generator
from cloudify.constants import NODE_INSTANCE, RELATIONSHIP_INSTANCE
from cloudify_rest_client.client import CloudifyClient
from cloudify_types.shared_resource.constants import SHARED_RESOURCE_TYPE
from cloudify_types.shared_resource.operations import execute_workflow
from cloudify_types.shared_resource.execute_shared_resource_workflow import _get_target_shared_resource_client

from .constants import (
    RESOURCES_LIST_PROPERTY,
    FREE_RESOURCES_LIST_PROPERTY,
    RESERVATIONS_PROPERTY,
    SINGLE_RESERVATION_PROPERTY
)


def _refresh_source_and_target_runtime_props(ctx, **kwargs):
    ctx.source.instance.refresh()
    ctx.target.instance.refresh()


def _update_source_and_target_runtime_props(ctx, **kwargs):
    ctx.source.instance.update()
    ctx.target.instance.update()


@operation(resumable=True)
def create_list(ctx, **kwargs):
    resource_config = ctx.node.properties.get('resource_config', None)

    if not isinstance(resource_config, list):
        raise NonRecoverableError(
            'The "resource_config" property must be of type: list')

    ctx.logger.debug('Initializing resources list...')
    ctx.instance.runtime_properties[RESOURCES_LIST_PROPERTY] = resource_config
    ctx.instance.runtime_properties[FREE_RESOURCES_LIST_PROPERTY] = \
        resource_config
    ctx.instance.runtime_properties[RESERVATIONS_PROPERTY] = {}


@operation(resumable=True)
def create_list_item(ctx, **kwargs):
    ctx.logger.debug('Initializing list item...')
    ctx.instance.runtime_properties[SINGLE_RESERVATION_PROPERTY] = ''


@operation(resumable=True)
def delete_list_item(ctx, **kwargs):
    ctx.logger.debug('Removing list item: {}'.format(
        ctx.instance.runtime_properties.get(SINGLE_RESERVATION_PROPERTY)))
    ctx.instance.runtime_properties[SINGLE_RESERVATION_PROPERTY] = ''


@operation(resumable=True)
def delete_list(ctx, **kwargs):
    ctx.logger.debug('Removing resources list: {}'.format(
        ctx.instance.runtime_properties.get(RESOURCES_LIST_PROPERTY)))
    ctx.instance.runtime_properties[RESOURCES_LIST_PROPERTY] = []
    ctx.instance.runtime_properties[FREE_RESOURCES_LIST_PROPERTY] = []
    ctx.instance.runtime_properties[RESERVATIONS_PROPERTY] = {}


@operation(resumable=True)
def reserve_list_item(ctx, **kwargs):
    ctx.logger.debug('Operation kwargs: {}'.format(kwargs))
    if ctx.type == RELATIONSHIP_INSTANCE and \
            ctx.target.node.type == SHARED_RESOURCE_TYPE:
        _reserve_shared_list_item(ctx, resources_list_node_id=kwargs.get(
            'resources_list_node_id', None))
    elif ctx.type == RELATIONSHIP_INSTANCE:
        _reserve_list_item_rel(ctx)
    elif ctx.type == NODE_INSTANCE and \
            ctx.node.type == "cloudify.nodes.resources.List":
        _reserve_list_item(ctx, reservation_id=kwargs.get('reservation_id', None))
    else:
        NonRecoverableError("Neither relationship nor operation context.")


def _reserve_list_item_rel(ctx, **kwargs):
    if not ctx.target.instance.runtime_properties.get(
            FREE_RESOURCES_LIST_PROPERTY, []):
        raise NonRecoverableError(
            'Reservation has failed, because there are no \
            available resources right now.')

    _refresh_source_and_target_runtime_props(ctx)

    free_resources = \
        ctx.target.instance.runtime_properties.get(
            FREE_RESOURCES_LIST_PROPERTY)
    reservations = \
        ctx.target.instance.runtime_properties.get(
            RESERVATIONS_PROPERTY, {})

    ctx.source.instance.runtime_properties[SINGLE_RESERVATION_PROPERTY] = \
        free_resources.pop(0)

    ctx.target.instance.runtime_properties[FREE_RESOURCES_LIST_PROPERTY] = \
        free_resources

    reservations[ctx.source.instance.id] = \
        ctx.source.instance.runtime_properties.get(SINGLE_RESERVATION_PROPERTY)
    ctx.target.instance.runtime_properties[RESERVATIONS_PROPERTY] = \
        reservations

    _update_source_and_target_runtime_props(ctx)

    ctx.logger.debug('Reservation successful: {0}\
            \nLeft resources: {1}\
            \nReservations: {2}'.format(
        ctx.source.instance.runtime_properties.get(
            SINGLE_RESERVATION_PROPERTY),
        ctx.target.instance.runtime_properties.get(
            FREE_RESOURCES_LIST_PROPERTY),
        ctx.target.instance.runtime_properties.get(
            RESERVATIONS_PROPERTY)
    ))


def _reserve_shared_list_item(ctx, **kwargs):
    workflow_id = 'execute_operation'
    reserve_params = {
        'operation': 'cloudify.interfaces.operations.reserve',
        'allow_kwargs_override': True,
        'operation_kwargs': {
            'reservation_id': ctx.source.instance.id
        }
    }
    execute_workflow(workflow_id, reserve_params)

    # Cloudify client setup
    client_config = _get_target_shared_resource_client()
    if client_config:
        http_client = CloudifyClient(client_config)
    else:
        http_client = manager.get_rest_client()

    resources_list_node_id = kwargs.get('resources_list_node_id', None)
    target_deployment_id = (ctx.target.node
                            .properties['resource_config']
                            ['deployment']['id'])

    resources_list_instance = None

    if resources_list_node_id:
        resources_list_instance = http_client.node_instances.list(
            deployment_id=target_deployment_id,
            node_id=resources_list_node_id)[0]
    else:
        # if resources_list_node_id is not specified, first matching node
        # will be used
        for node in http_client.nodes.list(deployment_id=target_deployment_id):
            if node.type == 'cloudify.nodes.resources.List':
                resources_list_instance = http_client.node_instances.list(
                    deployment_id=target_deployment_id,
                    node_id=node.id)[0]
                break

    ctx.source.instance.runtime_properties[SINGLE_RESERVATION_PROPERTY] = \
        resources_list_instance.runtime_properties.get(
            RESERVATIONS_PROPERTY).get(ctx.source.instance.id)

    ctx.logger.debug('Reservation successful: {0}\
            \nLeft resources: {1}\
            \nReservations: {2}'.format(
        ctx.source.instance.runtime_properties.get(
            SINGLE_RESERVATION_PROPERTY),
        resources_list_instance.runtime_properties.get(
            FREE_RESOURCES_LIST_PROPERTY),
        resources_list_instance.runtime_properties.get(
            RESERVATIONS_PROPERTY)
    ))


def _reserve_list_item(ctx, **kwargs):
    if not ctx.instance.runtime_properties.get(
            FREE_RESOURCES_LIST_PROPERTY, []):
        raise NonRecoverableError(
            'Reservation has failed, because there are no \
            available resources right now.')

    reservation_id = kwargs.get('reservation_id', None)
    ctx.instance.refresh()

    free_resources = \
        ctx.instance.runtime_properties.get(
            FREE_RESOURCES_LIST_PROPERTY)
    reservations = \
        ctx.instance.runtime_properties.get(
            RESERVATIONS_PROPERTY, {})

    if not reservation_id:
        reservation_id = id_generator(size=8)
        if reservation_id in reservations:
            raise RecoverableError('reservation_id already taken.')
    else:
        if reservation_id in reservations:
            raise NonRecoverableError('reservation_id already taken.')

    reservation = free_resources.pop(0)

    ctx.instance.runtime_properties[FREE_RESOURCES_LIST_PROPERTY] = \
        free_resources

    reservations[reservation_id] = reservation
    ctx.instance.runtime_properties[RESERVATIONS_PROPERTY] = \
        reservations

    ctx.instance.update()

    ctx.logger.debug('Reservation successful: {0}\
            \nLeft resources: {1}\
            \nReservations: {2}'.format(
        reservation,
        ctx.instance.runtime_properties.get(
            FREE_RESOURCES_LIST_PROPERTY),
        ctx.instance.runtime_properties.get(
            RESERVATIONS_PROPERTY)
    ))


@operation(resumable=True)
def return_list_item(ctx, **kwargs):
    ctx.logger.debug('Operation kwargs: {}'.format(kwargs))
    if ctx.type == RELATIONSHIP_INSTANCE and \
            ctx.target.node.type == SHARED_RESOURCE_TYPE:
        _return_shared_list_item(ctx)
    elif ctx.type == RELATIONSHIP_INSTANCE:
        _return_list_item_rel(ctx)
    elif ctx.type == NODE_INSTANCE and \
            ctx.node.type == "cloudify.nodes.resources.List":
        _return_list_item(ctx, reservation_id=kwargs.get('reservation_id', None))
    else:
        NonRecoverableError("Neither relationship nor operation context.")


def _return_list_item_rel(ctx, **kwargs):
    free_resources = ctx.target.instance.runtime_properties.get(
        FREE_RESOURCES_LIST_PROPERTY, [])
    reservation = ctx.source.instance.runtime_properties.get(
        SINGLE_RESERVATION_PROPERTY, None)
    reservations = ctx.target.instance.runtime_properties.get(
        RESERVATIONS_PROPERTY, None)

    if not reservation or not reservations:
        return ctx.logger.debug('Nothing to do.')

    _refresh_source_and_target_runtime_props(ctx)

    reservations.pop(ctx.source.instance.id)
    ctx.target.instance.runtime_properties[RESERVATIONS_PROPERTY] = \
        reservations

    free_resources.append(reservation)
    ctx.target.instance.runtime_properties[FREE_RESOURCES_LIST_PROPERTY] = \
        free_resources

    ctx.source.instance.runtime_properties[SINGLE_RESERVATION_PROPERTY] = ''

    _update_source_and_target_runtime_props(ctx)

    ctx.logger.debug('{0} has been returned back successfully to the resources list.\
        \nLeft resources: {1}'.format(
            reservation,
            ctx.target.instance.runtime_properties.get(
                FREE_RESOURCES_LIST_PROPERTY, [])
        ))


def _return_shared_list_item(ctx, **kwargs):
    workflow_id = 'execute_operation'
    reserve_params = {
        'operation': 'cloudify.interfaces.operations.return',
        'allow_kwargs_override': True,
        'operation_kwargs': {
            'reservation_id': ctx.source.instance.id
        }
    }
    execute_workflow(workflow_id, reserve_params)
    ctx.logger.debug('{0} has been returned back successfully to the resources list.'.format(
            ctx.source.instance.runtime_properties.get(SINGLE_RESERVATION_PROPERTY)
        ))
    ctx.source.instance.runtime_properties[SINGLE_RESERVATION_PROPERTY] = ''


def _return_list_item(ctx, **kwargs):
    reservation_id = kwargs.get('reservation_id')

    free_resources = ctx.instance.runtime_properties.get(
        FREE_RESOURCES_LIST_PROPERTY, [])
    reservations = ctx.instance.runtime_properties.get(
        RESERVATIONS_PROPERTY, None)
    reservation = reservations.get(reservation_id)

    if not reservation or not reservations:
        return ctx.logger.debug('Nothing to do.')

    ctx.instance.refresh()

    reservations.pop(reservation_id)
    ctx.instance.runtime_properties[RESERVATIONS_PROPERTY] = \
        reservations

    free_resources.append(reservation)
    ctx.instance.runtime_properties[FREE_RESOURCES_LIST_PROPERTY] = \
        free_resources

    ctx.instance.update()

    ctx.logger.debug('{0} has been returned back successfully to the resources list.\
        \nLeft resources: {1}'.format(
            reservation,
            ctx.instance.runtime_properties.get(
                FREE_RESOURCES_LIST_PROPERTY, [])
        ))
