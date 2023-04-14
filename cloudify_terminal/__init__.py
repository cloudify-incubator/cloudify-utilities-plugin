# Copyright (c) 2016-2020 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time

from cloudify import context
from cloudify.decorators import operation
from cloudify import exceptions as cfy_exc
from cloudify import ctx as CloudifyContext

from cloudify_common_sdk import exceptions

# Cloudify delete node action
START_NODE_ACTION = "cloudify.interfaces.lifecycle.start"
STOP_NODE_ACTION = "cloudify.interfaces.lifecycle.stop"
DELETE_NODE_ACTION = "cloudify.interfaces.lifecycle.delete"

# operation flags
FINISHED_OPERATIONS = '_finished_operations'


def rerun(ctx, func, args, kwargs, retry_count=10, retry_sleep=15):
    while retry_count > 0:
        try:
            return func(*args, **kwargs)
        except exceptions.RecoverableWarning as e:
            ctx.logger.info("Need for rerun: {e}".format(e=repr(e)))
            retry_count -= 1
            time.sleep(retry_sleep)
        except (exceptions.RecoverableError,
                exceptions.RecoverableResponseException,
                exceptions.RecoverableStatusCodeCodeException,
                exceptions.ExpectationException) as e:
            raise cfy_exc.RecoverableError(str(e))
        except (exceptions.NonRecoverableError,
                exceptions.NonRecoverableResponseException) as e:
            raise cfy_exc.NonRecoverableError(str(e))

    raise cfy_exc.RecoverableError(
        "Failed to rerun: {args}:{kwargs}"
        .format(args=repr(args), kwargs=repr(kwargs)))


def operation_cleanup(func, force=False):
    def wrapper(*args, **kwargs):
        ctx = kwargs.get('ctx', CloudifyContext)
        # rerun operation in any case
        force_rerun = kwargs.get('force_rerun', force)

        # check current operation state
        if ctx.type == context.NODE_INSTANCE:
            current_action = ctx.operation.name
            operations_finished = ctx.instance.runtime_properties.get(
                FINISHED_OPERATIONS, {})
            if not force_rerun and operations_finished.get(current_action):
                ctx.logger.debug(
                    "Operation {operation} is finished before."
                    .format(operation=current_action))
                return

        # run real operation
        result = func(*args, **kwargs)

        # check current operation
        if ctx.type == context.NODE_INSTANCE:
            current_action = ctx.operation.name
            if current_action == DELETE_NODE_ACTION:
                # cleanup runtime properties
                # need to convert generaton to list, python 3
                for key, _ in list(ctx.instance.runtime_properties.items()):
                    del ctx.instance.runtime_properties[key]
            else:
                # mark oparation as finished
                operations_finished = ctx.instance.runtime_properties.get(
                    FINISHED_OPERATIONS, {})
                operations_finished[current_action] = True
                # revert start on stop
                if current_action == STOP_NODE_ACTION:
                    operations_finished[START_NODE_ACTION] = False
                # copy flags back
                ctx.instance.runtime_properties[
                    FINISHED_OPERATIONS] = operations_finished

            # save flag as current state before external call
            ctx.instance.runtime_properties.dirty = True
            ctx.instance.update()

        return result
    return operation(func=wrapper, resumable=True)


def workflow_get_resource(file_name):
    with open(file_name, 'r') as f:
        return f.read()
