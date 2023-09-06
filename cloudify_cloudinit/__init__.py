# Copyright (c) 2017-2018 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import json
import yaml
from cloudify import ctx


class CloudInit(object):

    def __init__(self, operation_inputs):
        """
        Sets the properties that all operations need.
        :param operation_inputs: The inputs from the operation.
        """

        self.config = self.get_config(operation_inputs)

    @staticmethod
    def get_external_resource(config):
        for f in config.get('write_files', []):
            if not isinstance(f, dict):
                break
            try:
                content = f.get('content')
                if isinstance(content, dict):
                    resource_type = content.get('resource_type', '')
                    resource_name = content.get('resource_name', '')
                    template_variables = content.get('template_variables', {})
                    if 'file_resource' == resource_type:
                        if template_variables:
                            new_content = ctx.get_resource_and_render(
                                resource_name, template_variables)
                        else:
                            new_content = ctx.get_resource(resource_name)
                        f['content'] = new_content
            except ValueError:
                ctx.logger.debug('No external resource recognized.')
                pass
        return config

    def get_config(self, inputs):

        config = ctx.node.properties.get('resource_config', {})
        config.update(
            ctx.instance.runtime_properties.get('resource_config', {}))
        config.update(inputs.get('resource_config', {}))
        config.update(self.get_external_resource(config.copy()))

        return config

    def json(self):
        """Dump json representaion of config"""
        return json.dumps(self.config)

    @property
    def __str__(self):
        """Override the string implementation of object."""

        cloud_init = yaml.dump(
            self.config, default_flow_style=False, sort_keys=False)
        cloud_init_string = str(cloud_init).replace('!!python/unicode ', '')
        header = ctx.node.properties.get('header')
        if header:
            cloud_init_string = \
                header + '\n' + cloud_init_string
        if ctx.node.properties.get('encode_base64'):
            return base64.b64encode(
                cloud_init_string.encode()).decode(
                    'ascii')
        return cloud_init_string

    def update(self, **_):
        ctx.instance.runtime_properties['resource_config'] = self.config
        ctx.instance.runtime_properties['cloud_config'] = self.__str__
        ctx.instance.runtime_properties['json_config'] = self.json()
