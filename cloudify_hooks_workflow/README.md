# cloudify-hooks-workflow

Way to reproduce:
* Add such event handler to `/opt/mgmtworker/config/hooks.conf`
[Look to documentation for more information](https://docs.cloudify.co/5.0.5/working_with/manager/actionable-events/).
```yaml
hooks:
- event_type: workflow_failed
  implementation: cloudify-utilities-plugin.cloudify_hooks_workflow.tasks.run_workflow
  inputs:
    workflow_for_run: uninstall
    workflow_params: {}
    filter_by:
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
