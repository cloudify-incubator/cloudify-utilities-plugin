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

import grp
import os
import pwd
import shutil
import subprocess
from getpass import getuser

from cloudify import ctx
from cloudify.exceptions import (
    NonRecoverableError,
    HttpException
)

from cloudify_common_sdk._compat import text_type


def execute_command(_command, extra_args=None):

    ctx.logger.debug('_command {0}.'.format(_command))

    subprocess_args = {
        'args': _command,
        'stdout': subprocess.PIPE,
        'stderr': subprocess.PIPE
    }

    if extra_args is not None and isinstance(extra_args, dict):
        subprocess_args.update(extra_args)

    ctx.logger.debug('subprocess_args {0}.'.format(subprocess_args))

    process = subprocess.Popen(**subprocess_args)
    output, error = process.communicate()

    ctx.logger.debug('command: {0} '.format(_command))
    ctx.logger.debug('output: {0} '.format(output))
    ctx.logger.debug('error: {0} '.format(error))
    ctx.logger.debug('process.returncode: {0} '.format(process.returncode))

    if process.returncode:
        ctx.logger.error('Running `{0}` returns error.'.format(_command))
        return False

    return output


class CloudifyFile(object):

    def __init__(self, operation_inputs):
        self.config = self.get_config(operation_inputs)
        self.resource_path = self.config.get('resource_path')
        self.file_path = self.config.get('file_path')
        self.owner = self.config.get('owner')
        self.mode = self.config.get('mode')
        self.template_variables = \
            self.config.get('template_variables')
        self.use_sudo = self.config.get('use_sudo')
        self.allow_failure = \
            self.config.get('allow_failure')

    @staticmethod
    def get_config(inputs):
        config = ctx.node.properties.get('resource_config', {})
        config.update(
            ctx.instance.runtime_properties.get('resource_config', {}))
        config.update(inputs.get('resource_config', {}))
        return config

    def create(self):

        try:
            if isinstance(self.template_variables, dict):
                downloaded_file_path = \
                    ctx.download_resource_and_render(
                        self.resource_path,
                        template_variables=self.template_variables)
            else:
                downloaded_file_path = \
                    ctx.download_resource(self.resource_path)
        except HttpException as e:
            err = '{0}'.format(str(e))
            if self.allow_failure is False:
                raise NonRecoverableError(err)
            ctx.logger.error(err)
            return True

        if self.use_sudo:
            add_shell = {'shell': True}
            cp_out = execute_command([
                'sudo', 'cp', str(downloaded_file_path), str(self.file_path)
            ], extra_args=add_shell)
            chown_out = execute_command([
                'sudo', 'chown', str(self.owner), str(self.file_path)
            ], extra_args=add_shell)
            chmod_out = execute_command([
                'sudo', 'chmod', str(self.mode), str(self.file_path)
            ], extra_args=add_shell)
            if cp_out is False or chown_out is False or chmod_out is False:
                raise NonRecoverableError(
                    'Sudo command failed. '
                    'Most likely this is related to {0} user permissions. '
                    'See previous ERROR log message.'.format(getuser()))
            return True

        if not isinstance(self.owner, text_type):
            raise NonRecoverableError('Property owner must be a string.')

        split_owner = self.owner.split(':')

        if len(split_owner) == 1:
            user_string = split_owner[0]
            group_string = split_owner[0]
        elif len(split_owner) == 2:
            user_string = split_owner[0]
            group_string = split_owner[1]
        else:
            raise NonRecoverableError(
                'Property owner must be one of the following '
                'formats: "user" or "user:group".')

        try:
            uid = pwd.getpwnam(user_string).pw_uid
            gid = grp.getgrnam(group_string).gr_gid
        except KeyError as e:
            raise NonRecoverableError('{0}'.format(str(e)))

        try:
            shutil.move(downloaded_file_path, self.file_path)
            os.chown(self.file_path, uid, gid)
            os.chmod(self.file_path, int(str(self.mode), 8))
        except OSError as e:
            raise NonRecoverableError('{0}'.format(str(e)))

        return True

    def delete(self):
        if self.use_sudo:
            execute_command(['sudo', 'rm', self.file_path])
            return True
        os.remove(self.file_path)
        return True
