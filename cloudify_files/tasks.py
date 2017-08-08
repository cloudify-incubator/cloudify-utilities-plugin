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
import re
import tempfile
import StringIO
import ConfigParser
from ConfigParser import DuplicateSectionError

from . import CloudifyFile
from cloudify import ctx
from cloudify.decorators import operation
from cloudify.exceptions import OperationRetry

SECTION_RE = re.compile('\[[A-Za-z0-9-_\.]+\]')
PAIR_RE = re.compile('[A-Za-z0-9_]+[\s]=[\s][A-Za-z0-9_]+')


@operation
def delete(**_):
    if ctx.node.properties.get(
            'use_external_resource', False) is False:
        CloudifyFile(_).remove()


@operation
def create(**_):
    file_node_instance = CloudifyFile(_)
    target_path_dir = os.path.dirname(file_node_instance.target_path)
    if not os.path.exists(target_path_dir):
        raise OperationRetry('{0} does not exist yet.'.format(target_path_dir))

    _, temporary_file_path = tempfile.mkstemp()

    if file_node_instance.resource_path:
        temporary_file_path = \
            get_rendered_file(
                file_node_instance.resource_path,
                file_node_instance.template_variables)
    elif file_node_instance.file_content:
        with open(temporary_file_path, 'w') as outfile:
            outfile.write(file_node_instance.file_content)
    elif file_node_instance.config_sections:
        config_parser = read_config_file(file_node_instance.target_path)
        config_parser = \
            add_to_config(config_parser, file_node_instance.config_sections)
        temporary_file_path = write_config_file(config_parser)

    file_node_instance.rename(temporary_file_path)
    if file_node_instance.file_permissions:
        file_node_instance.chmod()


@operation
def remove(**_):
    if not ctx.node.properties['resource_config'].get('config_sections'):
        return
    file_node_instance = CloudifyFile(_)
    config_parser = read_config_file(file_node_instance.target_path)
    config_parser = \
        remove_from_config(config_parser, file_node_instance.config_sections)
    temporary_file_path = write_config_file(config_parser)
    file_node_instance.rename(temporary_file_path)


def get_rendered_file(_resource_path, _template_variables):

    _, _temporary_file_path = tempfile.mkstemp()

    _rendered_file = \
        ctx.download_resource_and_render(
            _resource_path,
            target_path=_temporary_file_path,
            template_variables=_template_variables or None)

    return _rendered_file


def read_config_file(path_to_file):
    config_string = ''
    if os.path.exists(path_to_file):
        with open(path_to_file, 'r') as outfile:
            for line in outfile.readlines():
                if line == '\n':
                    continue
                line = line.rstrip('\n')
                if not re.match(SECTION_RE, line) and not re.match(PAIR_RE, line):
                    line = '%s = None' % line
                config_string = '%s\n%s' % (config_string, line)
    sio = StringIO.StringIO(config_string)
    _config_parser = ConfigParser.ConfigParser()
    _config_parser.readfp(sio)
    return _config_parser


def write_config_file(_config):
    _, _temporary_file_path = tempfile.mkstemp()
    sio = StringIO.StringIO()
    _config.write(sio)
    with open(_temporary_file_path, 'w') as outfile:
        lines_string = sio.getvalue()
        lines = lines_string.split('\n')
        for line in lines:
            split_line = line.split(' = None')
            outfile.writelines('%s\n' % split_line[0])
    return _temporary_file_path


def add_to_config(_config, sections):
    for section, section_config in sections.items():
        try:
            _config.add_section(section)
        except DuplicateSectionError:
            pass
        if isinstance(section_config, list) or \
                isinstance(section_config, set):
            for li in section_config:
                _config.set(section, li)
        elif isinstance(section_config, dict):
            for k, v in section_config.items():
                _config.set(section, k, v)
    return _config


def remove_from_config(_config, sections):
    for section, section_config in sections.items():
        if isinstance(section_config, list) or \
                isinstance(section_config, set):
            for li in section_config:
                _config.remove_option(section, li)
        elif isinstance(section_config, dict):
            for k, v in section_config.items():
                _config.remove_option(section, k)
        _config.remove_section(section)
    return _config
