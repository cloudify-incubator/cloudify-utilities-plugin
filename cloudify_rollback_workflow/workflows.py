# Copyright (c) 2016-2019 Cloudify Platform Ltd. All rights reserved
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
from cloudify.workflows.tasks_graph import make_or_get_graph
from cloudify.plugins.lifecycle import set_send_node_event_on_error_handler


@workflow(resumable=True)
def start(ctx, operation_parms, run_by_dependency_order, type_names, node_ids,
          node_instance_ids, ignore_failure, **kwargs):
    execute_operation(ctx, 'cloudify.interfaces.lifecycle.start',
                      operation_parms, True, run_by_dependency_order,
                      type_names, node_ids, node_instance_ids, ignore_failure,
                      **kwargs)


@workflow(resumable=True)
def stop(ctx, operation_parms, run_by_dependency_order, type_names, node_ids,
         node_instance_ids, ignore_failure, **kwargs):
    execute_operation(ctx, 'cloudify.interfaces.lifecycle.stop',
                      operation_parms, True, run_by_dependency_order,
                      type_names, node_ids, node_instance_ids, ignore_failure,
                      **kwargs)


@workflow(resumable=True)
def precreate(ctx, operation_parms, run_by_dependency_order, type_names,
              node_ids, node_instance_ids, ignore_failure, **kwargs):
    execute_operation(ctx, 'cloudify.interfaces.lifecycle.precreate',
                      operation_parms, True, run_by_dependency_order,
                      type_names, node_ids, node_instance_ids, ignore_failure,
                      **kwargs)


@workflow(resumable=True)
def create(ctx, operation_parms, run_by_dependency_order, type_names,
           node_ids, node_instance_ids, ignore_failure, **kwargs):
    execute_operation(ctx, 'cloudify.interfaces.lifecycle.create',
                      operation_parms, True, run_by_dependency_order,
                      type_names, node_ids, node_instance_ids, ignore_failure,
                      **kwargs)


@workflow(resumable=True)
def configure(ctx, operation_parms, run_by_dependency_order, type_names,
              node_ids, node_instance_ids, ignore_failure, **kwargs):
    execute_operation(ctx, 'cloudify.interfaces.lifecycle.configure',
                      operation_parms, True, run_by_dependency_order,
                      type_names, node_ids, node_instance_ids, ignore_failure,
                      **kwargs)


@workflow(resumable=True)
def poststart(ctx, operation_parms, run_by_dependency_order, type_names,
              node_ids, node_instance_ids, ignore_failure, **kwargs):
    execute_operation(ctx, 'cloudify.interfaces.lifecycle.poststart',
                      operation_parms, True, run_by_dependency_order,
                      type_names, node_ids, node_instance_ids, ignore_failure,
                      **kwargs)


@workflow(resumable=True)
def prestop(ctx, operation_parms, run_by_dependency_order, type_names,
            node_ids, node_instance_ids, ignore_failure, **kwargs):
    execute_operation(ctx, 'cloudify.interfaces.lifecycle.prestop',
                      operation_parms, True, run_by_dependency_order,
                      type_names, node_ids, node_instance_ids, ignore_failure,
                      **kwargs)


@workflow(resumable=True)
def delete(ctx, operation_parms, run_by_dependency_order, type_names,
           node_ids, node_instance_ids, ignore_failure, **kwargs):
    execute_operation(ctx, 'cloudify.interfaces.lifecycle.delete',
                      operation_parms, True, run_by_dependency_order,
                      type_names, node_ids, node_instance_ids, ignore_failure,
                      **kwargs)


@workflow(resumable=True)
def postdelete(ctx, operation_parms, run_by_dependency_order, type_names,
               node_ids, node_instance_ids, ignore_failure, **kwargs):
    execute_operation(ctx, 'cloudify.interfaces.lifecycle.postdelete',
                      operation_parms, True, run_by_dependency_order,
                      type_names, node_ids, node_instance_ids, ignore_failure,
                      **kwargs)


@workflow(resumable=True)
def execute_operation(ctx, operation, *args, **kwargs):
    """ A generic workflow for executing arbitrary operations on nodes """
    name = 'execute_operation_{0}'.format(operation)
    graph = _make_execute_operation_graph(
        ctx, operation, name=name, *args, **kwargs)
    graph.execute()


@make_or_get_graph
def _make_execute_operation_graph(ctx, operation, operation_kwargs,
                                  allow_kwargs_override,
                                  run_by_dependency_order, type_names,
                                  node_ids, node_instance_ids, ignore_failure,
                                  **kwargs):
    graph = ctx.graph_mode()
    subgraphs = {}

    # filtering node instances
    filtered_node_instances = _filter_node_instances(
        ctx=ctx,
        node_ids=node_ids,
        node_instance_ids=node_instance_ids,
        type_names=type_names)

    if run_by_dependency_order:
        # if run by dependency order is set, then create stub subgraphs for the
        # rest of the instances. This is done to support indirect
        # dependencies, i.e. when instance A is dependent on instance B
        # which is dependent on instance C, where A and C are to be executed
        # with the operation on (i.e. they're in filtered_node_instances)
        # yet B isn't.
        # We add stub subgraphs rather than creating dependencies between A
        # and C themselves since even though it may sometimes increase the
        # number of dependency relationships in the execution graph, it also
        # ensures their number is linear to the number of relationships in
        # the deployment (e.g. consider if A and C are one out of N instances
        # of their respective nodes yet there's a single instance of B -
        # using subgraphs we'll have 2N relationships instead of N^2).
        filtered_node_instances_ids = set(inst.id for inst in
                                          filtered_node_instances)
        for instance in ctx.node_instances:
            if instance.id not in filtered_node_instances_ids:
                subgraphs[instance.id] = graph.subgraph(instance.id)

    # preparing the parameters to the execute_operation call
    exec_op_params = {
        'kwargs': operation_kwargs,
        'operation': operation
    }
    if allow_kwargs_override is not None:
        exec_op_params['allow_kwargs_override'] = allow_kwargs_override

    # registering actual tasks to sequences
    for instance in filtered_node_instances:
        start_event_message = 'Starting operation {0}'.format(operation)
        if operation_kwargs:
            start_event_message += ' (Operation parameters: {0})'.format(
                operation_kwargs)
        subgraph = graph.subgraph(instance.id)
        sequence = subgraph.sequence()
        sequence.add(
            instance.send_event(start_event_message),
            instance.execute_operation(**exec_op_params),
            instance.send_event('Finished operation {0}'.format(operation)))
        if ignore_failure:
            set_ignore_handlers(subgraph, instance)
        subgraphs[instance.id] = subgraph

    # adding tasks dependencies if required
    if run_by_dependency_order:
        for instance in ctx.node_instances:
            for rel in instance.relationships:
                graph.add_dependency(subgraphs[instance.id],
                                     subgraphs[rel.target_id])
    return graph


def _filter_node_instances(ctx, node_ids, node_instance_ids, type_names):
    filtered_node_instances = []
    for node in ctx.nodes:
        if node_ids and node.id not in node_ids:
            continue
        if type_names and not next((type_name for type_name in type_names if
                                    type_name in node.type_hierarchy), None):
            continue

        for instance in node.instances:
            if node_instance_ids and instance.id not in node_instance_ids:
                continue
            filtered_node_instances.append(instance)
    return filtered_node_instances


def set_ignore_handlers(_subgraph, instance):
    for task in _subgraph.tasks.values():
        if task.is_subgraph:
            set_ignore_handlers(task)
        else:
            set_send_node_event_on_error_handler(task, instance)
