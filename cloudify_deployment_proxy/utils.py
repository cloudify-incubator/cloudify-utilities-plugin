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

import sys

from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from cloudify.exceptions import OperationRetry
from cloudify.utils import exception_to_error_cause


def generate_traceback_exception():
    _, exc_value, exc_traceback = sys.exc_info()
    response = exception_to_error_cause(exc_value, exc_traceback)
    return response


def get_desired_value(key,
                      args,
                      instance_attr,
                      node_prop):

    return (args.get(key) or
            instance_attr.get(key) or
            node_prop.get(key))


def update_attributes(_type, _key, _value):
    ctx.instance.runtime_properties[_type][_key] = _value


def proxy_operation(operation):
    def decorator(task, **kwargs):
        def wrapper(**kwargs):
            try:
                kwargs['operation'] = operation
                return task(**kwargs)
            except OperationRetry:
                response = generate_traceback_exception()

                ctx.logger.error(
                    'Error traceback {0} with message {1}'.format(
                        response['traceback'], response['message']))

                raise OperationRetry(
                    'Error: {0} while trying to run proxy task {1}'
                    ''.format(response['message'], operation))

            except Exception:
                response = generate_traceback_exception()

                ctx.logger.error(
                    'Error traceback {0} with message {1}'.format(
                        response['traceback'], response['message']))

                raise NonRecoverableError(
                    'Error: {0} while trying to run proxy task {1}'
                    ''.format(response['message'], operation))

        return wrapper
    return decorator
