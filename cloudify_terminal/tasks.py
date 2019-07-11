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
from cloudify_common_sdk import filters
import time

from cloudify import ctx
from cloudify import exceptions as cfy_exc
from cloudify.decorators import operation

import cloudify_terminal_sdk.terminal_connection as terminal_connection
from cloudify_common_sdk import exceptions


def _rerun(ctx, func, args, kwargs, retry_count=10, retry_sleep=15):
    retry_count = 10
    while retry_count > 0:
        try:
            return func(*args, **kwargs)
        except exceptions.RecoverableWarning as e:
            ctx.logger.info("Need for rerun: {e}".format(e=repr(e)))
            retry_count -= 1
            time.sleep(retry_sleep)
        except exceptions.RecoverableError as e:
            raise cfy_exc.RecoverableError(str(e))
        except exceptions.NonRecoverableError as e:
            raise cfy_exc.NonRecoverableError(str(e))

    raise cfy_exc.RecoverableError(
        "Failed to rerun: {args}:{kwargs}"
        .format(args=repr(args), kwargs=repr(kwargs)))


@operation(resumable=True)
def run(**kwargs):
    """main entry point for all calls"""

    calls = kwargs.get('calls', [])
    if not calls:
        ctx.logger.info("No calls")
        return

    try:
        ctx_properties = ctx.node.properties
        ctx_instance = ctx.instance
    except cfy_exc.NonRecoverableError:
        # Realationships context?
        ctx_properties = ctx.target.node.properties
        ctx_instance = ctx.target.instance

    # credentials
    properties = ctx_properties
    terminal_auth = properties.get('terminal_auth', {})
    terminal_auth.update(kwargs.get('terminal_auth', {}))
    ip_list = terminal_auth.get('ip')

    # if node contained in some other node, try to overwrite ip
    if not ip_list:
        ip_list = [ctx_instance.host_ip]
        ctx.logger.info("Used host from container: {ip_list}"
                        .format(ip_list=repr(ip_list)))

    if isinstance(ip_list, basestring):
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
    exit_command = terminal_auth.get('exit_command', 'exit')
    smart_device = terminal_auth.get('smart_device')
    # save logs to debug file
    log_file_name = None
    if terminal_auth.get('store_logs'):
        log_file_name = "/tmp/terminal-%s_%s_%s.log" % (
            str(ctx.execution_id), str(ctx_instance.id), str(ctx.workflow_id)
        )
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
                                        global_promt_check)
            ctx.logger.info("Will be used: " + ip)
            break

        except Exception as ex:
            ctx.logger.info("Can't connect to:{} with exception:{} and type:{}"
                            .format(repr(ip), str(ex), str(type(ex))))
    else:
        raise cfy_exc.OperationRetry(message="Let's try one more time?")

    ctx.logger.info("Device prompt: {prompt}"
                    .format(prompt=filters.shorted_text(prompt)))

    for call in calls:
        responses = call.get('responses', [])
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
            template = ctx.get_resource(template_name)
            if not template:
                ctx.logger.info("Empty template.")
                continue
            if not template_params:
                template_params = {}
            # save context for reuse in template
            template_params['ctx'] = ctx
            operation = filters.render_template(template, template_params)

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
            operation = filters.render_template(template, template_params)

        if not operation:
            continue

        if responses:
            ctx.logger.info("We have predefined responses: {responses}"
                            .format(responses=filters.shorted_text(responses)))

        ctx.logger.debug("Template: \n{operation}"
                         .format(operation=filters.shorted_text(operation)))

        result = ""
        for op_line in operation.split("\n"):
            # skip empty lines
            if not op_line.strip():
                continue

            ctx.logger.info("Executing template...")
            ctx.logger.debug("Execute: {opline}"
                             .format(opline=filters.shorted_text(op_line)))

            result_part = _rerun(
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
                ctx.logger.info(filters.shorted_text(result_part))

            result += (result_part + "\n")
        # save results to runtime properties
        save_to = call.get('save_to')
        if save_to:
            ctx.logger.info("For save: {result}"
                            .format(result=filters.shorted_text(result)))
            ctx_instance.runtime_properties[save_to] = result.strip()

    while not connection.is_closed() and exit_command:
        ctx.logger.info("Execute close")
        result = _rerun(
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
                        .format(result=filters.shorted_text(result)))
        time.sleep(1)

    connection.close()
