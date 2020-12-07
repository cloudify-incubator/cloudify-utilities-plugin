# cloudify-hooks-workflow

Supported parameters:
* `inputs`: passed from cloudify hooks (or first param hooks)
* `logger_file`: duplicate logger output to separate file
* `client_config`: custom credentials for manager, by default is not required for use
* `filter_by`: key-value list, where:
  * `path`: path to field for validate,
  * `values`: list of possible values
* `workflow_for_run`: name workflow to run on deployment
* `workflow_params`: additional parameter for workflow.

Deployment properties combined for `filter_by`:
* `deployment_inputs`: deployment inputs
* `deployment_outputs`: deployment outputs
* `deployment_capabilities`: deployment capabilities

Additionaly from hooks callback comes to filter:
* `execution_parameters`: parameters originaly received for execution
* `is_system_workflow`: type workflow, e.g.: True/False
* `blueprint_id`: blueprint id
* `tenant_name`: tenant name
* `rest_token`: rest token
* `workflow_id`: workflow id, e.g.: `install`
* `arguments`: resulted arguments
* `timestamp`: current time stamp
* `deployment_id`: deployment id
* `message_type`: type of hooks message
* `execution_id`: execution id
* `event_type`: hooks type, e.g.: `workflow_failed`

As `workflow_params` can be:
* `parameters`: Parameters for the workflow execution.
* `allow_custom_parameters`: Determines whether to allow parameters which
  weren't defined in the workflow parameters schema in the blueprint.
* `force`: Determines whether to force the execution of the workflow in a
  case where there's an already running execution for this deployment.
* `dry_run`: If set to true, no actual actions will be performed. This is
  a dry run of the execution
* `queue`: If set, blocked executions will be queued and automatically run
  when possible
* `schedule`: A string representing the date and time this workflow should
  be executed at. If not passed this workflow will be executed immediately.

Way to reproduce:
* Add such event handler to `/opt/mgmtworker/config/hooks.conf`
[Look to documentation for more information](https://docs.cloudify.co/5.0.5/working_with/manager/actionable-events/).
```yaml
hooks:
- event_type: workflow_failed
  implementation: cloudify-utilities-plugin.cloudify_hooks_workflow.tasks.run_workflow
  inputs:
    logger_file: /tmp/workflow_failed.log
    workflow_for_run: uninstall
    workflow_params: {}
    filter_by:
    - path: ["workflow_id"]
      values: ["install"]
    - path: ["deployment_capabilities", "autouninstall", "value"]
      values: [true, "yes"]
  description: A hook for workflow_failed
```
* check that all deployments with `autouninstall` prefix uninstalled.
```shell
# will be uninstalled after install
cfy install cloudify_hooks_workflow/examples/check-failure.yaml -b check1
# will save alive as deployments is not failed
cfy install cloudify_hooks_workflow/examples/check-failure.yaml -b check2 -i raise_failure_first=ignore_action
# will be stay failed
cfy install cloudify_hooks_workflow/examples/check-failure.yaml -b check3 -i autouninstall=no
```
