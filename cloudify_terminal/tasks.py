# Copyright (c) 2016-2019 Cloudify Platform Ltd. All rights reserved
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

import time
import logging

from cloudify import context
from cloudify.decorators import workflow
from cloudify import exceptions as cfy_exc
from cloudify import ctx as CloudifyContext

from cloudify_common_sdk.filters import (obfuscate_passwords,
                                         shorted_text,
                                         render_template, )
from cloudify_common_sdk._compat import text_type
import cloudify_terminal_sdk.terminal_connection as terminal_connection

from . import rerun, operation_cleanup, workflow_get_resource


def _execute(ctx, properties, runtime_properties, get_resource, host_ip,
             log_stamp, kwargs):
    # register logger file
    logger_file = kwargs.get('logger_file')
    if logger_file:
        fh = logging.FileHandler(logger_file)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"))
        ctx.logger.addHandler(fh)

    # get current calls
    calls = kwargs.get('calls', [])
    if not calls:
        ctx.logger.info("No calls")
        return

    # credentials
    terminal_auth = properties.get('terminal_auth', {})
    terminal_auth.update(kwargs.get('terminal_auth', {}))
    ip_list = terminal_auth.get('ip')

    # if node contained in some other node, try to overwrite ip
    if not ip_list and host_ip:
        ip_list = [host_ip]
        ctx.logger.info("Used host from container: {ip_list}"
                        .format(ip_list=repr(ip_list)))

    if isinstance(ip_list, text_type):
        ip_list = [ip_list]
    user = terminal_auth.get('user')
    password = terminal_auth.get('password')
    key_content = terminal_auth.get('key_content')
    port = terminal_auth.get('port', 22)

    if not ip_list or not user:
        raise cfy_exc.NonRecoverableError(
            "please check your credentials, ip or user not set"
        )

    # additional settings
    global_promt_check = terminal_auth.get('promt_check')
    global_warning_examples = terminal_auth.get('warnings', [])
    global_error_examples = terminal_auth.get('errors', [])
    global_critical_examples = terminal_auth.get('criticals', [])
    global_responses = terminal_auth.get('responses', [])
    exit_command = terminal_auth.get('exit_command', 'exit')
    smart_device = terminal_auth.get('smart_device')

    # save logs to debug file
    log_file_name = None
    if terminal_auth.get('store_logs'):
        log_file_name = "/tmp/terminal-{log_stamp}.log".format(
            log_stamp=log_stamp)
        ctx.logger.info(
            "Communication logs will be saved to %s" % log_file_name
        )

    if smart_device:
        ctx.logger.info("Used ssh shell extension.")
        connection = terminal_connection.SmartConnection(
            logger=ctx.logger, log_file_name=log_file_name)
    else:
        ctx.logger.info("Used raw stream connection.")
        connection = terminal_connection.RawConnection(
            logger=ctx.logger, log_file_name=log_file_name)

    for ip in ip_list:
        try:
            prompt = connection.connect(ip, user, password, key_content, port,
                                        prompt_check=global_promt_check,
                                        responses=global_responses)
            ctx.logger.info("Will be used: " + ip)
            break

        except Exception as ex:
            ctx.logger.info("Can't connect to:{} with exception:{} and type:{}"
                            .format(repr(ip), str(ex), str(type(ex))))
    else:
        raise cfy_exc.OperationRetry(message="Let's try one more time?")

    ctx.logger.info(
        "Device prompt: {prompt}".format(prompt=shorted_text(prompt)))

    for call in calls:
        responses = call.get('responses', global_responses)
        promt_check = call.get('promt_check', global_promt_check)
        error_examples = call.get('errors', global_error_examples)
        warning_examples = call.get('warnings', global_warning_examples)
        critical_examples = call.get('criticals', global_critical_examples)
        # use action if exist
        operation = call.get('action', "")
        # use template if have
        if not operation and 'template' in call:
            template_name = call.get('template')
            template_params = call.get('params')
            template = get_resource(template_name)
            if not template:
                ctx.logger.info("Empty template.")
                continue
            if not template_params:
                template_params = {}
            # save context for reuse in template
            template_params['ctx'] = ctx
            operation = render_template(template, template_params)

        # incase of template_text
        if not operation and 'template_text' in call:
            template_params = call.get('params')
            template = call.get('template_text')
            if not template:
                ctx.logger.info("Empty template_text.")
                continue
            if not template_params:
                template_params = {}
            # save context for reuse in template
            template_params['ctx'] = ctx
            operation = render_template(template, template_params)

        if not operation:
            continue

        if responses:
            ctx.logger.info("We have predefined responses: {responses}"
                            .format(responses=shorted_text(responses)))

        ctx.logger.debug("Template: \n{operation}".format(
            operation=shorted_text(obfuscate_passwords(operation))))

        result = ""
        for op_line in operation.split("\n"):
            # skip empty lines
            if not op_line.strip():
                continue

            ctx.logger.info("Executing template...")
            ctx.logger.debug("Execute: {opline}".format(
                opline=shorted_text(obfuscate_passwords(op_line))))

            result_part = rerun(
                ctx=ctx,
                func=connection.run,
                args=[],
                kwargs={
                    "command": op_line,
                    "prompt_check": promt_check,
                    "error_examples": error_examples,
                    "warning_examples": warning_examples,
                    "critical_examples": critical_examples,
                    "responses": responses
                },
                retry_count=call.get('retry_count', 10),
                retry_sleep=call.get('retry_sleep', 15))

            if result_part.strip():
                ctx.logger.info(shorted_text(result_part))

            result += (result_part + "\n")
        # save results to runtime properties
        save_to = call.get('save_to')
        if save_to:
            ctx.logger.info("For save: {result}"
                            .format(result=shorted_text(result)))
            runtime_properties[save_to] = result.strip()

    while not connection.is_closed() and exit_command:
        ctx.logger.info("Execute close")
        result = rerun(
            ctx=ctx,
            func=connection.run,
            args=[],
            kwargs={
                "command": exit_command,
                "prompt_check": promt_check,
                "warning_examples": global_warning_examples,
                "error_examples": global_error_examples,
                "critical_examples": global_error_examples
            })
        ctx.logger.info("Result of close: {result}"
                        .format(result=shorted_text(result)))
        time.sleep(1)

    connection.close()


@operation_cleanup
def run(*args, **kwargs):
    """main entry point for all calls"""
    # get current context
    ctx = kwargs.get('ctx', CloudifyContext)

    if ctx.type == context.NODE_INSTANCE:
        # Node instance
        properties = ctx.node.properties
        runtime_properties = ctx.instance.runtime_properties

        # get ip from parent
        try:
            host_ip = ctx.instance.host_ip
        except cfy_exc.NonRecoverableError:
            host_ip = None

        log_stamp = "{execution_id}_{instance_id}_{workflow_id}".format(
            execution_id=ctx.execution_id,
            instance_id=ctx.instance.id,
            workflow_id=ctx.workflow_id
        )

    elif ctx.type == context.RELATIONSHIP_INSTANCE:
        # Realationships context
        properties = ctx.target.node.properties
        runtime_properties = ctx.target.instance.runtime_properties

        # get ip from parent
        try:
            host_ip = ctx.target.instance.host_ip
        except cfy_exc.NonRecoverableError:
            host_ip = None

        log_stamp = "{execution_id}_{instance_id}_{workflow_id}".format(
            execution_id=ctx.execution_id,
            instance_id=ctx.target.instance.id,
            workflow_id=ctx.workflow_id
        )

    _execute(
        ctx=ctx,
        properties=properties,
        runtime_properties=runtime_properties,
        get_resource=ctx.get_resource,
        host_ip=host_ip,
        log_stamp=log_stamp,
        kwargs=kwargs
    )


# callback name from hooks config
@workflow
def run_as_workflow(*args, **kwargs):
    # get current context
    ctx = kwargs.get('ctx', CloudifyContext)
    if ctx.type != context.DEPLOYMENT:
        raise cfy_exc.NonRecoverableError(
            "Called with wrong context: {ctx_type}".format(
                ctx_type=ctx.type
            )
        )

    # check inputs
    if len(args):
        inputs = args[0]
    else:
        inputs = kwargs.get('inputs', {})

    properties = kwargs.get('properties', {})

    _execute(
        ctx=ctx,
        properties=properties,
        runtime_properties={'__inputs__': inputs},
        get_resource=workflow_get_resource,
        host_ip=None,
        log_stamp="{execution_id}_{workflow_id}".format(
            execution_id=inputs.get("execution_id", 'noexecution'),
            workflow_id=inputs.get("workflow_id", 'noworkflow')
        ),
        kwargs=kwargs
    )
