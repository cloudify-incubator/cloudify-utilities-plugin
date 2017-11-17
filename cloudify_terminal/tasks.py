# Copyright (c) 2016-2017 GigaSpaces Technologies Ltd. All rights reserved
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
from cloudify import ctx
from cloudify import exceptions as cfy_exc
from cloudify.decorators import operation
from jinja2 import Template

import terminal_connection


@operation
def run(**kwargs):
    """main entry point for all calls"""

    calls = kwargs.get('calls', [])
    if not calls:
        ctx.logger.info("No calls")
        return

    # credentials
    properties = ctx.node.properties
    terminal_auth = properties.get('terminal_auth', {})
    terminal_auth.update(kwargs.get('terminal_auth', {}))
    ip_list = terminal_auth.get('ip', [ctx.instance.host_ip])
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
    global_error_examples = terminal_auth.get('errors')
    exit_command = terminal_auth.get('exit_command', 'exit')
    # save logs to debug file
    log_file_name = None
    if terminal_auth.get('store_logs'):
        log_file_name = "/tmp/terminal-%s_%s_%s.log" % (
            str(ctx.execution_id), str(ctx.instance.id), str(ctx.workflow_id)
        )
        ctx.logger.info(
            "Communication logs will be saved to %s" % log_file_name
        )

    connection = terminal_connection.connection()

    for ip in ip_list:
        try:
            prompt = connection.connect(ip, user, password, key_content, port,
                                        global_promt_check, logger=ctx.logger,
                                        log_file_name=log_file_name)
            ctx.logger.info("Will be used: " + ip)
            break
        except Exception as ex:
            ctx.logger.info("Can't connect to %s with %s" % (
                repr(ip), str(ex)
            ))
    else:
        raise cfy_exc.NonRecoverableError(
            "please check your ip list"
        )

    ctx.logger.info("Device prompt: " + prompt)

    for call in calls:
        responses = call.get('responses', [])
        promt_check = call.get('promt_check', global_promt_check)
        error_examples = call.get('errors', global_error_examples)
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
            template_engine = Template(template)
            if not template_params:
                template_params = {}
            # save context for reuse in template
            template_params['ctx'] = ctx
            operation = template_engine.render(template_params)

        # incase of template_text
        if not operation and 'template_text' in call:
            template_params = call.get('params')
            template = call.get('template_text')
            if not template:
                ctx.logger.info("Empty template_text.")
                continue
            template_engine = Template(template)
            if not template_params:
                template_params = {}
            # save context for reuse in template
            template_params['ctx'] = ctx
            operation = template_engine.render(template_params)

        if not operation:
            continue

        if responses:
            ctx.logger.info("We have predefined responses: " + str(responses))

        ctx.logger.info("Template: \n" + str(operation))

        result = ""
        for op_line in operation.split("\n"):
            # skip empty lines
            if not op_line.strip():
                continue

            ctx.logger.info("Execute: " + op_line)
            result_part = connection.run(op_line, promt_check,
                                         error_examples, responses)

            if result_part.strip():
                ctx.logger.info(result_part.strip())

            result += (result_part + "\n")
        # save results to runtime properties
        save_to = call.get('save_to')
        if save_to:
            ctx.logger.info("For save: " + result.strip())
            ctx.instance.runtime_properties[save_to] = result.strip()

    while not connection.is_closed() and exit_command:
        ctx.logger.info("Execute close")
        result = connection.run(exit_command, promt_check, error_examples)
        ctx.logger.info("Result of close: " + result)

    connection.close()
