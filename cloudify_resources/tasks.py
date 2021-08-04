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

from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError

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


@operation(resumable=True)
def return_list_item(ctx, **kwargs):
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
