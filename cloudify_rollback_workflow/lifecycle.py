########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
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

import itertools

from cloudify import utils
from cloudify import constants
from cloudify.state import workflow_ctx
from cloudify.workflows.tasks_graph import forkjoin, make_or_get_graph
from cloudify.workflows import tasks as workflow_tasks


def rollback_node_instances(graph,
                            node_instances,
                            related_nodes=None,
                            name_prefix=''):
    processor = UtilitiesLifecycleProcessor(graph=graph,
                                            node_instances=node_instances,
                                            related_nodes=related_nodes,
                                            name_prefix=name_prefix,
                                            ignore_failure=True)

    processor.rollback()


class UtilitiesLifecycleProcessor(object):

    def __init__(self,
                 graph,
                 node_instances=None,
                 related_nodes=None,
                 modified_relationship_ids=None,
                 ignore_failure=False,
                 name_prefix=''):
        self.graph = graph
        self.node_instances = node_instances or set()
        self.intact_nodes = related_nodes or set()
        self.modified_relationship_ids = modified_relationship_ids or {}
        self.ignore_failure = ignore_failure
        self._name_prefix = name_prefix

    def rollback(self):
        graph = self._process_node_instances(
            workflow_ctx,
            name=self._name_prefix + 'rollback',
            node_instance_subgraph_func=rollback_node_instance_subgraph,
            graph_finisher_func=self._finish_uninstall)
        graph.execute()

    @make_or_get_graph
    def _process_node_instances(self,
                                ctx,
                                node_instance_subgraph_func,
                                graph_finisher_func):
        subgraphs = {}
        for instance in self.node_instances:
            subgraphs[instance.id] = \
                node_instance_subgraph_func(
                    instance, self.graph, ignore_failure=self.ignore_failure)

        for instance in self.intact_nodes:
            subgraphs[instance.id] = self.graph.subgraph(
                'stub_{0}'.format(instance.id))

        graph_finisher_func(self.graph, subgraphs)
        return self.graph

    def _finish_uninstall(self, graph, subgraphs):
        self._finish_subgraphs(
            graph=graph,
            subgraphs=subgraphs,
            intact_op='cloudify.interfaces.relationship_lifecycle.unlink',
            install=False)

    def _finish_subgraphs(self, graph, subgraphs, intact_op, install):
        # Create task dependencies based on node relationships
        self._add_dependencies(graph=graph,
                               subgraphs=subgraphs,
                               instances=self.node_instances,
                               install=install)

        def intact_on_dependency_added(instance, rel, source_task_sequence):
            if (rel.target_node_instance in self.node_instances or
                    rel.target_node_instance.node_id in
                    self.modified_relationship_ids.get(instance.node_id, {})):
                intact_tasks = _relationship_operations(rel, intact_op)
                for intact_task in intact_tasks:
                    if not install:
                        set_send_node_event_on_error_handler(
                            intact_task, instance)

                    source_task_sequence.add(intact_task)

        # Add operations for intact nodes depending on a node instance
        # belonging to node_instances
        self._add_dependencies(graph=graph,
                               subgraphs=subgraphs,
                               instances=self.intact_nodes,
                               install=install,
                               on_dependency_added=intact_on_dependency_added)

    @staticmethod
    def _handle_dependency_creation(source_subgraph, target_subgraph,
                                    operation, target_id, graph):
        if operation:
            for task_subgraph in target_subgraph.graph.tasks:
                # If the task is not an operation task
                if not task_subgraph.cloudify_context:
                    continue

                operation_path, operation_name = \
                    (task_subgraph.cloudify_context["operation"]["name"]
                     .rsplit(".", 1))
                node_id = task_subgraph.cloudify_context["node_id"]
                if (operation_path == 'cloudify.interfaces.lifecycle' and
                        operation_name == operation and
                        target_id == node_id):

                    # Adding dependency to all post tasks that are dependent
                    # of the chosen operation, with the assumption that they
                    # are all only dependent on the operation not each other.
                    for task_id in target_subgraph.graph._dependents.get(
                            task_subgraph.id, []):
                        graph.add_dependency(source_subgraph,
                                             target_subgraph.graph.get_task(
                                                 task_id))
                    break
        else:
            graph.add_dependency(source_subgraph, target_subgraph)

    def _add_dependencies(self, graph, subgraphs, instances, install,
                          on_dependency_added=None):
        subgraph_sequences = dict(
            (instance_id, subgraph.sequence())
            for instance_id, subgraph in subgraphs.items())
        for instance in instances:
            relationships = list(instance.relationships)
            if not install:
                relationships = reversed(relationships)
            for rel in relationships:
                if (rel.target_node_instance in self.node_instances or
                        rel.target_node_instance in self.intact_nodes):
                    source_subgraph = subgraphs[instance.id]
                    target_subgraph = subgraphs[rel.target_id]

                    operation = rel.relationship.properties.get("operation",
                                                                None)

                    if install:
                        self._handle_dependency_creation(source_subgraph,
                                                         target_subgraph,
                                                         operation,
                                                         rel.target_id,
                                                         graph)
                    else:
                        self._handle_dependency_creation(target_subgraph,
                                                         source_subgraph,
                                                         operation,
                                                         instance.id,
                                                         graph)

                    if on_dependency_added:
                        task_sequence = subgraph_sequences[instance.id]
                        on_dependency_added(instance, rel, task_sequence)


def set_send_node_event_on_error_handler(task, instance):
    task.on_failure = _SendNodeEventHandler(instance)


def _skip_nop_operations(task, pre=None, post=None):
    """If `task` is a NOP, then skip pre and post

    Useful for skipping the 'creating node instance' message in case
    no creating is actually going to happen.
    """
    if not task or task.is_nop():
        return []
    if pre is None:
        pre = []
    if post is None:
        post = []
    if not isinstance(pre, list):
        pre = [pre]
    if not isinstance(post, list):
        post = [post]
    return pre + [task] + post


def _relationships_operations(graph,
                              node_instance,
                              operation,
                              reverse=False,
                              modified_relationship_ids=None):
    relationships_groups = itertools.groupby(
        node_instance.relationships,
        key=lambda r: r.relationship.target_id)
    tasks = []
    for _, relationship_group in relationships_groups:
        group_tasks = []
        for relationship in relationship_group:
            # either the relationship ids aren't specified, or all the
            # relationship should be added
            source_id = relationship.node_instance.node.id
            target_id = relationship.target_node_instance.node.id
            if (not modified_relationship_ids or
                    (source_id in modified_relationship_ids and
                     target_id in modified_relationship_ids[source_id])):
                group_tasks += [
                    op
                    for op in _relationship_operations(relationship, operation)
                    if not op.is_nop()
                ]
        if group_tasks:
            tasks.append(forkjoin(*group_tasks))
    if not tasks:
        return
    if reverse:
        tasks = reversed(tasks)
    result = graph.subgraph('{0}_subgraph'.format(operation))
    result.on_failure = _relationship_subgraph_on_failure
    sequence = result.sequence()
    sequence.add(*tasks)
    return result


def _relationship_operations(relationship, operation):
    return [relationship.execute_source_operation(operation),
            relationship.execute_target_operation(operation)]


def is_host_node(node_instance):
    return constants.COMPUTE_NODE_TYPE in node_instance.node.type_hierarchy


def _host_pre_stop(host_node_instance):
    install_method = utils.internal.get_install_method(
        host_node_instance.node.properties)
    tasks = []
    tasks += [
        host_node_instance.execute_operation(
            'cloudify.interfaces.monitoring_agent.stop'),
        host_node_instance.execute_operation(
            'cloudify.interfaces.monitoring_agent.uninstall'),
    ]
    if install_method != constants.AGENT_INSTALL_METHOD_NONE:
        tasks.append(host_node_instance.send_event('Stopping agent'))
        if install_method in constants.AGENT_INSTALL_METHODS_SCRIPTS:
            # this option is only available since 3.3 so no need to
            # handle 3.2 version here.
            tasks += [
                host_node_instance.execute_operation(
                    'cloudify.interfaces.cloudify_agent.stop_amqp'),
                host_node_instance.send_event('Deleting agent'),
                host_node_instance.execute_operation(
                    'cloudify.interfaces.cloudify_agent.delete')
            ]
        else:
            node_operations = host_node_instance.node.operations
            if 'cloudify.interfaces.worker_installer.stop' in node_operations:
                tasks += [
                    host_node_instance.execute_operation(
                        'cloudify.interfaces.worker_installer.stop'),
                    host_node_instance.send_event('Deleting agent'),
                    host_node_instance.execute_operation(
                        'cloudify.interfaces.worker_installer.uninstall')
                ]
            else:
                tasks += [
                    host_node_instance.execute_operation(
                        'cloudify.interfaces.cloudify_agent.stop'),
                    host_node_instance.send_event('Deleting agent'),
                    host_node_instance.execute_operation(
                        'cloudify.interfaces.cloudify_agent.delete')
                ]
        tasks += [host_node_instance.send_event('Agent deleted')]
    return tasks


class _SendNodeEventHandler(object):
    def __init__(self, instance=None, instance_id=None):
        if instance is None:
            instance = workflow_ctx.get_node_instance(instance_id)
        self.instance = instance

    def dump(self):
        return {
            'instance_id': self.instance.id,
        }

    def __call__(self, tsk):
        event = self.instance.send_event(
            'Ignoring task {0} failure'.format(tsk.name))
        event.apply_async()
        return workflow_tasks.HandlerResult.ignore()


def _relationship_subgraph_on_failure(subgraph):
    for task in subgraph.tasks.values():
        subgraph.remove_task(task)
    handler_result = workflow_tasks.HandlerResult.ignore()
    subgraph.containing_subgraph.failed_task = subgraph.failed_task
    subgraph.containing_subgraph.set_state(workflow_tasks.TASK_FAILED)
    return handler_result


def _node_get_state_handler(tsk):
    host_started = tsk.async_result.get()
    if host_started:
        return workflow_tasks.HandlerResult.cont()
    else:
        return workflow_tasks.HandlerResult.retry(ignore_total_retries=True)


def rollback_node_instance_subgraph(instance, graph, ignore_failure):
    subgraph = graph.subgraph(instance.id)
    sequence = subgraph.sequence()

    def set_ignore_handlers(_subgraph):
        for task in _subgraph.tasks.values():
            if task.is_subgraph:
                set_ignore_handlers(task)
            else:
                set_send_node_event_on_error_handler(task, instance)

    # Remove unneeded operations
    instance_state = instance.state
    # decide if do prestop stop and validation delete

    if instance_state not in ['starting']:
        stop_message = []
        monitoring_stop = []
        host_pre_stop = []
        prestop = []
        deletion_validation = []
        stop = [instance.send_event(
            'Rollback Stop: nothing to do, instance state is {0}'.format(
                instance_state))]
        configured_set_state = []
    else:
        stop_message = [
            forkjoin(
                instance.set_state('stopping'),
                instance.send_event('Stopping node instance')
            )
        ]
        monitoring_stop = _skip_nop_operations(
            instance.execute_operation('cloudify.interfaces.monitoring.stop')
        )

        # Only exists in >= 5.0.
        if 'cloudify.interfaces.validation.delete' in instance.node.operations:
            deletion_validation = _skip_nop_operations(
                pre=instance.send_event(
                    'Validating node instance before deletion'),
                task=instance.execute_operation(
                    'cloudify.interfaces.validation.delete'
                ),
                post=instance.send_event(
                    'Node instance validated before deletion')
            )
        else:
            deletion_validation = []

        # Only exists in >= 5.0.
        if 'cloudify.interfaces.lifecycle.prestop' in instance.node.operations:
            prestop = _skip_nop_operations(
                pre=instance.send_event('Prestopping node instance'),
                task=instance.execute_operation(
                    'cloudify.interfaces.lifecycle.prestop'),
                post=instance.send_event('Node instance prestopped'))
        else:
            prestop = []

        if is_host_node(instance):
            host_pre_stop = _host_pre_stop(instance)
        else:
            host_pre_stop = []

        stop = _skip_nop_operations(
            task=instance.execute_operation(
                'cloudify.interfaces.lifecycle.stop'),
            post=instance.send_event('Stopped node instance'))

        configured_set_state = [instance.set_state('configured')]

    # Decide when we want to unlink +delete + post delete
    if instance_state not in ['creating', 'configuring']:
        unlink = []
        postdelete = []
        delete = [instance.send_event(
            'Rollback Delete: nothing to do, instance state is {0}'.format(
                instance_state))]
        uninitialized_set_state = []
    else:
        unlink = _skip_nop_operations(
            pre=instance.send_event('Unlinking relationships'),
            task=_relationships_operations(
                subgraph,
                instance,
                'cloudify.interfaces.relationship_lifecycle.unlink',
                reverse=True),
            post=instance.send_event('Relationships unlinked')
        )
        delete = _skip_nop_operations(
            pre=forkjoin(
                instance.set_state('deleting'),
                instance.send_event('Deleting node instance')),
            task=instance.execute_operation(
                'cloudify.interfaces.lifecycle.delete')
        )
        # Only exists in >= 5.0.
        if 'cloudify.interfaces.lifecycle.postdelete' \
                in instance.node.operations:
            postdelete = _skip_nop_operations(
                pre=instance.send_event('Postdeleting node instance'),
                task=instance.execute_operation(
                    'cloudify.interfaces.lifecycle.postdelete'),
                post=instance.send_event('Node instance postdeleted'))
        else:
            postdelete = []

        uninitialized_set_state = [instance.set_state('uninitialized')]

    if instance_state not in ['creating', 'configuring', 'starting']:
        finish_message = []
    else:
        finish_message = [
            instance.send_event('Rollbacked node instance')
        ]

    tasks = (
            stop_message +
            (deletion_validation or
             [instance.send_event('Validating node instance after deletion: '
                                  'nothing to do')]) +
            monitoring_stop +
            prestop +
            host_pre_stop +
            (stop or
             [instance.send_event('Stopped node instance: nothing to do')]) +
            configured_set_state +
            unlink +
            (delete or
             [instance.send_event('Deleting node instance: nothing to do')]) +
            postdelete +
            uninitialized_set_state +
            finish_message
    )
    sequence.add(*tasks)

    if ignore_failure:
        set_ignore_handlers(subgraph)
    # else:
    #     subgraph.on_failure = get_subgraph_on_failure_handler(
    #         instance, rollback_node_instance_subgraph)

    return subgraph
