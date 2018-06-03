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
from urlparse import urlparse

from cloudify import ctx
from cloudify import manager
from cloudify.exceptions import NonRecoverableError
from cloudify_rest_client.client import CloudifyClient
from cloudify_rest_client.exceptions import CloudifyClientError

from .constants import (
    UNINSTALL_ARGS,
    EXECUTIONS_TIMEOUT,
    POLLING_INTERVAL,
    EXTERNAL_RESOURCE,
    BP_UPLOAD,
    BP_DELETE,
    DEP_CREATE,
    DEP_DELETE,
    EXEC_START,
    EXEC_LIST,
    NIP,
    NIP_TYPE,
    DEP_TYPE,
)
from .polling import (
    any_bp_by_id,
    any_dep_by_id,
    poll_with_timeout,
    poll_workflow_after_execute,
    dep_system_workflows_finished
)
from .utils import get_desired_value, update_attributes


class DeploymentProxyBase(object):

    def __init__(self,
                 operation_inputs):
        """
        Sets the properties that all operations need.
        :param operation_inputs: The inputs from the operation.
        """

        full_operation_name = ctx.operation.name
        self.operation_name = full_operation_name.split('.').pop()

        self.client_config = get_desired_value(
            'client', operation_inputs,
            ctx.instance.runtime_properties,
            ctx.node.properties
        )

        if self.client_config:
            self.client = CloudifyClient(**self.client_config)
        else:
            self.client = manager.get_rest_client()

        self.config = get_desired_value(
            'resource_config', operation_inputs,
            ctx.instance.runtime_properties,
            ctx.node.properties)

        # Blueprint-related properties
        self.blueprint = self.config.get('blueprint', {})
        self.blueprint_id = self.blueprint.get('id') or ctx.instance.id
        self.blueprint_file_name = self.blueprint.get('main_file_name')
        self.blueprint_archive = self.blueprint.get('blueprint_archive')

        # Deployment-related properties
        self.deployment = self.config.get('deployment', {})
        self.deployment_id = self.deployment.get('id') or ctx.instance.id
        self.deployment_inputs = self.deployment.get('inputs', {})
        self.deployment_outputs = self.deployment.get('outputs', {})
        self.deployment_logs = self.deployment.get('logs', {})

        # Node-instance-related properties
        self.node_instance_proxy = self.config.get('node_instance')

        # Execution-related properties
        self.workflow_id = \
            operation_inputs.get('workflow_id',
                                 'create_deployment_environment')
        self.workflow_state = \
            operation_inputs.get(
                'workflow_state',
                'terminated')
        self.reexecute = \
            self.config.get('reexecute') \
            or ctx.instance.runtime_properties.get('reexecute') \
            or False

        # Polling-related properties
        self.interval = operation_inputs.get('interval', POLLING_INTERVAL)
        self.state = operation_inputs.get('state', 'terminated')
        self.timeout = operation_inputs.get('timeout', EXECUTIONS_TIMEOUT)

        # This ``execution_id`` will be set once execute workflow done
        # successfully
        self.execution_id = None

    def dp_get_client_response(self,
                               _client,
                               _client_attr,
                               _client_args):

        _generic_client = \
            getattr(self.client, _client)

        _special_client = \
            getattr(_generic_client, _client_attr)

        try:
            response = _special_client(**_client_args)
        except CloudifyClientError as ex:
            raise NonRecoverableError(
                'Client action {0} failed: {1}.'.format(_client_attr, str(ex)))
        else:
            return response

    def upload_blueprint(self):

        if 'blueprint' not in ctx.instance.runtime_properties.keys():
            ctx.instance.runtime_properties['blueprint'] = dict()

        update_attributes('blueprint', 'id', self.blueprint_id)
        update_attributes(
            'blueprint', 'blueprint_archive', self.blueprint_archive)
        update_attributes(
            'blueprint', 'application_file_name', self.blueprint_file_name)

        if self.blueprint.get(EXTERNAL_RESOURCE):
            ctx.logger.info("Used external blueprint.")
            return False

        # Parse the blueprint_archive in order to get url parts
        parse_url = urlparse(self.blueprint_archive)

        # Check if the ``blueprint_archive`` is not a URL then we need to
        # download it and pass the binaries to the client_args
        if not(parse_url.netloc and parse_url.scheme):
            self.blueprint_archive = \
                ctx.download_resource(self.blueprint_archive)

        client_args = \
            dict(blueprint_id=self.blueprint_id,
                 archive_location=self.blueprint_archive,
                 application_file_name=self.blueprint_file_name)

        if any_bp_by_id(self.client, self.blueprint_id):
            ctx.logger.info("Blueprint {0} already exists."
                            .format(self.blueprint_id))
            return False

        return self.dp_get_client_response('blueprints',
                                           BP_UPLOAD,
                                           client_args)

    def create_deployment(self):

        client_args = \
            dict(blueprint_id=self.blueprint_id,
                 deployment_id=self.deployment_id,
                 inputs=self.deployment_inputs)

        if 'deployment' not in ctx.instance.runtime_properties.keys():
            ctx.instance.runtime_properties['deployment'] = dict()

        update_attributes('deployment', 'id', self.deployment_id)

        if any_dep_by_id(self.client, self.deployment_id):
            ctx.logger.info("Deployment {0} already exists."
                            .format(self.deployment_id))
            return False

        if not self.deployment.get(EXTERNAL_RESOURCE):
            ctx.logger.info("Create deployment {0}."
                            .format(self.deployment_id))
            self.dp_get_client_response('deployments', DEP_CREATE, client_args)

        # In order to set the ``self.execution_id`` need to get the
        # ``execution_id`` of current deployment ``self.deployment_id``

        # Prepare executions list fields
        exec_list_fields = \
            ['status', 'workflow_id', 'created_at', 'id', 'deployment_id']

        # Call list executions for the current deployment
        _execs = self.dp_get_client_response(
            'executions', EXEC_LIST,
            {
                'deployment_id': self.deployment_id,
                '_include': exec_list_fields
            }
        )

        # Retrieve the ``execution_id`` associated with the current deployment
        for _exec in _execs:
            if _exec.get('workflow_id') == 'create_deployment_environment':
                self.execution_id = _exec.get('id')
                ctx.logger.info("Found execution_id {0} for deployment_id {1}"
                                .format(_exec.get('id'), self.deployment_id))
                break

        # If the ``execution_id`` cannot be found raise error
        if not self.execution_id:
            raise NonRecoverableError(
                'No execution id Found for deployment'
                ' {0}'.format(self.deployment_id)
            )

        return self.verify_execution_successful()

    def delete_deployment(self):

        client_args = dict(deployment_id=self.deployment_id)

        poll_result = True

        if not self.deployment.get(EXTERNAL_RESOURCE):

            ctx.logger.info("Wait for stop deployment related executions.")

            pollster_args = \
                dict(_client=self.client,
                     _check_all_in_deployment=self.deployment_id)

            poll_with_timeout(
                dep_system_workflows_finished,
                timeout=self.timeout,
                pollster_args=pollster_args,
                expected_result=True)

            ctx.logger.info("Delete deployment {0}".format(self.deployment_id))
            self.dp_get_client_response('deployments', DEP_DELETE, client_args)

            ctx.logger.info("Wait for deployment delete.")

            pollster_args = \
                dict(_client=self.client,
                     _dep_id=self.deployment_id)

            poll_result = poll_with_timeout(
                any_dep_by_id,
                timeout=self.timeout,
                pollster_args=pollster_args,
                expected_result=False)

            del ctx.instance.runtime_properties['deployment']

        ctx.logger.info("Little wait internal cleanup services.")

        time.sleep(POLLING_INTERVAL)

        ctx.logger.info("Wait for stop all system workflows.")

        pollster_args = \
            dict(_client=self.client)

        poll_with_timeout(
            dep_system_workflows_finished,
            timeout=self.timeout,
            pollster_args=pollster_args,
            expected_result=True)

        if not self.blueprint.get(EXTERNAL_RESOURCE):
            ctx.logger.info("Delete blueprint {0}."
                            .format(self.blueprint_id))
            client_args = dict(blueprint_id=self.blueprint_id)
            self.dp_get_client_response('blueprints', BP_DELETE, client_args)

        return poll_result

    def execute_workflow(self):

        if 'executions' not in ctx.instance.runtime_properties.keys():
            ctx.instance.runtime_properties['executions'] = dict()

        update_attributes('executions', 'workflow_id', self.workflow_id)

        # Wait for the deployment to finish any executions
        pollster_args = \
            dict(_client=self.client,
                 _check_all_in_deployment=self.deployment_id)

        if not poll_with_timeout(dep_system_workflows_finished,
                                 timeout=self.timeout,
                                 pollster_args=pollster_args,
                                 expected_result=True):
            return ctx.operation.retry(
                'The deployment is not ready for execution.')

        # we must to run some execution
        if (
            self.deployment.get(EXTERNAL_RESOURCE) and self.reexecute
        ) or not self.deployment.get(EXTERNAL_RESOURCE):

            execution_args = \
                self.config.get(
                    'executions_start_args',
                    UNINSTALL_ARGS if self.workflow_id == 'uninstall' else {}
                )
            client_args = \
                dict(deployment_id=self.deployment_id,
                     workflow_id=self.workflow_id,
                     **execution_args)
            response = self.dp_get_client_response('executions',
                                                   EXEC_START, client_args)

            # Set the execution_id for the last execution process created
            self.execution_id = response['id']
            ctx.logger.debug('Executions start response: {0}'.format(response))

            # Poll for execution success.
            if not self.verify_execution_successful():
                ctx.logger.error('Deployment error.')

            ctx.logger.debug('Polling execution succeeded')

        if NIP_TYPE == ctx.node.type:
            ctx.logger.debug('Start post execute node proxy')
            return self.post_execute_node_instance_proxy()
        elif DEP_TYPE == ctx.node.type:
            ctx.logger.debug('Start post execute deployment proxy')
            return self.post_execute_deployment_proxy()
        return False

    def post_execute_node_instance_proxy(self):

        node_instance_id = self.node_instance_proxy.get('id')
        node_instance_proxy = \
            ctx.instance.runtime_properties.get(NIP, dict())
        client_args = \
            dict(deployment_id=self.deployment_id,
                 node_id=self.node_instance_proxy.get('node', {}).get('id'))
        node_instances = \
            self.dp_get_client_response('node_instances', 'list', client_args)
        ctx.logger.debug(
            'Received these node instances: {0}'.format(node_instances))
        for node_instance in node_instances:
            if node_instance_id and \
                    node_instance_id != node_instance.get('id'):
                continue
            node_instance_proxy[node_instance.get('id')] = \
                node_instance.get('runtime_properties')
        ctx.instance.runtime_properties[NIP] = node_instance_proxy
        return True

    def post_execute_deployment_proxy(self):
        runtime_prop = ctx.instance.runtime_properties['deployment']
        ctx.logger.debug(
            'Runtime  deployment properties {0}'.format(runtime_prop))

        if 'outputs' \
                not in ctx.instance.runtime_properties['deployment'].keys():
            update_attributes('deployment', 'outputs', dict())
            ctx.logger.debug('No deployment proxy outputs exist.')

        try:
            ctx.logger.debug('Deployment Id is {0}'.format(self.deployment_id))

            response = self.client.deployments.outputs.get(self.deployment_id)

            ctx.logger.debug(
                'Deployment outputs response {0}'.format(response))

        except CloudifyClientError as ex:
            ctx.logger.error(
                'Failed to query deployment outputs: {0}'.format(str(ex)))
        else:
            dep_outputs = response.get('outputs')
            ctx.logger.debug('Deployment outputs: {0}'.format(dep_outputs))
            for key, val in self.deployment_outputs.items():
                ctx.instance.runtime_properties[
                    'deployment']['outputs'][val] = \
                    dep_outputs.get(key, '')
        return True

    def verify_execution_successful(self):
        return poll_workflow_after_execute(
            self.timeout,
            self.interval,
            self.client,
            self.deployment_id,
            self.workflow_state,
            self.workflow_id,
            self.execution_id,
            _log_redirect=self.deployment_logs.get('redirect', True))
