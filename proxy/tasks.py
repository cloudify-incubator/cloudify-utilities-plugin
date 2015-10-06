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

import sys
import time


# ctx is imported and used in operations
from cloudify import ctx
from cloudify import exceptions
from cloudify import manager

from cloudify.decorators import operation


@operation
def create_validation(**kwargs):
    client = manager.get_rest_client()
    deployment_id = ctx.node.properties['deployment_id']
    if not deployment_id or deployment_id == '':
        raise exceptions.NonRecoverableError(
            "Deployment ID is not specified.")
    try:
        client.deployments.get(deployment_id)
    except Exception as ex:
        ctx.logger.error("Error during obtaining deployment {0}. "
                         "Reason: {1}."
                         .format(deployment_id, str(ex)))


@operation
def wait_for_deployment(**kwargs):

    if 'deployment_id' not in ctx.node.properties:
        raise exceptions.NonRecoverableError(
            "Deployment ID not specified.")

    client = manager.get_rest_client()
    timeout = ctx.node.properties['timeout']
    deployment_id = ctx.node.properties['deployment_id']

    def _check_if_deployment_is_ready():
        _dep = client.deployments.get(deployment_id)
        ctx.logger.info("Deployment object: {0}.".format(str(_dep)))
        return _dep['status'] != "terminated"

    poll_until(_check_if_deployment_is_ready,
               expected_result=True,
               timeout=timeout)


@operation
def obtain_outputs(**kwargs):

    client = manager.get_rest_client()
    outputs = ctx.node.properties['inherit_outputs']
    deployment_id = ctx.node.properties['deployment_id']

    try:
        deployment_outputs = client.deployments.get(deployment_id).outputs
        for key in outputs:
            ctx.instance.runtime_properties['outputs'].update(
                {key: deployment_outputs.get(key)})
    except Exception as ex:
        ctx.logger.info(
            "Caught exception during obtaining "
            "deployment outputs {0} {1}"
            .format(sys.exc_info()[0], str(ex)))
        raise ex

    raise exceptions.RecoverableError("timed out waiting for deployment")


def poll_until(pollster, expected_result=None, sleep_time=5, timeout=30):
    if not callable(pollster):
        raise Exception("%s is not callable" % pollster.__name__)
    while time.time() <= time.time() + timeout:
        if pollster() != expected_result:
            time.sleep(sleep_time)
    raise exceptions.RecoverableError("Timed out waiting for deployment "
                                      "to reach appropriate state.")
