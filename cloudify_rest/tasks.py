########
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

import traceback
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError, RecoverableError
from cloudify_rest.rest_sdk import utility, exceptions


def execute(params, template_file, **kwargs):
    ctx.logger.debug(
        'execute_as_relationship params {0} template {1}'.format(
            params, template_file))
    runtime_properties = ctx.instance.runtime_properties.copy()
    if not params:
        params = {}
    runtime_properties.update(params)
    _execute(runtime_properties, template_file, ctx.instance, ctx.node)


def execute_as_relationship(params, template_file, **kwargs):
    ctx.logger.debug(
        'execute_as_relationship params {0} template {1}'.format(
            params, template_file))
    if not params:
        params = {}
    runtime_properties = ctx.target.instance.runtime_properties.copy()
    runtime_properties.update(ctx.source.instance.runtime_properties)
    runtime_properties.update(params)
    _execute(runtime_properties, template_file, ctx.source.instance,
             ctx.source.node)


def _execute(params, template_file, instance, node):
    if not template_file:
        ctx.logger.info(
            'Processing finished. No template file provided.')
        return
    template = ctx.get_resource(template_file)
    try:
        instance.runtime_properties.update(
            utility.process(params, template, node.properties.copy()))
    except (exceptions.ExpectationException,
            exceptions.RecoverebleStatusCodeCodeException)as e:
        raise RecoverableError(e)
    except Exception as e:
        ctx.logger.info(
            'Exception traceback : {}'.format(traceback.format_exc()))
        raise NonRecoverableError(e)
