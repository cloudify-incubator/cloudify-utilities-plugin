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

from cloudify_rest_client.exceptions import CloudifyClientError
from mock import MagicMock
import datetime

# Node Templates

blueprint_deployment_properties = {
    'resource_config': {
        'blueprint_archive': 'URL'
    }
}

deployment_proxy_properties = {
    'resource_config': {
        'blueprint': {
            'id': '',
            'blueprint_archive': 'URL',
            'main_file_name': 'blueprint.yaml'
        },
        'deployment': {
            'id': '',
            'inputs': {},
            'outputs': {
                'output1': 'output2'
            }
        }
    }
}


def return_list(*args, **kwargs):
    list_mock = {
        'id': MagicMock,
        'workflow_id': MagicMock,
        'workflow_state': MagicMock
    }
    return [list_mock]


def return_object(*args, **kwargs):
    return MagicMock


def return_none_object(*args, **kwargs):
    return None


def return_dict_object(*args, **kwargs):
    return {}


BLUEPRINTS_MOCK = MagicMock
BLUEPRINTS_LIST = return_list
BLUEPRINTS_GET = return_none_object
BLUEPRINTS_UPLOAD = MagicMock(return_value={'id': 'test'})

DEPLOYMENTS_MOCK = MagicMock
DEPLOYMENTS_OUTPUTS = MagicMock
DEPLOYMENTS_OUTPUTS_GET = MagicMock(return_value={'outputs': {}})
DEPLOYMENTS_LIST = return_list
DEPLOYMENTS_DELETE = MagicMock(return_value=True)
DEPLOYMENTS_CREATE = MagicMock(return_value={
    'id': 'test',
    'created_at': datetime.datetime.now()
})
DEPLOYMENTS_CREATE = MagicMock(return_value={
    'id': 'test',
    'created_at': datetime.datetime.now()
})
EXECUTIONS_MOCK = MagicMock
EXECUTIONS_LIST = return_list
EXECUTIONS_CREATE = MagicMock(return_value={
    'workflow_id': 'install'})

# Exceptions
REST_CLIENT_EXCEPTION = MagicMock(side_effect=CloudifyClientError('Mistake'))
