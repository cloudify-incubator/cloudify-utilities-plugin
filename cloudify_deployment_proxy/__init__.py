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

from cloudify import ctx
from cloudify import manager
from cloudify.exceptions import NonRecoverableError
from cloudify_rest_client.exceptions import CloudifyClientError

from .constants import (
    UNINSTALL_ARGS,
    DEPLOYMENTS_TIMEOUT,
    EXECUTIONS_TIMEOUT,
    POLLING_INTERVAL,
    EXTERNAL_RESOURCE,
    BP_UPLOAD,
    DEP_CREATE,
    DEP_DELETE,
    EXEC_START,
    NIP,
    NIP_TYPE,
    DEP_TYPE
)
from .polling import (
    any_bp_by_id,
    any_dep_by_id,
    poll_with_timeout,
    poll_workflow_after_execute,
)
from .utils import get_desired_value, update_attributes


class DeploymentProxyBase:

    def __init__(self,
                 operation_inputs):
        """
        Sets the properties that all operations need.
        :param operation_inputs: The inputs from the operation.
        """

        full_operation_name = ctx.operation.name
        self.operation_name = full_operation_name.split('.').pop()

        self.client = get_desired_value(
            'client', operation_inputs,
            ctx.instance.runtime_properties,
            ctx.node.properties) or manager.get_rest_client()

        self.config = get_desired_value(
            'resource_config', operation_inputs,
            ctx.instance.runtime_properties,
            ctx.node.properties)

        self.external_resource = \
            ctx.instance.runtime_properties.get(
                EXTERNAL_RESOURCE, True)

        # Blueprint-related properties
        self.blueprint = self.config.get('blueprint')
        self.blueprint_id = self.blueprint.get('id') or ctx.instance.id
        self.blueprint_file_name = self.blueprint.get('main_file_name')
        self.blueprint_archive = self.blueprint.get('blueprint_archive')

        # Deployment-related properties
        self.deployment = self.config.get('deployment')
        self.deployment_id = self.deployment.get('id') or ctx.instance.id
        self.deployment_inputs = self.deployment.get('inputs')
        self.deployment_outputs = self.deployment.get('outputs')

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
        self.timeout = \
            operation_inputs.get(
                'timeout',
                EXECUTIONS_TIMEOUT if 'execute_start' else DEPLOYMENTS_TIMEOUT)

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

        client_args = \
            dict(blueprint_id=self.blueprint_id,
                 archive_location=self.blueprint_archive,
                 application_file_name=self.blueprint_file_name)

        if 'blueprint' not in ctx.instance.runtime_properties.keys():
            ctx.instance.runtime_properties['blueprint'] = dict()

        update_attributes('blueprint', 'id', self.blueprint_id)
        update_attributes(
            'blueprint', 'blueprint_archive', self.blueprint_archive)
        update_attributes(
            'blueprint', 'application_file_name', self.blueprint_file_name)

        if any_bp_by_id(self.client, self.blueprint_id):
            return False

        ctx.instance.runtime_properties[EXTERNAL_RESOURCE] = False
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
            return False

        ctx.instance.runtime_properties[EXTERNAL_RESOURCE] = False
        self.dp_get_client_response('deployments', DEP_CREATE, client_args)

        return self.verify_execution_successful()

    def delete_deployment(self):

        client_args = dict(deployment_id=self.deployment_id)

        if not ctx.instance.runtime_properties.get(EXTERNAL_RESOURCE, True):
            self.dp_get_client_response('deployments', DEP_DELETE, client_args)

        pollster_args = \
            dict(_client=self.client,
                 _dep_id=self.deployment_id)

        del ctx.instance.runtime_properties['deployment']

        return poll_with_timeout(
            any_dep_by_id,
            timeout=self.timeout,
            pollster_args=pollster_args,
            expected_result=False)

    def execute_workflow(self):

        if 'executions' not in ctx.instance.runtime_properties.keys():
            ctx.instance.runtime_properties['executions'] = dict()

        update_attributes('executions', 'workflow_id', self.workflow_id)

        # Wait for the deployment to
        if self.external_resource \
                and not (self.reexecute and
                         self.verify_execution_successful()):
            return ctx.operation.retry(
                'The deployment is not ready for execution.')

        execution_args = \
            self.config.get(
                'executions_start_args',
                UNINSTALL_ARGS if self.workflow_id == 'uninstall' else {}
            )
        client_args = \
            dict(deployment_id=self.deployment_id,
                 workflow_id=self.workflow_id,
                 **execution_args)
        self.dp_get_client_response('executions', EXEC_START, client_args)

        # Poll for execution success.
        if not self.verify_execution_successful():
            ctx.logger.error('Deployment error.')

        if NIP_TYPE == ctx.node.type:
            return self.post_execute_node_instance_proxy()
        elif DEP_TYPE == ctx.node.type:
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

        if 'outputs' \
                not in ctx.instance.runtime_properties['deployment'].keys():
            update_attributes('deployment', 'outputs', dict())

        try:
            response = self.client.deployments.outputs.get(self.deployment_id)
        except CloudifyClientError as ex:
            ctx.logger.error(
                'Failed to query deployment outputs: {0}'.format(str(ex)))
        else:
            dep_outputs = response.get('outputs')
            ctx.logger.debug('Deployment outputs: {0}'.format(dep_outputs))
            for key, val in self.deployment_outputs.items():
                update_attributes(
                    'deployment',
                    'outputs.' + val,
                    dep_outputs.get(key, ''))
        return True

    def verify_execution_successful(self):
        return poll_workflow_after_execute(
            self.timeout,
            self.interval,
            self.client,
            self.deployment_id,
            self.workflow_state,
            self.workflow_id)
