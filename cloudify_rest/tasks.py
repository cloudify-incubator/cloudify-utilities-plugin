########
# Copyright (c) 2014-2020 Cloudify Platform Ltd. All rights reserved
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
import logging
import traceback

from cloudify import ctx as CloudifyContext
from cloudify.exceptions import NonRecoverableError, RecoverableError
from cloudify.decorators import workflow

from cloudify_rest_sdk import utility
from cloudify_common_sdk.filters import get_field_value_recursive

from cloudify_terminal import operation_cleanup, rerun


def _get_params_attributes(ctx, runtime_properties, params_list):
    params = {}
    for param_name in params_list:
        params[param_name] = get_field_value_recursive(
            ctx.logger, runtime_properties, params_list[param_name])
    return params


@operation_cleanup
def bunch_execute(templates=None, **kwargs):
    # get current context
    ctx = kwargs.get('ctx', CloudifyContext)
    auth = kwargs.get('auth')

    for template in templates or []:
        params = template.get('params', {})
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
                                       ctx.instance.runtime_properties,
                                       params_attributes))
        ctx.logger.debug('Params: {params}'
                         .format(params=repr(runtime_properties)))
        runtime_properties["ctx"] = ctx
        _execute(params=runtime_properties, template_file=template_file,
                 ctx=ctx, instance_props=ctx.instance.runtime_properties,
                 node_props=ctx.node.properties, save_path=save_to,
                 prerender=prerender, remove_calls=remove_calls, auth=auth,
                 resource_callback=ctx.get_resource,
                 retry_count=kwargs.get('retry_count', 1),
                 retry_sleep=kwargs.get('retry_sleep', 15))
    else:
        ctx.logger.debug('No calls.')


@operation_cleanup
def execute(*argc, **kwargs):
    # get current context
    ctx = kwargs.get('ctx', CloudifyContext)
    auth = kwargs.get('auth')
    params = kwargs.get('params', {})
    template_file = kwargs.get('template_file')
    save_path = kwargs.get('save_path')
    prerender = kwargs.get('prerender', False)
    remove_calls = kwargs.get('remove_calls', False)
    if not params:
        params = {}

    ctx.logger.debug("Execute params: {} template: {}"
                     .format(repr(params), repr(template_file)))
    runtime_properties = ctx.instance.runtime_properties.copy()

    runtime_properties.update(params)
    _execute(params=runtime_properties, template_file=template_file, ctx=ctx,
             instance_props=ctx.instance.runtime_properties,
             node_props=ctx.node.properties, save_path=save_path,
             prerender=prerender, remove_calls=remove_calls, auth=auth,
             resource_callback=ctx.get_resource,
             retry_count=kwargs.get('retry_count', 1),
             retry_sleep=kwargs.get('retry_sleep', 15))


@operation_cleanup
def execute_as_relationship(*argc, **kwargs):
    # get current context
    ctx = kwargs.get('ctx', CloudifyContext)
    auth = kwargs.get('auth')
    params = kwargs.get('params', {})
    template_file = kwargs.get('template_file')
    save_path = kwargs.get('save_path')
    prerender = kwargs.get('prerender', False)
    remove_calls = kwargs.get('remove_calls', False)
    if not params:
        params = {}

    ctx.logger.debug("Execute as relationship params: {} template: {}"
                     .format(repr(params), repr(template_file)))

    runtime_properties = ctx.target.instance.runtime_properties.copy()
    runtime_properties.update(ctx.source.instance.runtime_properties)
    runtime_properties.update(params)
    _execute(params=runtime_properties, template_file=template_file, ctx=ctx,
             instance_props=ctx.source.instance.runtime_properties,
             node_props=ctx.source.node.properties, save_path=save_path,
             prerender=prerender, remove_calls=remove_calls, auth=auth,
             resource_callback=ctx.get_resource,
             retry_count=kwargs.get('retry_count', 1),
             retry_sleep=kwargs.get('retry_sleep', 15))


def _workflow_get_resource(file_name):
    try:
        with open(file_name, 'r') as f:
            return f.read()
    except IOError as ex:
        raise NonRecoverableError(
            'Failed to open: {file_name}: {ex}'
            .format(file_name=file_name, ex=repr(ex)))


# callback name from hooks config
@workflow
def execute_as_workflow(*args, **kwargs):
    # get current context
    ctx = kwargs.get('ctx', CloudifyContext)

    # register logger file
    logger_file = kwargs.get('logger_file')
    if logger_file:
        fh = logging.FileHandler(logger_file)
        fh.setLevel(logging.DEBUG)
        ctx.logger.addHandler(fh)

    # check inputs
    if len(args):
        inputs = args[0]
    else:
        inputs = kwargs.get('inputs', {})

    # copy resource ids back
    for field in [
        'blueprint_id', 'deployment_id', 'tenant_name', 'rest_token'
    ]:
        if not ctx._context.get(field):
            if not inputs.get(field):
                ctx.logger.error("Partially provided inputs: {inputs}"
                                 .format(inputs=inputs))
                return
            ctx._context[field] = inputs[field]

    auth = kwargs.get('auth')
    params = kwargs.get('params', {})
    node_props = kwargs.get('properties', {})
    template_file = kwargs.get('template_file')
    save_path = kwargs.get('save_path')
    prerender = kwargs.get('prerender', False)
    remove_calls = kwargs.get('remove_calls', False)
    if not params:
        params = {}

    ctx.logger.debug("Execute as workflows params: {} template: {}"
                     .format(repr(params), repr(template_file)))

    params['__inputs__'] = inputs

    # place for save responses
    runtime_properties = {}

    _execute(params=params, template_file=template_file,
             ctx=ctx, instance_props=runtime_properties,
             node_props=node_props, save_path=save_path, prerender=prerender,
             remove_calls=remove_calls, auth=auth,
             resource_callback=_workflow_get_resource,
             retry_count=kwargs.get('retry_count', 1),
             retry_sleep=kwargs.get('retry_sleep', 15))
    ctx.logger.debug("Final response: {runtime}"
                     .format(runtime=repr(runtime_properties)))


def _execute_in_retry(template, params, instance_props, node_props,
                      resource_callback=None, save_path=None,
                      prerender=False, remove_calls=False, auth=None):
    merged_params = {}
    merged_params.update(node_props.get("params", {}))
    merged_params.update(params)
    merged_auth = node_props.copy()
    # we have something additional to node properties for merge
    if auth:
        merged_auth.update(auth)
    result = utility.process(merged_params, template,
                             merged_auth,
                             prerender=prerender,
                             resource_callback=resource_callback)
    if remove_calls and result:
        result = result.get('result_properties', {})
    if save_path:
        instance_props[save_path] = result
    else:
        instance_props.update(result)


def _execute(params, template_file, retry_count, retry_sleep, ctx, **kwargs):
    if not template_file:
        ctx.logger.info('Processing finished. No template file provided.')
        return
    template = kwargs['resource_callback'](template_file)
    try:
        kwargs['params'] = params
        kwargs['template'] = template
        rerun(ctx=ctx, func=_execute_in_retry, args=[], kwargs=kwargs,
              retry_count=retry_count, retry_sleep=retry_sleep)
    except (NonRecoverableError,
            RecoverableError) as e:
        ctx.logger.debug("Raised: {e}".format(e=e))
        raise e
    except Exception as e:
        ctx.logger.info('Exception traceback : {}'
                        .format(traceback.format_exc()))
        raise NonRecoverableError(e)
