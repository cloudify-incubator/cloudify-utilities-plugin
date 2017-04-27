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

from . import get_desired_value
import time

from cloudify import ctx
from cloudify import manager

from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError
from cloudify_rest_client.exceptions import CloudifyClientError

DEPLOYMENTS_TIMEOUT = 120
EXECUTIONS_TIMEOUT = 900
POLLING_INTERVAL = 10
EXT_RES = 'external_resource'

DEFAULT_UNINSTALL_ARGS = {
    'allow_custom_parameters': True,
    'parameters': {
        'ignore_failure': True
    }
}


@operation
def upload_blueprint(**_):

    client = get_desired_value(
        'client', _,
        ctx.instance.runtime_properties,
        ctx.node.properties) or manager.get_rest_client()

    config = get_desired_value(
        'resource_config', _,
        ctx.instance.runtime_properties,
        ctx.node.properties)

    blueprint = config.get('blueprint')
    app_name = blueprint.get('main_file_name')
    bp_archive = blueprint.get('blueprint_archive')
    bp_id = blueprint.get('id') or ctx.instance.id

    if not any_bp_by_id(client, bp_id):
        ctx.instance.runtime_properties[EXT_RES] = False
        try:
            client.blueprints._upload(
                blueprint_id=bp_id,
                archive_location=bp_archive,
                application_file_name=app_name)
        except CloudifyClientError as ex:
            raise NonRecoverableError('Blueprint failed {0}.'.format(str(ex)))

    ctx.instance.runtime_properties['blueprint'] = {}
    ctx.instance.runtime_properties['blueprint']['id'] = bp_id
    ctx.instance.runtime_properties['blueprint']['application_file_name'] = \
        app_name
    ctx.instance.runtime_properties['blueprint']['blueprint_archive'] = \
        bp_archive

    return True


@operation
def create_deployment(**_):

    client = get_desired_value(
        'client', _,
        ctx.instance.runtime_properties,
        ctx.node.properties) or manager.get_rest_client()

    config = get_desired_value(
        'resource_config', _,
        ctx.instance.runtime_properties,
        ctx.node.properties)

    blueprint = config.get('blueprint')
    bp_id = blueprint.get('id') or ctx.instance.id

    deployment = config.get('deployment')
    dep_id = deployment.get('id') or ctx.instance.id
    inputs = deployment.get('inputs')
    outputs = deployment.get('outputs')

    interval = _.get('interval', POLLING_INTERVAL)
    state = _.get('state', 'terminated')
    timeout = _.get('timeout', DEPLOYMENTS_TIMEOUT)
    workflow_id = \
        _.get('workflow_id',
              'create_deployment_environment')

    if not any_dep_by_id(client, dep_id):
        ctx.instance.runtime_properties[EXT_RES] = False
        try:
            client.deployments.create(
                blueprint_id=bp_id,
                deployment_id=dep_id,
                inputs=inputs)
        except CloudifyClientError as ex:
            raise NonRecoverableError(
                'Deployment create failed {0}.'.format(str(ex)))

    ctx.instance.runtime_properties['deployment'] = {}
    ctx.instance.runtime_properties['deployment']['id'] = dep_id

    poll_workflow_after_execute(
        timeout,
        interval,
        client,
        dep_id,
        state,
        workflow_id)

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
            if 'outputs' \
                    not in \
                    ctx.instance.runtime_properties['deployment'].keys():
                ctx.instance.runtime_properties['deployment']['outputs'] = {}
            ctx.instance.runtime_properties['deployment']['outputs'][val] = \
                dep_outputs.get(key, '')

    return True


@operation
def delete_deployment(**_):

    client = get_desired_value(
        'client', _,
        ctx.instance.runtime_properties,
        ctx.node.properties) or manager.get_rest_client()

    config = get_desired_value(
        'resource_config', _,
        ctx.instance.runtime_properties,
        ctx.node.properties)

    deployment = config.get('deployment')
    dep_id = deployment.get('id') or ctx.instance.id

    timeout = _.get('timeout', DEPLOYMENTS_TIMEOUT)

    if not ctx.instance.runtime_properties.get(EXT_RES, True):
        try:
            client.deployments.delete(deployment_id=dep_id)
        except CloudifyClientError as ex:
            raise NonRecoverableError(
                'Deployment delete failed {0}.'.format(str(ex)))
        del ctx.instance.runtime_properties[EXT_RES]

    pollster_args = {
        '_client': client,
        '_dep_id': dep_id
    }

    success = \
        poll_with_timeout(
            all_deps_by_id,
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

    client = get_desired_value(
        'client', _,
        ctx.instance.runtime_properties,
        ctx.node.properties) or manager.get_rest_client()

    config = get_desired_value(
        'resource_config', _,
        ctx.instance.runtime_properties,
        ctx.node.properties)

    deployment = config.get('deployment')
    dep_id = deployment.get('id') or ctx.instance.id

    interval = _.get('interval', POLLING_INTERVAL)
    timeout = _.get('timeout', DEPLOYMENTS_TIMEOUT)

    workflow_id = \
        _.get(
            'workflow_id',
            'create_deployment_environment')
    workflow_state = \
        _.get(
            'workflow_state',
            'terminated')

    if workflow_id == 'uninstall':
        uninstall_reexecute = False
        _args = DEFAULT_UNINSTALL_ARGS
    else:
        uninstall_reexecute = True
        _args = {}
    execution_args = _.get('executions_start_args', _args)

    external_resource = \
        ctx.instance.runtime_properties.get(
            EXT_RES, True)
    reexecute = \
        _.get('reexecute') \
        or ctx.instance.runtime_properties.get('reexecute') \
        or uninstall_reexecute

    def _execute_and_poll():

        try:
            client.executions.start(
                deployment_id=dep_id,
                workflow_id=workflow_id,
                **execution_args)
        except CloudifyClientError as ex:
            raise NonRecoverableError(
                'Executions start failed {0}.'.format(str(ex)))

        return poll_workflow_after_execute(
            timeout,
            interval,
            client,
            dep_id,
            workflow_state,
            workflow_id)

    ctx.instance.runtime_properties['executions'] = {}
    ctx.instance.runtime_properties['executions']['workflow_id'] = \
        workflow_id

    if not external_resource or \
            (reexecute and poll_workflow_after_execute(
                timeout,
                interval,
                client,
                dep_id,
                workflow_state,
                workflow_id)):

        return _execute_and_poll()

    ctx.logger.debug(
        'Not running execute because this is an external_resource.')

    return True


def poll_with_timeout(pollster,
                      timeout,
                      interval=POLLING_INTERVAL,
                      pollster_args={},
                      expected_result=True):

    current_time = time.time()

    while time.time() <= current_time + timeout:
        if pollster(**pollster_args) != expected_result:
            ctx.logger.debug('Polling...')
            time.sleep(interval)
        else:
            ctx.logger.debug('Polling succeeded!')
            return True

    ctx.logger.error('Polling timed out!')
    return False


def any_bp_by_id(_client, _dep_id):
    resource_type = 'blueprints'
    return any_resource_by_id(_client, _dep_id, resource_type)


def any_dep_by_id(_client, _dep_id):
    resource_type = 'deployments'
    return any_resource_by_id(_client, _dep_id, resource_type)


def any_resource_by_id(_client, _resource_id, _resource_type):
    return any(resource_by_id(_client, _resource_id, _resource_type))


def all_deps_by_id(_client, _dep_id):
    resource_type = 'deployments'
    return all_resource_by_id(_client, _dep_id, resource_type)


def all_resource_by_id(_client, _resource_id, _resource_type):
    return all(resource_by_id(_client, _resource_id, _resource_type))


def resource_by_id(_client, _id, _type):
    _resources_client = getattr(_client, _type)
    try:
        _resources = _resources_client.list(_include=['id'])
    except CloudifyClientError as ex:
        raise NonRecoverableError(
            '{0} list failed {1}.'.format(_type, str(ex)))
    else:
        return [str(_r['id']) == _id for _r in _resources]


# Todo: Add ability to filter by execution ID.
def dep_workflow_in_state_pollster(_client,
                                   _dep_id,
                                   _state,
                                   _workflow_id=None):

    exec_list_fields = \
        ['status', 'workflow_id', 'created_at', 'id']

    try:
        _execs = \
            _client.executions.list(deployment_id=_dep_id,
                                    _include=exec_list_fields)
    except CloudifyClientError as ex:
        raise NonRecoverableError(
            'Executions list failed {0}.'.format(str(ex)))
    else:
        for _exec in _execs:
            if _exec.get('status') == _state:
                if _workflow_id and not \
                        _exec.get('workflow_id') == \
                        _workflow_id:
                    continue
                return True
    return False


def poll_workflow_after_execute(_timeout,
                                _interval,
                                _client,
                                _dep_id,
                                _state,
                                _workflow_id):

    pollster_args = {
        '_client': _client,
        '_dep_id': _dep_id,
        '_state': _state,
        '_workflow_id': _workflow_id
    }

    ctx.logger.debug('Polling: {0}'.format(pollster_args))

    success = \
        poll_with_timeout(
            dep_workflow_in_state_pollster,
            timeout=_timeout,
            interval=_interval,
            pollster_args=pollster_args)

    if not success:
        raise NonRecoverableError(
            'Execution not finished. Timeout: {0} seconds.'.format(_timeout))
    return True
