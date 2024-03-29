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
import re
import sys
import pathlib
from setuptools import setup, find_packages


def get_version():
    current_dir = pathlib.Path(__file__).parent.resolve()
    with open(os.path.join(current_dir,
                           'cloudify_cloudinit/__version__.py'),
              'r') as outfile:
        var = outfile.read()
        return re.search(r'\d+.\d+.\d+', var).group()


install_requires = [
    'cloudify-utilities-plugins-sdk>=0.0.129'
]

if sys.version_info.major == 3 and sys.version_info.minor == 6:
    # This is for backwards compatibility for Python 3.6.
    install_requires += [
        'cloudify_types @ git+https://github.com/cloudify-cosmo/' \
        'cloudify-manager.git@6.4.2-build#egg=cloudify-types' \
        '&subdirectory=cloudify_types'
    ]
    packages = [
        'cloudify_ssh_key',
        'cloudify_files',
        'cloudify_deployment_proxy',
        'cloudify_terminal',
        'cloudify_configuration',
        'cloudify_hooks_workflow',
        'cloudify_iso',
        'cloudify_custom_workflow',
        'cloudify_suspend',
        'cloudify_cloudinit',
        'cloudify_rest',
        'cloudify_scalelist',
        'cloudify_secrets',
        'cloudify_rollback_workflow',
        'cloudify_resources'
    ]
else:
    # This is for anything else, in practice it will be Python 3.11.
    install_requires += [
        'fusion-common',
        'fusion-mgmtworker'
    ]
    packages=find_packages()


setup(
    name='cloudify-utilities-plugin',
    version=get_version(),
    author='Cloudify Platform Ltd.',
    author_email='hello@cloudify.co',
    description='Utilities for extending Cloudify',
    packages=packages,
    license='LICENSE',
    install_requires=install_requires
)
