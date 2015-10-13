# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
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

import time

from cloudify import ctx
from cloudify import exceptions
from cloudify import manager


def poll_until_with_timeout(pollster, expected_result=None,
                            sleep_time=5, timeout=30):
    if not callable(pollster):
        raise exceptions.NonRecoverableError(
            "%s is not callable" % pollster.__name__)
    while time.time() <= time.time() + timeout:
        if pollster() != expected_result:
            time.sleep(sleep_time)
        else:
            return True
    raise exceptions.NonRecoverableError("Timed out waiting for deployment "
                                         "to reach appropriate state.")


def check_if_deployment_is_ready(client, deployment_id):

    def _pollster():
        _execs = client.executions.list(deployment_id=deployment_id)
        ctx.logger.info("Deployment execution objects: {0}."
                        .format(str(_execs)))
        return any([_e['status'] == 'terminated' for _e in _execs])

    return _pollster


def poll_until(pollster, expected_result=None, sleep_time=5):
    if not callable(pollster):
        raise exceptions.NonRecoverableError(
            "%s is not callable" % pollster.__name__)
    while pollster() != expected_result:
        time.sleep(sleep_time)
    raise exceptions.NonRecoverableError(
        "Timed out waiting for deployment "
        "to reach appropriate state.")


def execute_workflow(deployment_id, workflow_id):
    ctx.logger.info("Entering execute_workflow event.")
    try:
        client = manager.get_rest_client()
        client.executions.start(deployment_id,
                                workflow_id)
        ctx.logger.info("Workflow {0} started.".format(
            workflow_id))
        poll_until_with_timeout(
            check_if_deployment_is_ready(
                client, deployment_id),
            expected_result=True,
            timeout=900)
    except Exception as ex:
        ctx.logger.error("Error during deployment uninstall {0}. "
                         "Reason: {1}."
                         .format(deployment_id, str(ex)))
        raise exceptions.NonRecoverableError(
            "Error during deployment uninstall {0}. "
            "Reason: {1}.".format(deployment_id, str(ex)))
    ctx.logger.info("Exiting execute_workflow event.")
