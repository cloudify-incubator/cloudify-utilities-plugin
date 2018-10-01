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

import yaml
import base64
import copy
from cloudify import ctx


class CloudInit(object):

    def __init__(self, operation_inputs):
        """
        Sets the properties that all operations need.
        :param operation_inputs: The inputs from the operation.
        """

        self.config = self.get_config(self, operation_inputs)

    def get_external_resource(self, config):
        for f in config.get('write_files', []):
            if not isinstance(f, dict):
                break
            try:
                resource_type = f['content'].get('resource_type', '')
                resource_name = f['content'].get('resource_name', '')
                template_variables = f['content'].get('template_variables', {})
                if 'file_resource' == resource_type:
                    f['content'] = ctx.get_resource_and_render(resource_name, template_variables)
            except ValueError:
                ctx.logger.debug('No external resource recognized.')
                pass
        return config

    @staticmethod
    def get_config(self, inputs):

        config = ctx.node.properties.get('resource_config', {})
        config.update(
            ctx.instance.runtime_properties.get('resource_config', {}))
        config.update(inputs.get('resource_config', {}))
        config.update(self.get_external_resource(config.copy()))

        return config

    @property
    def __str__(self):
        """Override the string implementation of object."""

        cloud_init = yaml.dump(self.config)
        cloud_init_string = str(cloud_init).replace('!!python/unicode ', '')
        header = ctx.node.properties.get('header')
        if header:
            cloud_init_string = \
                header + '\n' + cloud_init_string
        if ctx.node.properties.get('encode_base64'):
            cloud_init_string = \
                base64.encodestring(cloud_init_string)
        return cloud_init_string

    def update(self, **_):
        ctx.instance.runtime_properties['resource_config'] = self.config
        ctx.instance.runtime_properties['cloud_config'] = self.__str__
