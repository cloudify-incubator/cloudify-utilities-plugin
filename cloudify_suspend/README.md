# Cloudify Utilities: Suspend
Additional suport for `suspend`/`resume` workflows.

## Supported workflows

* `suspend`: Workflow call `cloudify.interfaces.lifecycle.suspend` for each node that have such operation.
* `resume`: Workflow call `cloudify.interfaces.lifecycle.resume` for each node that have such operation.

# Usage example:

After upload [blueprint](examples/example.yaml) call 'suspend' workflow.

```shell
$ cfy execution start resume -b examples
2017-09-28 08:12:05.125  CFY <examples> Starting 'resume' workflow execution
2017-09-28 08:12:05.127  CFY <examples> [server_11nk1j] Starting to resume
2017-09-28 08:12:05.229  CFY <examples> [server_11nk1j.resume] Sending task 'script_runner.tasks.run'
2017-09-28 08:12:05.257  CFY <examples> [server_11nk1j.resume] Task started 'script_runner.tasks.run'
2017-09-28 08:12:05.361  LOG <examples> [server_11nk1j.resume] INFO: resume server_id=Server!
2017-09-28 08:12:05.361  CFY <examples> [server_11nk1j.resume] Task succeeded 'script_runner.tasks.run'
2017-09-28 08:12:05.484  CFY <examples> [server_11nk1j] Done resume
2017-09-28 08:12:05.552  CFY <examples> 'resume' workflow execution succeeded
```
