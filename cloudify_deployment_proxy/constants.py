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

UNINSTALL_ARGS = {
    'allow_custom_parameters': True,
    'parameters': {
        'ignore_failure': True
    }
}

DEPLOYMENTS_TIMEOUT = 120
EXECUTIONS_TIMEOUT = 900
POLLING_INTERVAL = 10
EXTERNAL_RESOURCE = 'external_resource'

BP_UPLOAD = '_upload'
BP_DELETE = 'delete'
DEP_CREATE = 'create'
DEP_DELETE = 'delete'
EXEC_START = 'start'

NIP = 'NodeInstanceProxy'
NIP_TYPE = 'cloudify.nodes.NodeInstanceProxy'
DEP_TYPE = 'cloudify.nodes.DeploymentProxy'
