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

import setuptools

setuptools.setup(
    name='cloudify-utilities-plugin',
    version='1.13.0',
    author='Cloudify Platform Ltd.',
    author_email='hello@cloudify.co',
    description='Utilities for extending Cloudify',
    packages=['cloudify_deployment_proxy',
              'cloudify_ssh_key',
              'cloudify_files',
              'cloudify_terminal',
              'cloudify_configuration',
              'cloudify_custom_workflow',
              'cloudify_suspend',
              'cloudify_cloudinit',
              'cloudify_rest',
              'cloudify_scalelist',
              'cloudify_secrets'],
    license='LICENSE',
    install_requires=[
        'cloudify-plugins-common>=3.4.2',
        'cloudify-rest-client>=4.0',  # deployment_proxy
        'cloudify-utilities-plugins-sdk==0.0.8',  # terminal, rest
        "Jinja2>=2.7.2",  # terminal, rest, configuration
        'pycrypto',  # ssh_key
        'pyyaml']  # cloudinit and rest
)
