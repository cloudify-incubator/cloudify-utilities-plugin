########
# Copyright (c) 2020 Cloudify Platform Ltd. All rights reserved
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

from cloudify import ctx as CloudifyContext
from cloudify import manager
from cloudify_rest_client.client import CloudifyClient
from cloudify.decorators import workflow

from cloudify_common_sdk.filters import get_field_value_recursive


def _check_filter(ctx, filter_by, inputs):
    if isinstance(filter_by, list):
        for field_desc in filter_by:
            # check type of field_desc
            if not isinstance(field_desc, dict):
                ctx.logger.error(
                    "Event skiped by wrong field description.")
                return False

            # check path
            field_path = field_desc.get('path')
            if not field_path:
                ctx.logger.error("Event skiped by undefined key.")
                return False

            # posible values
            field_values = field_desc.get('values')
            if not field_values:
                ctx.logger.error("Event skiped by undefined values.")
                return False

            # check that we have such values in properties
            value = get_field_value_recursive(
                ctx.logger, inputs, field_path)

            # skip events if not in subset
            if value not in field_values:
                ctx.logger.error(
                    "Event with {value} skiped by {key}:{values} rule."
                    .format(
                        value=repr(value), key=repr(field_path),
                        values=repr(field_values)))
                return False
    else:
        ctx.logger.error(
            "Filter skiped by incorrect type of rules list.")
        return False

    # everything looks good
    return True


# callback name from hooks config
@workflow
def run_workflow(*args, **kwargs):
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

    # dump current parameters
    ctx.logger.debug(
        "Workflow run called with {inputs} and args '{args}' and kwargs:"
        " {kwargs}".format(inputs=repr(inputs), args=repr(args),
                           kwargs=repr(kwargs)))

    # check deployment id, strange if empty but lets check
    deployment_id = inputs.get('deployment_id')
    if not deployment_id:
        ctx.logger.error("Deployment id is undefined")
        return

    # get workflow name
    workflow_name = kwargs.get('workflow_for_run')
    if not workflow_name:
        ctx.logger.error("Workflow for run is undefined")
        return

    # get workflow params
    workflow_params = kwargs.get('workflow_params', {})

    # get credentials for rest connection to manager, can be used for run
    # workflow with different user/tenant
    client_config = kwargs.get('client_config', {})
    if client_config:
        client = CloudifyClient(**client_config)
    else:
        # get client from current manager
        client = manager.get_rest_client()

    # get deployment information
    deployment = client.deployments.get(deployment_id=deployment_id)
    if not deployment:
        ctx.logger.error("Deployment disappear.")
        return

    # get filter dictionary
    filter_by = kwargs.get('filter_by', [])
    ctx.logger.debug("Filter {filter_by}".format(filter_by=repr(filter_by)))
    if filter_by:
        # get values from deployment information, use _get_
        # for support 5+ managers
        inputs['deployment_inputs'] = deployment.get('inputs', {})
        inputs['deployment_outputs'] = deployment.get('outputs', {})
        inputs['deployment_capabilities'] = deployment.get('capabilities', {})
        if not _check_filter(ctx=ctx, filter_by=filter_by, inputs=inputs):
            ctx.logger.debug(
                "Event skiped by filter.")
            return

    # mark that we going to run to logs
    ctx.logger.info("Going to {workflow_name} on {deployment_id}".format(
        workflow_name=workflow_name,
        deployment_id=deployment_id))

    # send uninstall event
    client.executions.start(deployment_id=deployment_id,
                            workflow_id=workflow_name,
                            **workflow_params)
