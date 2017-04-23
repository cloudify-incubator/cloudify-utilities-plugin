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

import time
from datetime import datetime

from cloudify import ctx
from cloudify import manager

from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError
from cloudify_rest_client.exceptions import CloudifyClientError


def poll_with_timeout(pollster,
                      timeout,
                      interval=5,
                      pollster_args={},
                      expected_result=True):

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
        ctx.logger.debug('Polling client...')
        if pollster(**pollster_args) != expected_result:
            ctx.logger.debug('Still polling.')
            time.sleep(interval)
        else:
            ctx.logger.info('Polling succeeded.')
            return True

    ctx.logger.error('Polling failed.')
    return False


def chop_datetime(_date):
    return _date.split('.')[0]


def timestamp_diff(expected, actual):
    T_FORMAT = "%Y-%m-%dT%H:%M:%S"

    expected_timestamp = \
        datetime.strptime(chop_datetime(expected),
                          T_FORMAT)
    actual_timestamp = \
        datetime.strptime(chop_datetime(actual),
                          T_FORMAT)
    timestamp_diff = actual_timestamp-expected_timestamp
    return (timestamp_diff).total_seconds()


def all_dep_workflows_in_state_pollster(_client,
                                        _dep_id,
                                        _state):
    _execs = _client.executions.list(deployment_id=_dep_id)
    return all([str(_e['status']) == _state for _e in _execs])


def dep_workflow_in_state_pollster(_client,
                                   _dep_id,
                                   _state,
                                   _workflow_id,
                                   _created_at):

    exec_list_fields = \
        ['status', 'workflow_id', 'created_at']

    _execs = \
        _client.executions.list(deployment_id=_dep_id,
                                _include=exec_list_fields)

    for _exec in _execs:
        ctx.logger.info('Exec: {0}'.format(_exec))
        if _exec.get('workflow_id') == _workflow_id and \
                _exec.get('status') == _state and \
                timestamp_diff(_created_at,
                               _exec.get('created_at')) <= 1:
            return True
    return False


def poll_workflow_after_execute(_timeout,
                                _client,
                                _dep_id,
                                _state,
                                _workflow_id,
                                _created_at):

    pollster_args = {
        '_client': _client,
        '_dep_id': _dep_id,
        '_state': _state,
        '_workflow_id': _workflow_id,
        '_created_at': _created_at
    }

    ctx.logger.info('Polling: {0}'.format(pollster_args))

    success = \
        poll_with_timeout(
            dep_workflow_in_state_pollster,
            timeout=_timeout,
            pollster_args=pollster_args)

    if not success:
        raise NonRecoverableError(
            'Deployment not ready. Timeout: {0} seconds.'.format(_timeout))
    return True


@operation
def wait_for_deployment_ready(state, timeout, **_):

    client = _.get('client') or manager.get_rest_client()
    config = _.get('resource_config') or \
        ctx.node.properties.get('resource_config')
    dep_id = _.get('id') or config.get('deployment_id')

    ctx.logger.info(
        'Waiting for all workflows in '
        'deployment {0} '
        'to be in state {1}.'
        .format(dep_id,
                state))

    pollster_args = {
        '_client': client,
        '_dep_id': dep_id,
        '_state': state
    }
    success = \
        poll_with_timeout(
            all_dep_workflows_in_state_pollster,
            timeout=timeout,
            pollster_args=pollster_args)
    if not success:
        raise NonRecoverableError(
            'Deployment not ready. Timeout: {0} seconds.'.format(timeout))
    return True


@operation
def query_deployment_data(daemonize,
                          interval,
                          timeout,
                          **_):

    if daemonize:
        raise NonRecoverableError(
            'Option "daemonize" is not implemented.')

    client = _.get('client') or manager.get_rest_client()
    config = _.get('resource_config') or \
        ctx.node.properties.get('resource_config')
    dep_id = _.get('id') or config.get('deployment_id')
    outputs = config.get('outputs')

    ctx.logger.debug(
        'Deployment {0} output mapping: {1}'.format(dep_id, outputs))

    try:
        dep_outputs_response = client.deployments.outputs.get(dep_id)
    except CloudifyClientError as ex:
        ctx.logger.error(
            'Ignoring: Failed to query deployment outputs: {0}'
            .format(str(ex)))
    else:
        dep_outputs = dep_outputs_response.get('outputs')

        ctx.logger.debug(
            'Received these deployment outputs: {0}'.format(dep_outputs))
        for key, val in outputs.items():
            ctx.instance.runtime_properties[val] = dep_outputs.get(key, '')
    return True


@operation
def upload_blueprint(**_):
    client = _.get('client') or manager.get_rest_client()
    config = _.get('resource_config') or \
        ctx.node.properties.get('resource_config')

    app_name = _.get('application_file_name') or \
        config.get('application_file_name')
    bp_archive = _.get('blueprint_archive') or \
        config.get('blueprint_archive')
    bp_id = _.get('blueprint_id') or \
        config.get('blueprint_id', ctx.instance.id)

    try:
        bp_upload_response = \
            client.blueprints._upload(blueprint_id=bp_id,
                                      archive_location=bp_archive,
                                      application_file_name=app_name)
    except CloudifyClientError as ex:
        raise NonRecoverableError('Blueprint failed {0}.'.format(str(ex)))

    ctx.instance.runtime_properties['blueprint'] = {}
    ctx.instance.runtime_properties['blueprint']['id'] = \
        bp_upload_response.get('id')


@operation
def create_deployment(**_):

    client = _.get('client') or manager.get_rest_client()
    config = _.get('resource_config') or \
        ctx.node.properties.get('resource_config')

    blueprint = _.get('blueprint') or \
        ctx.instance.runtime_properties.get('blueprint')
    bp_id = _.get('blueprint_id') or \
        blueprint.get('id') or config.get('blueprint_id')
    dep_id = _.get('deployment_id') or \
        config.get('deployment_id', bp_id)
    inputs = _.get('inputs') or config.get('inputs', {})
    timeout = _.get('timeout', 30)

    try:
        dp_create_response = \
            client.deployments.create(blueprint_id=bp_id,
                                      deployment_id=dep_id,
                                      inputs=inputs)
    except CloudifyClientError as ex:
        raise NonRecoverableError(
            'Deployment create failed {0}.'.format(str(ex)))

    dep_created_at = dp_create_response.get('created_at')

    ctx.instance.runtime_properties['deployment'] = {}
    ctx.instance.runtime_properties['deployment']['id'] = \
        dp_create_response.get('id')
    ctx.instance.runtime_properties['deployment']['created_at'] = \
        dep_created_at

    return poll_workflow_after_execute(timeout,
                                       client,
                                       dep_id,
                                       'terminated',
                                       'create_deployment_environment',
                                       dep_created_at)


# @operation
# def execute_install(**_):
#     client = _.get('client') or manager.get_rest_client()
#     config = _.get('resource_config') or \
#         ctx.node.properties.get('resource_config')
#     dep_id = _.get('deployment_id') or \
#         config.get('deployment_id',
#                    ctx.instance.runtime_properties['deployment']['id'])
#     workflow_id = _.get('workflow_id')
#     execution_args = _.get('executions_start_args')
#     timeout = _.get('timeout', 180)

#     try:
#         ex_start_response = \
#                 client.executions.start(deployment_id=dep_id,
#                                         workflow_id=workflow_id,
#                                         **execution_args)
#     except CloudifyClientError as ex:
#         raise NonRecoverableError(
#             'Executions start failed {0}.'.format(str(ex)))

#     ctx.logger.info('Output: {0}'.format(ex_start_response))

#     ctx.instance.runtime_properties['executions'] = {}
#     ctx.instance.runtime_properties['executions']['workflow_id'] = \
#         ex_start_response.get('id')
#     ctx.instance.runtime_properties['executions']['created_at'] = \
#         ex_start_response.get('created_at')

#     dep_created_at = ctx.instance.runtime_properties.get('deployment',
#                                                          {}).get('created_at')

#     pollster_args = {
#         '_client': client,
#         '_dep_id': dep_id,
#         '_state': 'terminated',
#         '_workflow_id': 'install',
#         '_created_at': dep_created_at
#     }

#     success = \
#         poll_with_timeout(
#             dep_workflow_in_state_pollster,
#             timeout=timeout,
#             pollster_args=pollster_args)

#     if not success:
#         raise NonRecoverableError(
#             'Deployment not ready. Timeout: {0} seconds.'.format(timeout))
#     return True
