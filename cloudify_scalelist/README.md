# Cloudify Utilities: Scale List Workflow

## Description
Add support for scale several scalling group in one transaction.

## Supported workflows

Supported scale up list of instances.

### scaleuplist

Create new instances defined in `scalable_entity_properties` list.

Parameters:
* `scalable_entity_properties`: List properties for nodes.
* `scale_compute`: If a node name is passed as the `scalable_entity_name`
  parameter and that node is contained (transitively) within a compute node
  and this property is `true`, operate on the compute node instead of the
  specified node. Default: `false`
* `ignore_failure`: Default: `false`
* `scale_transaction_field`: Place to save transaction id created in same
  transaction. Default: _transaction_id
* `scale_transaction_value`: Optional, transaction value.

### scaledownlist

Remove all instances from same transaction as node selected by `scale_node_name`.

Parameters:
* `scale_compute`: If a node name is passed as the `scale_node_name` parameter
  and that node is contained (transitively) within a compute node and this
  property is `true`, operate on the compute node instead of the specified node.
  Default: false
* `ignore_failure`: Default: `false`
* `scale_transaction_field`: Place to save transaction id created in same transaction.
* `scale_node_name`: Node name where we need to search value.
* `scale_node_field`: Node runtime properties field name for search value.
* `scale_node_field_value`: Node runtime properties field value for search

## Examples

[Example](examples/blueprint.yaml) for show scaling several scaling group
within one transaction.

## Install with one "two" node

We install blueprint with one "two" nodes.
```shell
$ cfy install cloudify-utilities-plugin/cloudify_scalelist/examples/blueprint.yaml -b examples
Uploading blueprint cloudify-utilities-plugin/cloudify_scalelist/examples/blueprint.yaml...
 blueprint.yaml |######################################################| 100.0%
Blueprint uploaded. The blueprint's id is examples
Creating new deployment from blueprint examples...
Deployment created. The deployment's id is examples
Executing workflow install on deployment examples [timeout=900 seconds]
Deployment environment creation is pending...
2018-06-28 08:53:39.574  CFY <examples> Starting 'create_deployment_environment' workflow execution
....
2018-06-28 08:54:00.628  CFY <examples> [one_l1grdr] Starting node
2018-06-28 08:54:01.631  CFY <examples> [two_o9pie8] Creating node
2018-06-28 08:54:01.631  CFY <examples> [two_o9pie8.create] Sending task 'script_runner.tasks.run'
2018-06-28 08:54:01.631  CFY <examples> [two_o9pie8.create] Task started 'script_runner.tasks.run'
2018-06-28 08:54:02.102  LOG <examples> [two_o9pie8.create] INFO: Downloaded scripts/create.py to /tmp/6P025/tmp3Vdq18-create.py
2018-06-28 08:54:03.020  LOG <examples> [two_o9pie8.create] INFO: Resulted properties: {u'predefined': u'', 'ctx': <cloudify.context.CloudifyContext object at 0x299e390>, u'script_path': u'scripts/create.py', u'resource_name': u'two0', u'defined_in_inputs': u'one_l1grdr'}
2018-06-28 08:54:03.020  LOG <examples> [two_o9pie8.create] INFO: We will create: two_o9pie8
2018-06-28 08:54:02.634  CFY <examples> [two_o9pie8.create] Task succeeded 'script_runner.tasks.run'
2018-06-28 08:54:03.637  CFY <examples> [two_o9pie8] Configuring node
2018-06-28 08:54:03.637  CFY <examples> [two_o9pie8] Starting node
2018-06-28 08:54:04.640  CFY <examples> [three_9qa5bk] Creating node
....
2018-06-28 08:54:14.666  CFY <examples> 'install' workflow execution succeeded
Finished executing workflow install on deployment examples
* Run 'cfy events list -e e2a944f6-f9cd-47f9-bd5c-5b5abf659d28' to retrieve the execution's events/logs
```

Check properties:
```shell
$ cfy node-instances get two_o9pie8
Retrieving node instance two_o9pie8

Node-instance:
+------------+---------------+---------+---------+---------+------------+----------------+------------+
|     id     | deployment_id | host_id | node_id |  state  | visibility |  tenant_name   | created_by |
+------------+---------------+---------+---------+---------+------------+----------------+------------+
| two_o9pie8 |  examples     |         |   two   | started |   tenant   | default_tenant |   admin    |
+------------+---------------+---------+---------+---------+------------+----------------+------------+

Instance runtime properties:
    resource_name: two0
    resource_id: two_o9pie8
```

## Install two additional 'two' nodes

Run scale list up
```shell
$ cfy executions start scaleuplist -d examples -p cloudify-utilities-plugin/cloudify_scalelist/examples/scaleup_params.yaml
Executing workflow scaleuplist on deployment examples [timeout=900 seconds]
2018-06-28 08:57:18.665  CFY <examples> Starting 'scaleuplist' workflow execution
2018-06-28 08:57:18.792  LOG <examples> INFO: Scale rules: {u'two_scale': {'count': 2, 'values': [{u'resource_name': u'two1'}, {u'resource_name': u'two2'}]}, u'four_scale': {'count': 3, 'values': [{u'resource_name': u'four1'}, {u'resource_name': u'four2'}, {u'resource_name': u'four3'}, {}, {}, {}]}}
2018-06-28 08:57:19.117  LOG <examples> INFO: Scale up u'two_scale' by delta: 2
2018-06-28 08:57:19.117  LOG <examples> INFO: Scale up u'four_scale' by delta: 3
2018-06-28 08:57:19.117  LOG <examples> INFO: Scale settings: {u'two_scale': {'instances': 3}, u'four_scale': {'instances': 4}}
2018-06-28 08:57:20.125  LOG <examples> INFO: Deployment modification started. [modification_id=f780db47-4e62-4e1a-8e1a-2fe2eafd768e]
2018-06-28 08:57:20.125  LOG <examples> INFO: Added: [u'three_dp5lqe', u'six_noqlic', u'three_nke3bw', u'four_3p58dr', u'six_ur7kbn', u'six_ajtm98', u'two_8b38ld', u'four_iqzzpd', u'two_czdur0', u'four_s4gpws', u'three_flgd5b']
2018-06-28 08:57:20.125  LOG <examples> INFO: Update node: two_czdur0
...
2018-06-28 08:57:21.752  CFY <examples> [two_czdur0] Creating node
2018-06-28 08:57:21.752  CFY <examples> [two_8b38ld.create] Task started 'script_runner.tasks.run'
2018-06-28 08:57:21.752  CFY <examples> [two_czdur0.create] Sending task 'script_runner.tasks.run'
2018-06-28 08:57:21.752  CFY <examples> [two_czdur0.create] Task started 'script_runner.tasks.run'
2018-06-28 08:57:22.153  LOG <examples> [two_8b38ld.create] INFO: Downloaded scripts/create.py to /tmp/WUJ2P/tmpMBIkmb-create.py
2018-06-28 08:57:23.142  LOG <examples> [two_8b38ld.create] INFO: Resulted properties: {u'predefined': u'', u'resource_name': u'two1', u'defined_in_inputs': u'one_l1grdr', u'_transaction_id': u'f780db47-4e62-4e1a-8e1a-2fe2eafd768e', u'script_path': u'scripts/create.py', 'ctx': <cloudify.context.CloudifyContext object at 0x287e390>}
2018-06-28 08:57:23.142  LOG <examples> [two_8b38ld.create] INFO: We will create: two_8b38ld
2018-06-28 08:57:23.142  LOG <examples> [two_czdur0.create] INFO: Downloaded scripts/create.py to /tmp/KQB80/tmpOxzvb_-create.py
2018-06-28 08:57:22.800  CFY <examples> [two_8b38ld.create] Task succeeded 'script_runner.tasks.run'
2018-06-28 08:57:23.142  LOG <examples> [two_czdur0.create] INFO: Resulted properties: {u'predefined': u'', u'resource_name': u'two2', u'defined_in_inputs': u'one_l1grdr', u'_transaction_id': u'f780db47-4e62-4e1a-8e1a-2fe2eafd768e', u'script_path': u'scripts/create.py', 'ctx': <cloudify.context.CloudifyContext object at 0x2e2b390>}
2018-06-28 08:57:23.142  LOG <examples> [two_czdur0.create] INFO: We will create: two_czdur0
2018-06-28 08:57:22.800  CFY <examples> [two_czdur0.create] Task succeeded 'script_runner.tasks.run'
...
2018-06-28 08:57:37.073  CFY <examples> [six_ur7kbn] Starting node
2018-06-28 08:57:38.076  CFY <examples> 'scaleuplist' workflow execution succeeded
Finished executing workflow scaleuplist on deployment examples
* Run 'cfy events list -e 9264cf6d-8e35-4004-a6f2-d4664193d309' to retrieve the execution's events/logs
```

Check properties:
```shell
$ cfy node-instances get two_czdur0
Retrieving node instance two_czdur0

Node-instance:
+------------+---------------+---------+---------+---------+------------+----------------+------------+
|     id     | deployment_id | host_id | node_id |  state  | visibility |  tenant_name   | created_by |
+------------+---------------+---------+---------+---------+------------+----------------+------------+
| two_czdur0 |  examples     |         |   two   | started |   tenant   | default_tenant |   admin    |
+------------+---------------+---------+---------+---------+------------+----------------+------------+

Instance runtime properties:
    resource_name: two2
    _transaction_id: f780db47-4e62-4e1a-8e1a-2fe2eafd768e
    resource_id: two_czdur0
```

## Remove instances created with resource_name=two2

Run scale list down
```shell
$ cfy executions start scaledownlist -d examples -p cloudify-utilities-plugin/cloudify_scalelist/examples/scaledown_params.yaml
Executing workflow scaledownlist on deployment examples [timeout=900 seconds]
2018-06-28 09:01:50.215  CFY <examples> Starting 'scaledownlist' workflow execution
2018-06-28 09:01:50.325  LOG <examples> INFO: List instances: {u'four': [u'four_iqzzpd', u'four_s4gpws', u'four_3p58dr'], u'six': [u'six_ajtm98', u'six_ur7kbn', u'six_noqlic'], u'two': [u'two_czdur0', u'two_8b38ld'], u'three': [u'three_dp5lqe', u'three_flgd5b', u'three_nke3bw']}
2018-06-28 09:01:51.329  LOG <examples> INFO: Scale rules: {u'two_scale': {'count': 2, 'values': [u'two_czdur0', u'two_8b38ld']}, u'four_scale': {'count': 3, 'values': [u'four_iqzzpd', u'four_s4gpws', u'four_3p58dr', u'six_ajtm98', u'six_ur7kbn', u'six_noqlic', u'three_dp5lqe', u'three_flgd5b', u'three_nke3bw']}}
2018-06-28 09:01:51.329  LOG <examples> INFO: Scale down u'two_scale' by delta: 2
2018-06-28 09:01:51.329  LOG <examples> INFO: Scale down u'four_scale' by delta: 3
2018-06-28 09:01:51.329  LOG <examples> INFO: Scale settings: {u'two_scale': {'instances': 1, 'removed_ids_include_hint': [u'two_8b38ld', u'two_czdur0']}, u'four_scale': {'instances': 1, 'removed_ids_include_hint': [u'four_3p58dr', u'four_iqzzpd', u'four_s4gpws', u'six_ajtm98', u'six_noqlic', u'six_ur7kbn', u'three_dp5lqe', u'three_flgd5b', u'three_nke3bw']}}
2018-06-28 09:01:51.329  LOG <examples> INFO: Deployment modification started. [modification_id=652e1a2a-7257-46f5-835b-96b3ccb6bfd5]
2018-06-28 09:01:51.329  LOG <examples> INFO: Removed: [u'three_9qa5bk', u'three_dp5lqe', u'six_noqlic', u'six_lr0xnq', u'two_o9pie8', u'three_nke3bw', u'four_3p58dr', u'six_ajtm98', u'two_czdur0', u'four_s4gpws', u'four_3hn6yy']
2018-06-28 09:01:51.329  LOG <examples> INFO: Proposed: [u'six_ajtm98', u'six_ur7kbn', u'six_noqlic', u'two_czdur0', u'two_8b38ld', u'three_dp5lqe', u'three_flgd5b', u'three_nke3bw', u'four_iqzzpd', u'four_s4gpws', u'four_3p58dr']
2018-06-28 09:01:51.329  LOG <examples> WARNING: Rolling back deployment modification. [modification_id=652e1a2a-7257-46f5-835b-96b3ccb6bfd5]: Exception("Instance u'two_o9pie8' not in proposed list [u'six_ajtm98', u'six_ur7kbn', u'six_noqlic', u'two_czdur0', u'two_8b38ld', u'three_dp5lqe', u'three_flgd5b', u'three_nke3bw', u'four_iqzzpd', u'four_s4gpws', u'four_3p58dr'].",)
2018-06-28 09:01:51.329  LOG <examples> INFO: Scale down based on transaction failed: Exception("Instance u'two_o9pie8' not in proposed list [u'six_ajtm98', u'six_ur7kbn', u'six_noqlic', u'two_czdur0', u'two_8b38ld', u'three_dp5lqe', u'three_flgd5b', u'three_nke3bw', u'four_iqzzpd', u'four_s4gpws', u'four_3p58dr'].",)
2018-06-28 09:01:52.169  CFY <examples> [six_noqlic] Stopping node
...
2018-06-28 09:02:02.551  CFY <examples> [two_czdur0] Deleting node
2018-06-28 09:02:02.551  CFY <examples> [two_8b38ld.delete] Sending task 'script_runner.tasks.run'
2018-06-28 09:02:02.551  CFY <examples> [two_8b38ld.delete] Task started 'script_runner.tasks.run'
2018-06-28 09:02:02.551  CFY <examples> [two_czdur0.delete] Sending task 'script_runner.tasks.run'
2018-06-28 09:02:02.551  CFY <examples> [two_czdur0.delete] Task started 'script_runner.tasks.run'
2018-06-28 09:02:02.881  LOG <examples> [two_8b38ld.delete] INFO: Downloaded scripts/delete.py to /tmp/GTDH5/tmp3xUMS9-delete.py
2018-06-28 09:02:03.381  LOG <examples> [two_8b38ld.delete] INFO: We have some resource u'two_8b38ld', so we can delete such
2018-06-28 09:02:03.381  LOG <examples> [two_8b38ld.delete] INFO: Resulted properties: {u'predefined': u'', u'resource_name': u'two1', u'defined_in_inputs': u'one_l1grdr', u'resource_id': u'two_8b38ld', 'ctx': <cloudify.context.CloudifyContext object at 0x24a2390>, u'_transaction_id': u'f780db47-4e62-4e1a-8e1a-2fe2eafd768e', u'script_path': u'scripts/delete.py'}
2018-06-28 09:02:03.381  LOG <examples> [two_czdur0.delete] INFO: Downloaded scripts/delete.py to /tmp/BMGFZ/tmpnnINzq-delete.py
2018-06-28 09:02:03.553  CFY <examples> [two_8b38ld.delete] Task succeeded 'script_runner.tasks.run'
2018-06-28 09:02:03.381  LOG <examples> [two_czdur0.delete] INFO: We have some resource u'two_czdur0', so we can delete such
2018-06-28 09:02:03.381  LOG <examples> [two_czdur0.delete] INFO: Resulted properties: {u'predefined': u'', u'resource_name': u'two2', u'defined_in_inputs': u'one_l1grdr', u'resource_id': u'two_czdur0', 'ctx': <cloudify.context.CloudifyContext object at 0x3b0b390>, u'_transaction_id': u'f780db47-4e62-4e1a-8e1a-2fe2eafd768e', u'script_path': u'scripts/delete.py'}
2018-06-28 09:02:03.553  CFY <examples> [two_czdur0.delete] Task succeeded 'script_runner.tasks.run'
2018-06-28 09:02:04.386  LOG <examples> INFO: Cleanup node: six_ajtm98
```

State after clean up:
```shell
$ cfy node-instances get two_czdur0
Retrieving node instance two_czdur0

Node-instance:
+------------+---------------+---------+---------+---------------+------------+----------------+------------+
|     id     | deployment_id | host_id | node_id |     state     | visibility |  tenant_name   | created_by |
+------------+---------------+---------+---------+---------------+------------+----------------+------------+
| two_czdur0 |  examples     |         |   two   | uninitialized |   tenant   | default_tenant |   admin    |
+------------+---------------+---------+---------+---------------+------------+----------------+------------+

Instance runtime properties:
```

## Uninstall

Run uninstall instances:
```shell
$ cfy uninstall examples
Executing workflow uninstall on deployment examples [timeout=900 seconds]
2018-06-28 09:04:03.146  CFY <examples> Starting 'uninstall' workflow execution
2018-06-28 09:04:04.414  CFY <examples> [six_lr0xnq] Stopping node
...
2018-06-28 09:04:16.482  CFY <examples> [one_l1grdr] Stopping node
2018-06-28 09:04:16.607  LOG <examples> [two_o9pie8.delete] INFO: We have some resource u'two_o9pie8', so we can delete such
2018-06-28 09:04:16.607  LOG <examples> [two_czdur0.delete] INFO: Downloaded scripts/delete.py to /tmp/TKV05/tmpw8btoN-delete.py
2018-06-28 09:04:16.482  CFY <examples> [two_8b38ld.delete] Task succeeded 'script_runner.tasks.run'
2018-06-28 09:04:16.482  CFY <examples> [two_o9pie8.delete] Task succeeded 'script_runner.tasks.run'
2018-06-28 09:04:16.607  LOG <examples> [two_czdur0.delete] INFO: Resulted properties: {u'predefined': u'', 'ctx': <cloudify.context.CloudifyContext object at 0x271b390>, u'script_path': u'scripts/delete.py', u'resource_name': u'two0', u'defined_in_inputs': u'one_l1grdr'}
2018-06-28 09:04:16.607  LOG <examples> [two_czdur0.delete] INFO: Not fully created instances, skip it
2018-06-28 09:04:16.482  CFY <examples> [two_czdur0.delete] Task succeeded 'script_runner.tasks.run'
2018-06-28 09:04:16.482  CFY <examples> [one_l1grdr] Stopping node
...
2018-06-28 09:04:18.611  LOG <examples> [one_l1grdr.delete] INFO: We have some resource u'one_l1grdr', so we can delete such
2018-06-28 09:04:18.489  CFY <examples> [one_l1grdr.delete] Task succeeded 'script_runner.tasks.run'
2018-06-28 09:04:19.491  CFY <examples> 'uninstall' workflow execution succeeded
Finished executing workflow uninstall on deployment examples
```
