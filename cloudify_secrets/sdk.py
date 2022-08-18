########
# Copyright (c) 2014-2019 Cloudify Platform Ltd. All rights reserved
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

import json


class SecretsSDK(object):

    DEFAULT_SEPARATOR = '__'

    @staticmethod
    def _try_to_serialize(value):
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value)

        return str(value)

    @staticmethod
    def _try_to_parse(value):
        try:
            return json.loads(value)
        except ValueError:
            return value

    def __init__(self, logger, rest_client, separator=DEFAULT_SEPARATOR,
                 logs_secrets=False, **_):
        self._logger = logger
        self._rest_client = rest_client
        self._separator = separator
        self._logs_secrets = logs_secrets

    def _handle_variant(self, key, variant=None):
        if variant:
            return '{0}{1}{2}'.format(key, self._separator, variant)

        return key

    def _write(self, rest_client_method, entries, variant=None):
        result = {}

        for key, value in entries.items():
            if self._logs_secrets:
                self._logger.debug(
                    'Creating secret "{0}" with value: {1}'
                    .format(key, value)
                )

            result[key] = rest_client_method(
                key=self._handle_variant(key, variant),
                value=self._try_to_serialize(value)
            )

        return result

    def create(self, entries, variant=None, **_):
        return self._write(self._rest_client.secrets.create, entries, variant)

    def update(self, entries, variant=None, **_):
        return self._write(self._rest_client.secrets.patch, entries, variant)

    def delete(self, secrets, variant=None, **_):
        for key in secrets.keys():
            self._logger.debug(
                'Deleting secret "{0}" ...'.format(key)
            )

            self._rest_client.secrets.delete(
                key=self._handle_variant(key, variant)
            )

    def read(self, keys, variant=None, **_):
        result = {}

        for key in keys:
            self._logger.debug('Reading secret "{0}" ...'.format(key))

            response = self._rest_client.secrets.get(
                key=self._handle_variant(key, variant)
            )

            response['value'] = self._try_to_parse(response['value'])
            result[key] = response

        return result
