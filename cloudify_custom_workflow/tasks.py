from cloudify import ctx
from cloudify.workflows import ctx as workflow_ctx
from cloudify.decorators import workflow
import json


def log(**kwargs):
    ctx.logger.info("Log interface")


@workflow
def customwf( nodes_to_runon, operations_to_execute, **kwargs):

    ctx = workflow_ctx
    ctx.logger.info("Starting Custom Workflow")

    nodes =  json.loads(nodes_to_runon)
    operations = json.loads(operations_to_execute)
    ctx.logger.info("Nodes {} on Operations {}".format(nodes, operations))
    # update interface on the config node
    graph = ctx.graph_mode()

    sequence = graph.sequence()
    for node in ctx.nodes:
        if node.id in nodes:
            for instance in node.instances:
                for operation in operations:
                    ctx.logger.info("Running operation {} on instance {} of node {}".format(operation ,instance.id, node.id))
                    operation_task = instance.execute_operation( operation )
                    sequence.add(operation_task)

    graph.execute()
