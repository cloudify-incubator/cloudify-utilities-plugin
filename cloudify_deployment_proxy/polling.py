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
from cloudify.exceptions import NonRecoverableError
from cloudify_rest_client.exceptions import CloudifyClientError
from .constants import POLLING_INTERVAL


def any_bp_by_id(_client, _bp_id):
    resource_type = 'blueprints'
    return any_resource_by_id(_client, _bp_id, resource_type)


def any_dep_by_id(_client, _dep_id):
    resource_type = 'deployments'
    return any_resource_by_id(_client, _dep_id, resource_type)


def any_resource_by_id(_client, _resource_id, _resource_type):
    return any(resource_by_id(_client, _resource_id, _resource_type))


def all_deps_by_id(_client, _dep_id):
    resource_type = 'deployments'
    return all_resource_by_id(_client, _dep_id, resource_type)


def all_resource_by_id(_client, _resource_id, _resource_type):
    output = resource_by_id(_client, _resource_id, _resource_type)
    if not output:
        return False
    return all(output)


def resource_by_id(_client, _id, _type):
    _resources_client = getattr(_client, _type)
    try:
        _resources = _resources_client.list(_include=['id'])
    except CloudifyClientError as ex:
        raise NonRecoverableError(
            '{0} list failed {1}.'.format(_type, str(ex)))
    else:
        return [str(_r['id']) == _id for _r in _resources]


def poll_with_timeout(pollster,
                      timeout,
                      interval=POLLING_INTERVAL,
                      pollster_args=None,
                      expected_result=True):

    pollster_args = pollster_args or dict()

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
            if _workflow_id and _exec.get('workflow_id', '') != _workflow_id:
                continue
            elif _exec.get('status') == _state:
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
            'Execution timeout: {0} seconds.'.format(_timeout))
    return True
