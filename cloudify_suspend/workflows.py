# Copyright (c) 2017 GigaSpaces Technologies Ltd. All rights reserved
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
from cloudify.decorators import workflow


def _run_operation(ctx, operation, **kwargs):
    full_operation_name = 'cloudify.interfaces.lifecycle.' + operation
    ctx.logger.debug(operation)
    graph = ctx.graph_mode()

    for node in ctx.nodes:
        if full_operation_name in node.operations:
            for instance in node.instances:
                sequence = graph.sequence()
                sequence.add(
                    instance.send_event('Starting to {}'.format(operation)),
                    instance.execute_operation(full_operation_name, **kwargs),
                    instance.send_event('Done {}'.format(operation)))

    return graph.execute()


@workflow
def suspend(ctx, **kwargs):
    _run_operation(ctx, "suspend", **kwargs)


@workflow
def resume(ctx, **kwargs):
    _run_operation(ctx, "resume", **kwargs)
