# Copyright (c) 2020 Cloudify Platform Ltd. All rights reserved
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
from io import BytesIO

from cloudify_terminal import operation_cleanup

import cloudify_common_sdk.ftp as ftp

FTP_STORE_FILES = 'files'


@operation_cleanup
def create(ctx, resource_config, raw_files, files, **kwargs):
    uploaded = ctx.instance.runtime_properties.get(FTP_STORE_FILES, [])
    # files
    for file_name in files:
        file_bufer = BytesIO()
        file_bufer.write(files[file_name].encode())

        ftp.storbinary(
            host=resource_config['ip'],
            port=resource_config['port'],
            user=resource_config['user'],
            password=resource_config['password'],
            ignore_host=resource_config.get('ignore_host', False),
            tls=resource_config.get('tls', False),
            filename=file_name,
            stream=file_bufer)
        uploaded.append(file_name)
        # save
        ctx.instance.runtime_properties[FTP_STORE_FILES] = uploaded
        # save flag as current state before external call
        ctx.instance.runtime_properties.dirty = True
        ctx.instance.update()

    # raw_files
    for file_name in raw_files:
        file_bufer = BytesIO()
        file_bufer.write(ctx.get_resource(raw_files[file_name]).encode())

        ftp.storbinary(
            host=resource_config['ip'],
            port=resource_config['port'],
            user=resource_config['user'],
            password=resource_config['password'],
            ignore_host=resource_config.get('ignore_host', False),
            tls=resource_config.get('tls', False),
            filename=file_name,
            stream=file_bufer)
        uploaded.append(file_name)
        # save
        ctx.instance.runtime_properties[FTP_STORE_FILES] = uploaded
        # save flag as current state before external call
        ctx.instance.runtime_properties.dirty = True
        ctx.instance.update()


@operation_cleanup
def delete(ctx, resource_config, **kwargs):
    uploaded = ctx.instance.runtime_properties.get(FTP_STORE_FILES, [])
    for file_name in uploaded:
        ftp.delete(
            host=resource_config['ip'],
            port=resource_config['port'],
            user=resource_config['user'],
            password=resource_config['password'],
            ignore_host=resource_config.get('ignore_host', False),
            tls=resource_config.get('tls', False),
            filename=file_name)
