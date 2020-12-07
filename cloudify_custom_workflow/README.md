# Cloudify Utilities: Custom Workflow

The custom workflow utility allows you to run list of action as separate
workflow.

## The plugin supports

Plugin have supported `cloudify_custom_workflow.cloudify_custom_workflow.tasks.customwf`
workflow with such parameters:
 * `nodes_to_runon`: List of node names for run action on.
 * `operations_to_execute`: List action names for run.

For example look to [example.yaml](examples/example.yaml).
