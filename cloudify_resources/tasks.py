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


RESOURCES_LIST_PROPERTY = 'resource_config'
RESERVATIONS_PROPERTY = 'reservations'
SINGLE_RESERVATION_PROPERTY = 'reservation'


@operation(resumable=True)
def create_list(ctx, **kwargs):
    resource_config = ctx.node.properties.get('resource_config', None)

    if not isinstance(resource_config, list):
        raise NonRecoverableError(
            'The "resource_config" property must be of type: list')

    ctx.logger.debug('Initializing resources list...')
    ctx.instance.runtime_properties[RESOURCES_LIST_PROPERTY] = resource_config
    ctx.instance.runtime_properties[RESERVATIONS_PROPERTY] = {}


@operation(resumable=True)
def create_list_item(ctx, **kwargs):
    ctx.logger.debug('Initializing list item...')
    ctx.instance.runtime_properties[SINGLE_RESERVATION_PROPERTY] = {}


@operation(resumable=True)
def reserve_list_item(ctx, **kwargs):
    resources_list = ctx.target.instance.runtime_properties.get(RESOURCES_LIST_PROPERTY, [])
    reservations = ctx.target.instance.runtime_properties.get(RESERVATIONS_PROPERTY, {})

    if len(resources_list) == len(reservations.items()):
        raise NonRecoverableError(
            'Reservation has failed, because there are no available resources right now.')

    for index in reservations.values():
        resources_list.pop(index)

    ctx.source.instance.runtime_properties[SINGLE_RESERVATION_PROPERTY] = resources_list.pop()
    ctx.target.instance.runtime_properties[RESERVATIONS_PROPERTY][ctx.instance.id] = \
        ctx.source.instance.runtime_properties.get(SINGLE_RESERVATION_PROPERTY)
    ctx.logger.debug('Reservation successful: {0}\nLeft resources: {1}'.format(
        ctx.source.instance.runtime_properties.get('reservation'),
        resources_list
    ))


@operation(resumable=True)
def return_list_item(ctx, **kwargs):
    reservation = ctx.source.instance.runtime_properties.get(SINGLE_RESERVATION_PROPERTY, None)
    reservations = ctx.target.instance.runtime_properties.get(RESERVATIONS_PROPERTY, {})

    if not reservation or not reservations:
        return ctx.logger.debug('Nothing to do.')
    
    ctx.target.instance.runtime_properties[RESERVATIONS_PROPERTY] = \
        {k:v for k, v in reservations.items() if v != reservation}

    ctx.logger.debug('{} has been returned back successfully to the resources list.'.format(
        reservation
    ))


    

