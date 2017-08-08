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

import os

from cloudify import ctx
from cloudify.exceptions import OperationRetry

from .utils import execute_command, expand_paths


class CloudifyFile(object):

    def __init__(self, operation_inputs):
        """
        Sets the properties that all operations need.
        :param operation_inputs: The inputs from the operation.
        """

        self.config = self.get_config(operation_inputs)
        self.target_path = expand_paths(self.config.get('target_path'))
        self.resource_path = expand_paths(self.config.get('resource_path'))
        self.template_variables = self.config.get('template_variables')
        self.file_content = self.config.get('file_content')
        self.file_permissions = self.config.get('file_permissions')
        self.config_sections = self.config.get('config_sections') or {}


    def chmod(self):
        try:
            command = \
                'chmod {0} {1}'.format(self.file_permissions, self.target_path)
            execute_command(command)
        except OSError:
            command = \
                'sudo chmod {0} {1}'.format(
                    self.file_permissions, self.target_path)
            execute_command(command)

    @staticmethod
    def get_config(inputs):

        config = ctx.node.properties.get('resource_config', {})
        config.update(
            ctx.instance.runtime_properties.get('resource_config', {}))
        config.update(inputs.get('resource_config', {}))

        return config

    def rename(self, from_path):

        try:
            os.rename(from_path, self.target_path)
        except OSError:
            command = 'sudo mv {0} {1}'.format(from_path, self.target_path)
            result = execute_command(command, debug=True)
            if not result:
                raise OperationRetry(
                    'Running `{0}` has non-zero return value.'.format(command))
            ctx.logger.debug(
                'Command: {0}. Result: {1}'.format(command, result))

    def remove(self):

        try:
            os.remove(self.target_path)
        except OSError:
            command = 'sudo rm {0}'.format(self.target_path)
            result = execute_command(command, debug=True)
            if not result:
                raise OperationRetry(
                    'Running `{0}` has non-zero return value.'.format(command))
            ctx.logger.debug(
                'Command: {0}. Result: {1}'.format(command, result))
