# Copyright (c) 2017-2019 Cloudify Platform Ltd. All rights reserved
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

import os
import setuptools


def read(rel_path):
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, rel_path), 'r') as fp:
        return fp.read()


def get_version(rel_file='plugin.yaml'):
    lines = read(rel_file)
    for line in lines.splitlines():
        if 'package_version' in line:
            split_line = line.split(':')
            line_no_space = split_line[-1].replace(' ', '')
            line_no_quotes = line_no_space.replace('\'', '')
            return line_no_quotes.strip('\n')
    raise RuntimeError('Unable to find version string.')

setuptools.setup(
    name='cloudify-utilities-plugin',
    version=get_version(),
    author='Cloudify Platform Ltd.',
    author_email='hello@cloudify.co',
    description='Utilities for extending Cloudify',
    packages=['cloudify_ssh_key',
              'cloudify_files',
              'cloudify_deployment_proxy',
              'cloudify_terminal',
              'cloudify_configuration',
              'cloudify_hooks_workflow',
              'cloudify_custom_workflow',
              'cloudify_suspend',
              'cloudify_cloudinit',
              'cloudify_rest',
              'cloudify_scalelist',
              'cloudify_secrets',
              'cloudify_rollback_workflow'],
    license='LICENSE',
    install_requires=[
        'cloudify-common>=4.5.5',  # deployment_proxy
        'cloudify-utilities-plugins-sdk>=0.0.34',  # terminal, rest
        'ruamel.yaml']  # cloudinit
)
