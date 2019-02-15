########
# Copyright (c) 2014-2018 Cloudify Platform Ltd. All rights reserved
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

import traceback
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError, RecoverableError
from cloudify.decorators import operation

from cloudify_rest_sdk import utility
from cloudify_common_sdk import exceptions
from cloudify_common_sdk.filters import get_field_value_recursive


def _get_params_attributes(ctx, instance, params_list):
    params = {}
    for param_name in params_list:
        params[param_name] = get_field_value_recursive(
            ctx.logger, instance.runtime_properties, params_list[param_name])
    return params


@operation
def bunch_execute(templates=None, **kwargs):
    for template in templates or []:
        params = template.get('params')
        template_file = template.get('template_file')
        prerender = template.get('prerender')
        save_to = template.get('save_to')
        params_attributes = template.get('params_attributes')
        remove_calls = template.get('remove_calls')

        ctx.logger.info('Processing: {template_file}'
                        .format(template_file=repr(template_file)))
        runtime_properties = {}
        if params:
            runtime_properties.update(params)
        if params_attributes:
            runtime_properties.update(
                _get_params_attributes(ctx,
                                       ctx.instance,
                                       params_attributes))
        ctx.logger.debug('Params: {params}'
                         .format(params=repr(runtime_properties)))
        runtime_properties["ctx"] = ctx
        _execute(runtime_properties, template_file, ctx.instance, ctx.node,
                 save_to, prerender=prerender, remove_calls=remove_calls)
    else:
        ctx.logger.debug('No calls.')


@operation
def execute(params=None, template_file=None, save_path=None, prerender=False,
            remove_calls=False, **kwargs):

    params = params or {}
    template_file = template_file or ''

    ctx.logger.debug("Execute params: {} template: {}"
                     .format(repr(params), repr(template_file)))
    runtime_properties = ctx.instance.runtime_properties.copy()
    if not params:
        params = {}
    runtime_properties.update(params)
    _execute(runtime_properties, template_file, ctx.instance, ctx.node,
             save_path=save_path, prerender=prerender,
             remove_calls=remove_calls)


@operation
def execute_as_relationship(params=None, template_file=None, save_path=None,
                            prerender=False, remove_calls=False, **kwargs):
    ctx.logger.debug("Execute as relationship params: {} template: {}"
                     .format(repr(params), repr(template_file)))
    if not params:
        params = {}
    runtime_properties = ctx.target.instance.runtime_properties.copy()
    runtime_properties.update(ctx.source.instance.runtime_properties)
    runtime_properties.update(params)
    _execute(runtime_properties, template_file, ctx.source.instance,
             ctx.source.node, prerender=prerender, remove_calls=remove_calls)


def _execute(params, template_file, instance, node, save_path=None,
             prerender=False, remove_calls=False):
    if not template_file:
        ctx.logger.info('Processing finished. No template file provided.')
        return
    template = ctx.get_resource(template_file)
    try:
        merged_params = {}
        merged_params.update(node.properties.get("params", {}))
        merged_params.update(params)
        result = utility.process(merged_params, template,
                                 node.properties.copy(),
                                 prerender=prerender,
                                 resource_callback=ctx.get_resource)
        if remove_calls and result:
            result = result.get('result_properties', {})
        if save_path:
            instance.runtime_properties[save_path] = result
        else:
            instance.runtime_properties.update(result)
    except exceptions.NonRecoverableResponseException as e:
        raise NonRecoverableError(e)

    except (exceptions.RecoverableResponseException,
            exceptions.RecoverableStatusCodeCodeException,
            exceptions.ExpectationException)as e:
        raise RecoverableError(e)
    except Exception as e:
        ctx.logger.info('Exception traceback : {}'
                        .format(traceback.format_exc()))
        raise NonRecoverableError(e)
