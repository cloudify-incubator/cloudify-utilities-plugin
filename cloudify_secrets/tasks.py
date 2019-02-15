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
from cloudify.manager import get_rest_client
from cloudify_secrets.sdk import SecretsSDK

DATA_RUNTIME_PROPERTY = 'data'

DO_NOT_DELETE_PROPERTY = 'do_not_delete'

KEYS_PROPERTY = 'keys'


def _get_parameters(properties, kwargs):
    for k, v in properties.iteritems():
        if k not in kwargs:
            kwargs[k] = v

    return kwargs


@operation
def create(ctx, **kwargs):
    parameters = _get_parameters(ctx.node.properties, kwargs)

    result = SecretsSDK(ctx.logger, get_rest_client(), **parameters).create(
        **parameters
    )

    ctx.instance.runtime_properties[DO_NOT_DELETE_PROPERTY] = parameters.get(
        DO_NOT_DELETE_PROPERTY,
        False
    )
    ctx.instance.runtime_properties[DATA_RUNTIME_PROPERTY] = result


@operation
def update(ctx, **kwargs):
    parameters = _get_parameters(ctx.node.properties, kwargs)

    result = SecretsSDK(ctx.logger, get_rest_client(), **parameters).update(
        **parameters
    )

    ctx.instance.runtime_properties[DO_NOT_DELETE_PROPERTY] = parameters.get(
        DO_NOT_DELETE_PROPERTY,
        False
    )
    ctx.instance.runtime_properties[DATA_RUNTIME_PROPERTY] = result


@operation
def delete(ctx, **kwargs):
    if ctx.instance.runtime_properties.get(DO_NOT_DELETE_PROPERTY, False):
        ctx.logger.info(
            '"do_not_delete" property set to <true> - skipping deletion ...'
        )
    else:
        parameters = _get_parameters(ctx.node.properties, kwargs)
        secrets = ctx.instance.runtime_properties[DATA_RUNTIME_PROPERTY]

        SecretsSDK(ctx.logger, get_rest_client(), **parameters).delete(
            secrets,
            **parameters
        )

    ctx.instance.runtime_properties.pop(DATA_RUNTIME_PROPERTY, None)
    ctx.instance.runtime_properties.pop(DO_NOT_DELETE_PROPERTY, None)


@operation
def read(ctx, **kwargs):
    parameters = _get_parameters(ctx.node.properties, kwargs)

    result = SecretsSDK(ctx.logger, get_rest_client(), **parameters).read(
        **parameters
    )

    ctx.instance.runtime_properties[DATA_RUNTIME_PROPERTY] = result
