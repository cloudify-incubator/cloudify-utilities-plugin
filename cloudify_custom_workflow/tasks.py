from cloudify import ctx
from cloudify.workflows import ctx as workflow_ctx
from cloudify.decorators import workflow
import json


def log(**kwargs):
    ctx.logger.info("Log interface: {}".format(repr(kwargs)))


@workflow
def customwf(nodes_to_runon, operations_to_execute, **kwargs):

    ctx = workflow_ctx
    ctx.logger.info("Starting Custom Workflow")

    try:
        nodes = json.loads(nodes_to_runon)
    except TypeError:
        ctx.logger.info("Nodes not in Json trying directly")
        nodes = nodes_to_runon

    try:
        operations = json.loads(operations_to_execute)
    except TypeError:
        ctx.logger.info("operations not in Json trying directly")
        operations = operations_to_execute

    ctx.logger.info("Nodes {} on Operations {}".format(nodes, operations))
    # update interface on the config node
    graph = ctx.graph_mode()

    sequence = graph.sequence()
    for opnode in nodes:
        for node in ctx.nodes:
            if node.id == opnode:
                for instance in node.instances:
                    for operation in operations:
                        # add to run operation
                        sequence.add(
                            instance.send_event(
                                'Starting to {} on instance {} of node {}'
                                .format(operation, instance.id, node.id)),
                            instance.execute_operation(operation,
                                                       kwargs=kwargs),
                            instance.send_event('Done {}'.format(operation)))

    graph.execute()
