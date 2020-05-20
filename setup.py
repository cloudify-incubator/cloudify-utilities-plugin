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

import setuptools

setuptools.setup(
    name='cloudify-utilities-plugin',
    version='1.23.1',
    author='Cloudify Platform Ltd.',
    author_email='hello@cloudify.co',
    description='Utilities for extending Cloudify',
    packages=['cloudify_ssh_key',
              'cloudify_files',
              'cloudify_terminal',
              'cloudify_configuration',
              'cloudify_hooks_workflow',
              'cloudify_custom_workflow',
              'cloudify_suspend',
              'cloudify_cloudinit',
              'cloudify_rest',
              'cloudify_scalelist',
              'cloudify_secrets'],
    license='LICENSE',
    install_requires=[
        'cloudify-common>=4.4',  # deployment_proxy
        'cloudify-utilities-plugins-sdk==0.0.24',  # terminal, rest
        'ruamel.yaml']  # cloudinit
)
