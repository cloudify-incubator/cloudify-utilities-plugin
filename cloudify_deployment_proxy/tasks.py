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
        if pollster(**pollster_args) != expected_result:
            ctx.logger.debug('Still polling.')
            time.sleep(interval)
        else:
            ctx.logger.info('Polling succeeded.')
            return True

    ctx.logger.error('Polling failed.')
    return False


def get_instance_attribute_from_relationship(relationships,
                                             instance_attribute):
    relationship_type = 'cloudify.relationships.depends_on'
    node_instance = \
        get_instance_from_relationship_type(relationships,
                                            relationship_type)
    return node_instance.instance.runtime_properties.get(
        instance_attribute)


def get_instance_from_relationship_type(relationships, type):
    for relationship in relationships:
        if type in relationship.type_hierarchy:
            return relationship.target
    return None


def all_dep_workflows_in_state_pollster(_client,
                                        _dep_id,
                                        _state):
    _execs = _client.executions.list(deployment_id=_dep_id)
    return all([str(_e['status']) == _state for _e in _execs])


# Todo: Add ability to filter by execution ID.
def dep_workflow_in_state_pollster(_client,
                                   _dep_id,
                                   _state,
                                   _workflow_id,
                                   _created_at):

    exec_list_fields = \
        ['status', 'workflow_id', 'created_at', 'id']

    _execs = \
        _client.executions.list(deployment_id=_dep_id,
                                _include=exec_list_fields)

    for _exec in _execs:
        if _exec.get('workflow_id') == _workflow_id and \
                _exec.get('status') == _state:
            return True
    return False


def all_deps_pollster(_client, _dep_id):
    _deps = _client.deployments.list(_include=['id'])
    return all([str(_d['id']) == _dep_id for _d in _deps])


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

    ctx.logger.debug('Polling: {0}'.format(pollster_args))

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

    if not dep_id:
        deployment = get_instance_attribute_from_relationship(
            ctx.instance.relationships,
            'deployment')
        if not deployment:
            return ctx.operation.retry('Deployment not ready.')
        dep_id = deployment.get('id')

    ctx.instance.runtime_properties['deployment_id'] = dep_id

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
    dep_id = _.get('id') or \
        ctx.instance.runtime_properties.get('deployment_id') or \
        config.get('deployment_id')

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

    return True


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
    timeout = _.get('timeout', 20)

    try:
        dp_create_response = \
            client.deployments.create(blueprint_id=bp_id,
                                      deployment_id=dep_id,
                                      inputs=inputs)
    except CloudifyClientError as ex:
        raise NonRecoverableError(
            'Deployment create failed {0}.'.format(str(ex)))

    ctx.logger.info('output: {0}'.format(dp_create_response))

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


@operation
def delete_deployment(**_):

    dep_id_prop = ctx.instance.runtime_properties['deployment'].get('id')

    client = _.get('client') or manager.get_rest_client()
    config = _.get('resource_config') or \
        ctx.node.properties.get('resource_config')

    dep_id = _.get('deployment_id') or \
        config.get('deployment_id', dep_id_prop)
    timeout = _.get('timeout', 15)

    try:
        client.deployments.delete(deployment_id=dep_id)
    except CloudifyClientError as ex:
        raise NonRecoverableError(
            'Deployment delete failed {0}.'.format(str(ex)))

    pollster_args = {
        '_client': client,
        '_dep_id': dep_id
    }

    success = \
        poll_with_timeout(
            all_deps_pollster,
            timeout=timeout,
            pollster_args=pollster_args,
            expected_result=False)

    if not success:
        raise NonRecoverableError(
            'Deployment not deleted. Timeout: {0} seconds.'.format(timeout))

    del ctx.instance.runtime_properties['deployment']

    return True


@operation
def execute_start(**_):
    client = _.get('client') or manager.get_rest_client()
    config = _.get('resource_config') or \
        ctx.node.properties.get('resource_config')
    dep_id = _.get('deployment_id') or \
        config.get('deployment_id',
                   ctx.instance.runtime_properties['deployment']['id'])
    workflow_id = _.get('workflow_id')
    execution_args = _.get('executions_start_args', dict())
    timeout = _.get('timeout', 60)
    workflow_state = _.get('workflow_state', 'terminated')

    try:
        ex_start_response = \
            client.executions.start(deployment_id=dep_id,
                                    workflow_id=workflow_id,
                                    **execution_args)
    except CloudifyClientError as ex:
        raise NonRecoverableError(
            'Executions start failed {0}.'.format(str(ex)))

    ctx.logger.info('output: {0}'.format(ex_start_response))

    ctx.instance.runtime_properties['executions'] = {}
    ctx.instance.runtime_properties['executions']['workflow_id'] = \
        ex_start_response.get('workflow_id')
    ctx.instance.runtime_properties['executions']['created_at'] = \
        ex_start_response.get('created_at')

    dep_created_at = ctx.instance.runtime_properties.get('deployment',
                                                         {}).get('created_at')

    pollster_args = {
        '_client': client,
        '_dep_id': dep_id,
        '_state': workflow_state,
        '_workflow_id': workflow_id,
        '_created_at': dep_created_at
    }

    success = \
        poll_with_timeout(
            dep_workflow_in_state_pollster,
            timeout=timeout,
            pollster_args=pollster_args)

    if not success:
        raise NonRecoverableError(
            'Execution not finished. Timeout: {0} seconds.'.format(timeout))
    return True
