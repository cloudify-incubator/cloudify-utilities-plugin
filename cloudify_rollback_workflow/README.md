# Cloudify Utilities: Rollback Workflow

## Description
Add support for rollback node instances that exists in unresolved states due to failure in install workflow.
Also, wrappers workflows for cloudify lifecycle operations introduced.

## Prerequisites
* Tested with Cloudify 5.1.1.

## Supported workflows

The plugin supports:

### Rollback workflow

Rollback workflow will look at each node state, decide if the node state
is unresolved, and for those that are, execute the corresponding node
operation that will get us back to a resolved node state.

Unresolved node instance states are:
* creating
* configuring 
* starting


After rollback, `creating` and `configuring` node instances become `uninitialized`.
`starting` node instances become `uninitialized`. 
 

Parameters:
* `type_names`: A list of type names. The operation will be executed 
  only on node instances which are of these types or of types which
  (recursively) derive from them. An empty list means no filtering
  will take place and all type names are valid (Default: []). 
* `param node_ids`: A list of node ids. The operation will be executed only 
  on node instances which are instances of these nodes. An empty list
  means no filtering will take place and all nodes are valid (Default: []). 
* `node_instance_ids`: A list of node instance ids. The operation will
  be executed only on the node instances specified. An empty list
  means no filtering will take place and all node instances are valid (Default: []). 
*`full_rollback`: Whether to rollback to resolved state or full uninstall.

**Notes**: 
* All lifecycle operations(like: `cloudify.interfaces.lifecycle.delete`) that performed during rollback of an unresolved instance  
are performed while ignoring failures for this node instances.
If `full_rollback` chosen, so after rollback of unresolved nodes the rest of the nodes will be uninstalled without ignoring failures.
* Known issue for regular rollback (not full) - when rollback node instance X from `starting` state to `configured` state, if after rollback uninstall workflow performed then during
 uninstall `cloudify.interfaces.lifecycle.stop` operation will be executed(which can cause failure for uninstall) , it will be better to use `full_rollback` in this case.

### Example

[Example](examples/rollback_to_configured_and_uninitialized.yaml) demonstrates rollback of two node instances.



#### Install the example blueprint 

install [blueprint](examples/rollback_to_configured_and_uninitialized.yaml).
```shell
[root@9fbb5f2b0d4b offcial_examples]# cfy install rollback_to_configured_and_uninitialized.yaml -b rollback_to_configured_and_uninitialized -d rollback_to_configured_and_uninitialized
Uploading blueprint rollback_to_configured_and_uninitialized.yaml...
 rollback_to_confi... |################################################| 100.0%
Blueprint uploaded. The blueprint's id is rollback_to_configured_and_uninitialized
Creating new deployment from blueprint rollback_to_configured_and_uninitialized...
Deployment created. The deployment's id is rollback_to_configured_and_uninitialized
Executing workflow `install` on deployment `rollback_to_configured_and_uninitialized` [timeout=900 seconds]
Deployment environment creation is pending...
2021-01-12 13:43:06.111  CFY <rollback_to_configured_and_uninitialized> Starting 'create_deployment_environment' workflow execution
2021-01-12 13:43:06.113  LOG <rollback_to_configured_and_uninitialized> INFO: Creating deployment work directory
2021-01-12 13:43:06.151  CFY <rollback_to_configured_and_uninitialized> 'create_deployment_environment' workflow execution succeeded
2021-01-12 13:43:09.810  CFY <rollback_to_configured_and_uninitialized> Starting 'install' workflow execution
2021-01-12 13:43:09.985  CFY <rollback_to_configured_and_uninitialized> [node_three_tmjr2n] Validating node instance before creation: nothing to do
2021-01-12 13:43:09.987  CFY <rollback_to_configured_and_uninitialized> [node_three_tmjr2n] Precreating node instance: nothing to do
2021-01-12 13:43:09.987  CFY <rollback_to_configured_and_uninitialized> [node_three_tmjr2n] Creating node instance: nothing to do
2021-01-12 13:43:09.988  CFY <rollback_to_configured_and_uninitialized> [node_three_tmjr2n] Configuring node instance: nothing to do
2021-01-12 13:43:09.990  CFY <rollback_to_configured_and_uninitialized> [node_three_tmjr2n] Starting node instance
2021-01-12 13:43:10.266  CFY <rollback_to_configured_and_uninitialized> [node_three_tmjr2n.start] Sending task 'script_runner.tasks.run'
2021-01-12 13:43:10.888  LOG <rollback_to_configured_and_uninitialized> [node_three_tmjr2n.start] INFO: Downloaded resources/install.py to /tmp/NC2GQ/install.py
2021-01-12 13:43:10.888  LOG <rollback_to_configured_and_uninitialized> [node_three_tmjr2n.start] INFO: log without fail during install
2021-01-12 13:43:11.164  CFY <rollback_to_configured_and_uninitialized> [node_three_tmjr2n.start] Task succeeded 'script_runner.tasks.run'
2021-01-12 13:43:11.164  CFY <rollback_to_configured_and_uninitialized> [node_three_tmjr2n] Poststarting node instance: nothing to do
2021-01-12 13:43:11.166  CFY <rollback_to_configured_and_uninitialized> [node_three_tmjr2n] Node instance started
2021-01-12 13:43:11.414  CFY <rollback_to_configured_and_uninitialized> [node_two_y7fcvt] Validating node instance before creation: nothing to do
2021-01-12 13:43:11.415  CFY <rollback_to_configured_and_uninitialized> [node_two_y7fcvt] Precreating node instance: nothing to do
2021-01-12 13:43:11.417  CFY <rollback_to_configured_and_uninitialized> [node_two_y7fcvt] Creating node instance
2021-01-12 13:43:11.421  CFY <rollback_to_configured_and_uninitialized> [node_one_j5jqtj] Validating node instance before creation: nothing to do
2021-01-12 13:43:11.423  CFY <rollback_to_configured_and_uninitialized> [node_one_j5jqtj] Precreating node instance: nothing to do
2021-01-12 13:43:11.486  CFY <rollback_to_configured_and_uninitialized> [node_one_j5jqtj] Creating node instance: nothing to do
2021-01-12 13:43:11.489  CFY <rollback_to_configured_and_uninitialized> [node_one_j5jqtj] Configuring node instance: nothing to do
2021-01-12 13:43:11.497  CFY <rollback_to_configured_and_uninitialized> [node_one_j5jqtj] Starting node instance
2021-01-12 13:43:11.783  CFY <rollback_to_configured_and_uninitialized> [node_two_y7fcvt.create] Sending task 'script_runner.tasks.run'
2021-01-12 13:43:12.034  CFY <rollback_to_configured_and_uninitialized> [node_one_j5jqtj.start] Sending task 'script_runner.tasks.run'
2021-01-12 13:43:12.413  LOG <rollback_to_configured_and_uninitialized> [node_two_y7fcvt.create] INFO: Downloaded resources/install_fail.py to /tmp/M4Z9Y/install_fail.py
2021-01-12 13:43:12.414  LOG <rollback_to_configured_and_uninitialized> [node_two_y7fcvt.create] INFO: log and fail during install!
2021-01-12 13:43:12.651  LOG <rollback_to_configured_and_uninitialized> [node_one_j5jqtj.start] INFO: Downloaded resources/install_fail.py to /tmp/285JO/install_fail.py
2021-01-12 13:43:12.651  LOG <rollback_to_configured_and_uninitialized> [node_one_j5jqtj.start] INFO: log and fail during install!
2021-01-12 13:43:12.668  CFY <rollback_to_configured_and_uninitialized> [node_two_y7fcvt.create] Task failed 'script_runner.tasks.run'
Traceback (most recent call last):
  File "/opt/mgmtworker/env/lib64/python3.6/site-packages/cloudify/dispatch.py", line 793, in main
    payload = handler.handle()
  File "/opt/mgmtworker/env/lib64/python3.6/site-packages/cloudify/dispatch.py", line 456, in handle
    result = self._run_operation_func(ctx, kwargs)
  File "/opt/mgmtworker/env/lib64/python3.6/site-packages/cloudify/dispatch.py", line 509, in _run_operation_func
    return self.func(*self.args, **kwargs)
  File "/opt/mgmtworker/env/lib64/python3.6/site-packages/script_runner/tasks.py", line 80, in run
    script_result = process_execution(script_func, script_path, ctx, process)
  File "/opt/mgmtworker/env/lib64/python3.6/site-packages/script_runner/tasks.py", line 156, in process_execution
    script_func(script_path, ctx, process)
  File "/opt/mgmtworker/env/lib64/python3.6/site-packages/script_runner/tasks.py", line 323, in eval_script
    exec(compile(open(script_path).read(), script_path, 'exec'), eval_globals)
  File "/tmp/M4Z9Y/install_fail.py", line 4, in <module>
    raise Exception
Exception

2021-01-12 13:43:12.969  CFY <rollback_to_configured_and_uninitialized> [node_one_j5jqtj.start] Task failed 'script_runner.tasks.run'
Traceback (most recent call last):
  File "/opt/mgmtworker/env/lib64/python3.6/site-packages/cloudify/dispatch.py", line 793, in main
    payload = handler.handle()
  File "/opt/mgmtworker/env/lib64/python3.6/site-packages/cloudify/dispatch.py", line 456, in handle
    result = self._run_operation_func(ctx, kwargs)
  File "/opt/mgmtworker/env/lib64/python3.6/site-packages/cloudify/dispatch.py", line 509, in _run_operation_func
    return self.func(*self.args, **kwargs)
  File "/opt/mgmtworker/env/lib64/python3.6/site-packages/script_runner/tasks.py", line 80, in run
    script_result = process_execution(script_func, script_path, ctx, process)
  File "/opt/mgmtworker/env/lib64/python3.6/site-packages/script_runner/tasks.py", line 156, in process_execution
    script_func(script_path, ctx, process)
  File "/opt/mgmtworker/env/lib64/python3.6/site-packages/script_runner/tasks.py", line 323, in eval_script
    exec(compile(open(script_path).read(), script_path, 'exec'), eval_globals)
  File "/tmp/285JO/install_fail.py", line 4, in <module>
    raise Exception
Exception

```
Cancel the `install` workflow (or wait until it will fail).

Check node instances states:

```shell
[root@9fbb5f2b0d4b offcial_examples]# cfy node-instances list
Listing all instances...

Node-instances:
+-------------------+------------------------------------------+---------+------------+----------+------------+----------------+------------+
|         id        |              deployment_id               | host_id |  node_id   |  state   | visibility |  tenant_name   | created_by |
+-------------------+------------------------------------------+---------+------------+----------+------------+----------------+------------+
|  node_one_j5jqtj  | rollback_to_configured_and_uninitialized |         |  node_one  | starting |   tenant   | default_tenant |   admin    |
| node_three_tmjr2n | rollback_to_configured_and_uninitialized |         | node_three | started  |   tenant   | default_tenant |   admin    |
|  node_two_y7fcvt  | rollback_to_configured_and_uninitialized |         |  node_two  | creating |   tenant   | default_tenant |   admin    |
+-------------------+------------------------------------------+---------+------------+----------+------------+----------------+------------+

Showing 3 of 3 node-instances

```

See that `node_one_j5jqtj` state is `starting` and  `node_two_y7fcvt` state is `creating`.

#### Run rollback workflow

```shell
[root@9fbb5f2b0d4b offcial_examples]# cfy executions start rollback -d rollback_to_configured_and_uninitialized
Executing workflow `rollback` on deployment `rollback_to_configured_and_uninitialized` [timeout=900 seconds]
2021-01-12 14:31:03.130  LOG <rollback_to_configured_and_uninitialized> INFO: Installing managed plugin: 1f11c61f-1771-4096-9745-685c211b2683 [package_name: cloudify-utilities-plugin, package_version: 1.24.0, supported_platform: linux_x86_64, distribution: centos, distribution_release: core]
2021-01-12 14:31:05.604  CFY <rollback_to_configured_and_uninitialized> Starting 'rollback' workflow execution
2021-01-12 14:31:05.723  CFY <rollback_to_configured_and_uninitialized> [node_two_y7fcvt] Validating node instance after deletion: nothing to do
2021-01-12 14:31:05.747  CFY <rollback_to_configured_and_uninitialized> [node_one_j5jqtj] Stopping node instance
2021-01-12 14:31:05.749  CFY <rollback_to_configured_and_uninitialized> [node_two_y7fcvt] Rollback Stop: nothing to do, instance state is creating
2021-01-12 14:31:05.752  CFY <rollback_to_configured_and_uninitialized> [node_two_y7fcvt] Deleting node instance
2021-01-12 14:31:06.006  CFY <rollback_to_configured_and_uninitialized> [node_two_y7fcvt.delete] Sending task 'script_runner.tasks.run'
2021-01-12 14:31:06.108  CFY <rollback_to_configured_and_uninitialized> [node_one_j5jqtj] Validating node instance after deletion: nothing to do
2021-01-12 14:31:06.297  CFY <rollback_to_configured_and_uninitialized> [node_one_j5jqtj.stop] Sending task 'script_runner.tasks.run'
2021-01-12 14:31:06.607  LOG <rollback_to_configured_and_uninitialized> [node_two_y7fcvt.delete] INFO: Downloaded resources/uninstall_fail.py to /tmp/922GU/uninstall_fail.py
2021-01-12 14:31:06.608  LOG <rollback_to_configured_and_uninitialized> [node_two_y7fcvt.delete] INFO: log and fail during uninstall!
2021-01-12 14:31:06.826  CFY <rollback_to_configured_and_uninitialized> [node_two_y7fcvt.delete] Task failed 'script_runner.tasks.run'
Traceback (most recent call last):
  File "/opt/mgmtworker/env/lib64/python3.6/site-packages/cloudify/dispatch.py", line 793, in main
    payload = handler.handle()
  File "/opt/mgmtworker/env/lib64/python3.6/site-packages/cloudify/dispatch.py", line 456, in handle
    result = self._run_operation_func(ctx, kwargs)
  File "/opt/mgmtworker/env/lib64/python3.6/site-packages/cloudify/dispatch.py", line 509, in _run_operation_func
    return self.func(*self.args, **kwargs)
  File "/opt/mgmtworker/env/lib64/python3.6/site-packages/script_runner/tasks.py", line 80, in run
    script_result = process_execution(script_func, script_path, ctx, process)
  File "/opt/mgmtworker/env/lib64/python3.6/site-packages/script_runner/tasks.py", line 156, in process_execution
    script_func(script_path, ctx, process)
  File "/opt/mgmtworker/env/lib64/python3.6/site-packages/script_runner/tasks.py", line 323, in eval_script
    exec(compile(open(script_path).read(), script_path, 'exec'), eval_globals)
  File "/tmp/922GU/uninstall_fail.py", line 4, in <module>
    raise Exception
Exception

2021-01-12 14:31:06.826  CFY <rollback_to_configured_and_uninitialized> [node_two_y7fcvt] Ignoring task script_runner.tasks.run failure
2021-01-12 14:31:06.844  LOG <rollback_to_configured_and_uninitialized> [node_one_j5jqtj.stop] INFO: Downloaded resources/uninstall_fail.py to /tmp/U1DMY/uninstall_fail.py
2021-01-12 14:31:06.845  LOG <rollback_to_configured_and_uninitialized> [node_one_j5jqtj.stop] INFO: log and fail during uninstall!
2021-01-12 14:31:06.875  CFY <rollback_to_configured_and_uninitialized> [node_two_y7fcvt] Rollbacked node instance
2021-01-12 14:31:07.119  CFY <rollback_to_configured_and_uninitialized> [node_one_j5jqtj.stop] Task failed 'script_runner.tasks.run'
Traceback (most recent call last):
  File "/opt/mgmtworker/env/lib64/python3.6/site-packages/cloudify/dispatch.py", line 793, in main
    payload = handler.handle()
  File "/opt/mgmtworker/env/lib64/python3.6/site-packages/cloudify/dispatch.py", line 456, in handle
    result = self._run_operation_func(ctx, kwargs)
  File "/opt/mgmtworker/env/lib64/python3.6/site-packages/cloudify/dispatch.py", line 509, in _run_operation_func
    return self.func(*self.args, **kwargs)
  File "/opt/mgmtworker/env/lib64/python3.6/site-packages/script_runner/tasks.py", line 80, in run
    script_result = process_execution(script_func, script_path, ctx, process)
  File "/opt/mgmtworker/env/lib64/python3.6/site-packages/script_runner/tasks.py", line 156, in process_execution
    script_func(script_path, ctx, process)
  File "/opt/mgmtworker/env/lib64/python3.6/site-packages/script_runner/tasks.py", line 323, in eval_script
    exec(compile(open(script_path).read(), script_path, 'exec'), eval_globals)
  File "/tmp/U1DMY/uninstall_fail.py", line 4, in <module>
    raise Exception
Exception

2021-01-12 14:31:07.119  CFY <rollback_to_configured_and_uninitialized> [node_one_j5jqtj] Ignoring task script_runner.tasks.run failure
2021-01-12 14:31:07.119  CFY <rollback_to_configured_and_uninitialized> [node_one_j5jqtj] Stopped node instance
2021-01-12 14:31:07.170  CFY <rollback_to_configured_and_uninitialized> [node_one_j5jqtj] Rollback Delete: nothing to do, instance state is starting
2021-01-12 14:31:07.171  CFY <rollback_to_configured_and_uninitialized> [node_one_j5jqtj] Rollbacked node instance
2021-01-12 14:31:07.256  CFY <rollback_to_configured_and_uninitialized> 'rollback' workflow execution succeeded
Finished executing workflow rollback on deployment rollback_to_configured_and_uninitialized
* Run 'cfy events list 2296d271-f26f-47b9-94be-c5b0333bf538' to retrieve the execution's events/logs

```
See that even though `node_one_j5jqtj.stop` and `node_two_y7fcvt.delete` still the rollback succeeded (ignore failures during rollback as explained above).

Check node instances states:

```shell
[root@9fbb5f2b0d4b offcial_examples]# cfy node-instances list
Listing all instances...

Node-instances:
+-------------------+------------------------------------------+---------+------------+---------------+------------+----------------+------------+
|         id        |              deployment_id               | host_id |  node_id   |     state     | visibility |  tenant_name   | created_by |
+-------------------+------------------------------------------+---------+------------+---------------+------------+----------------+------------+
|  node_one_j5jqtj  | rollback_to_configured_and_uninitialized |         |  node_one  |   configured  |   tenant   | default_tenant |   admin    |
| node_three_tmjr2n | rollback_to_configured_and_uninitialized |         | node_three |    started    |   tenant   | default_tenant |   admin    |
|  node_two_y7fcvt  | rollback_to_configured_and_uninitialized |         |  node_two  | uninitialized |   tenant   | default_tenant |   admin    |
+-------------------+------------------------------------------+---------+------------+---------------+------------+----------------+------------+

Showing 3 of 3 node-instances

```
See that rollback handled unresolved node instances. 

### Wrapper workflows

Nine workflows introduced:
* alt_start.
* alt_stop.
* alt_precreate.
* alt_create.
* alt_configure.
* alt_poststart.
* alt_prestop.
* alt_delete.
* alt_postdelete.

Wrapper workflows are workflows that wrap execution of the corresponding lifecycle operation with `ignore_failure` option.

For example, `alt_create` workflow will execute `cloudify.interfaces.lifecycle.create`.

All the wrapper workflows share the same parameters:
* `operation_parms`: A dictionary of keyword arguments that will be passed to
  the operation invocation (Default: {}).
* `run_by_dependency_order`: A boolean describing whether the operation should
  execute on the relevant nodes according to the order of their relationships
  dependencies or rather execute on all relevant nodes in parallel (Default: true).
* `type_names`: A list of type names. The operation will be executed only on node
  instances which are of these types or of types which (recursively)
  derive from them. An empty list means no filtering will take place
  and all type names are valid (Default: []).
* `node_ids`: A list of node ids. The operation will be executed only on node
  instances which are instances of these nodes. An empty list means
  no filtering will take place and all nodes are valid (Default: []).
* `node_instance_ids`: A list of node instance ids. The operation will be 
  executed only on the node instances specified. An empty list means no 
  filtering will take place and all node instances are valid (Default: []).
* `ignore_failure`: Whether to ignore failure during execution of the operation.

