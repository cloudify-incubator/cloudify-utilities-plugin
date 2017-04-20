# Copyright (c) 2017 GigaSpaces Technologies Ltd. All rights reserved
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

from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from cloudify import manager

from cloudify.decorators import operation


def poll_with_timeout(pollster,
                      timeout,
                      interval=5,
                      expected_result=None):

    if not callable(pollster):
        raise NonRecoverableError(
            'pollster {0} is not callable'
            .format(pollster))

    ctx.logger.debug(
        'pollster: {0}, '
        'timeout: {1}, '
        'interval: {2}, '
        'expected_result: {3}.'
        .format(pollster.__name__,
                timeout,
                interval,
                expected_result))

    current_time = time.time()

    while time.time() <= current_time + timeout:
        ctx.logger.info('Polling client...')
        if pollster() != expected_result:
            ctx.logger.debug(
                'Still polling.')
            time.sleep(interval)
        else:
            ctx.logger.info(
                'Polling succeeded.')
            return True

    ctx.logger.error('Polling failed.')
    return False


def all_dep_workflows_in_state_pollster(_client, _dep_id, _state):
    _execs = _client.executions.list(deployment_id=_dep_id)
    return all([str(_e['status']) == _state for _e in _execs])


@operation
def wait_for_deployment_ready(state, timeout, **_):

    client = _.get('client') or manager.get_rest_client()
    dep_id = _.get('id') or ctx.node.properties.get('resource_id')

    ctx.logger.info(
        'Waiting for all workflows in '
        'deployment {0} '
        'to be in state {1}.'
        .format(dep_id,
                state))

    success = poll_with_timeout(all_dep_workflows_in_state_pollster(client, dep_id, state), timeout=timeout)
    if not success:
        raise NonRecoverableError(
            'Deployment not ready within specified timeout ({0} seconds).'.format(timeout))


@operation
def inherit_deployment_attributes(deployment_id, **kwargs):
    ctx.logger.info("Entering obtain_outputs event.")
    client = manager.get_rest_client()
    outputs = ctx.node.properties['inherit_outputs']
    ctx.logger.info("Outputs to inherit: {0}."
                    .format(str(outputs)))
    ctx.logger.info('deployment id %s' % deployment_id)
    inherit_inputs = ctx.node.properties['inherit_inputs']
    ctx.instance.runtime_properties.update({
        'inherit_outputs': outputs,
        'deployment_id': deployment_id
    })
    try:
        if inherit_inputs:
            _inputs = client.deployments.get(deployment_id)['inputs']
            ctx.instance.runtime_properties.update(
                {'proxy_deployment_inputs': _inputs})
        deployment_outputs = client.deployments.outputs.get(
            deployment_id)['outputs']
        ctx.logger.info("Available deployment outputs {0}."
                        .format(str(deployment_outputs)))
        ctx.logger.info("Available runtime properties: {0}.".format(
            str(ctx.instance.runtime_properties.keys())
        ))
        for key in outputs:
            ctx.instance.runtime_properties.update(
                {key: deployment_outputs.get(key)}
            )
    except Exception as ex:
        ctx.logger.error(
            "Caught exception during obtaining "
            "deployment outputs {0} {1}"
            .format(sys.exc_info()[0], str(ex)))
        raise exceptions.NonRecoverableError(
            "Caught exception during obtaining "
            "deployment outputs {0} {1}. Available runtime properties {2}"
            .format(sys.exc_info()[0], str(ex),
                    str(ctx.instance.runtime_properties.keys())))
    ctx.logger.info("Exiting obtain_outputs event.")


@operation
def cleanup(**kwargs):
    ctx.logger.info("Entering cleanup_outputs event.")
    outputs = ctx.instance.runtime_properties.get('inherit_outputs', [])
    if ('proxy_deployment_inputs' in
            ctx.instance.runtime_properties):
        del ctx.instance.runtime_properties['proxy_deployment_inputs']
    for key in outputs:
        if key in ctx.instance.runtime_properties:
            del ctx.instance.runtime_properties[key]
    ctx.logger.info("Exiting cleanup_outputs event.")


@operation
def get_outputs(**kwargs):
#  if (ctx.target.node._node.type!='cloudify.nodes.DeploymentProxy'):
#    raise (NonRecoverableError('invalid target: must connect to DeploymentProxy type'))

  for output in ctx.target.node.properties['inherit_outputs']:
    ctx.source.instance.runtime_properties[output]=ctx.target.instance.runtime_properties[output]
