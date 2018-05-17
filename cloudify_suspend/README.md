# Cloudify Utilities: Suspend
Additional suport for `suspend`, `resume`, `backup`, `restore`, `remove_backup`
workflows.

## Supported workflows

* `suspend`: Workflow call `cloudify.interfaces.freeze.suspend` for each node
  that has such operation. For backward compatibility also run deprecated
  `cloudify.interfaces.lifecycle.suspend`.
* `resume`: Workflow call `cloudify.interfaces.freeze.resume` for each node
  that has such operation. For backward compatibility also run deprecated
  `cloudify.interfaces.lifecycle.resume`.
* `backup`: Workflow call such calls for each node that has such operation.
  * `cloudify.interfaces.freeze.fs_finalize` for all **services** nodes,
  * `cloudify.interfaces.freeze.fs_finalize` for all **compute** nodes,
  * `cloudify.interfaces.snapshot.create` for all nodes in deployment,
  * `cloudify.interfaces.freeze.fs_finalize` for all **compute** nodes,
  * `cloudify.interfaces.freeze.fs_finalize` for all **services** nodes.
* `restore`:  Workflow call such calls for each node that have such operation.
  * `cloudify.interfaces.freeze.fs_finalize` for all **services** nodes,
  * `cloudify.interfaces.freeze.fs_finalize` for all **compute** nodes,
  * `cloudify.interfaces.snapshot.apply` for all nodes in deployment,
  * `cloudify.interfaces.freeze.fs_finalize` for all **compute** nodes,
  * `cloudify.interfaces.freeze.fs_finalize` for all **services** nodes.
* `remove_backup`:  Workflow call `cloudify.interfaces.snapshot.delete` for each
  node that has such operation.
* `statistics`:  Workflow call `cloudify.interfaces.statistics.perfomance` for each
  node that has such operation.

### Suspend/Resume support by plugins:

Plugin    | VM Suspend/Resume | File System freeze/unfreeze
--------- | ----------------- | ---------------------------
Openstack | Y                 | N (N/A)
LibVirt   | Y                 | N (N/A)


### VM Backup/Snapshot support by plugins:

Plugin    | VM Snapshot | VM Backup  | VM Snapshot Restore | VM Backup Restore | VM Snapshot Remove | VM Backup Remove
--------- | ----------- | -----------| ------------------- | ----------------- |------------------- | ----------------------
Openstack | Y           | Y          | Y                   | Y                 | Y                  | Y
LibVirt   | Y           | N (No API) | Y                   | N (No API)        | Y                  | N (No API)
vSphere   | Y           | N (No API) | Y                   | N (No API)        | Y                  | N (No API)

### Volume Backup/Snapshot support by plugins:

Plugin    | Volume Snapshot | Volume Backup | Volume Snapshot Restore | Volume Backup Restore | Volume Snapshot Remove | Volume Backup Remove
--------- | --------------- | ------------- | ----------------------- | --------------------- |----------------------- | --------------------
Openstack | Y               | Y             | N (No API)              | Y                     | Y                      | Y
LibVirt   | N (N/A)         | N (N/A)       | N (N/A)                 | N (N/A)               | N (N/A)                | N (N/A)
vSphere   | N (N/A)         | N (N/A)       | N (N/A)                 | N (N/A)               | N (N/A)                | N (N/A)

### Notes:

Abbreviations:
* N/A - Not supported by plugin
* Y - Supported by plugin
* N - Unsupported by infrastructure API

All workflows support `include_instances` for limit list of instances where we
call operations.

For partial backup can be used `include_instances` for limit list of instances or
split installation to several deployments and run on deployments one by one.

### Create backup/shapshot parameters

* `snapshot_name`: Backup name/tag. By default will be used "backup-<timestamp>"
* `snapshot_incremental`: Create incremental snapshots or full backup. By default created snapshots.
* `snapshot_type`: The backup type, like 'daily' or 'weekly'. By default: irregular
* `snapshot_rotation`: How many backups to keep around. By default: 1

# Usage example:

After upload [blueprint](examples/example.yaml) call 'suspend' workflow.

Suspend:

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

Create backup:

```shell
$ cfy executions start backup -b examples -p snapshot_name=backup_example --task-retry-interval 30
2018-05-16 12:10:22.408  CFY <examples> Starting 'backup' workflow execution
2018-05-16 12:10:22.413  CFY <examples> [example_node_s4bgna] Starting to cloudify.interfaces.freeze.fs_prepare
2018-05-16 12:10:22.413  CFY <examples> [qemu_vm_jvv6jt] Starting to cloudify.interfaces.snapshot.create
2018-05-16 12:10:22.413  CFY <examples> [example_node_s4bgna] Starting to cloudify.interfaces.freeze.fs_finalize
2018-05-16 12:10:22.512  CFY <examples> [example_node_s4bgna.fs_finalize] Sending task 'cloudify_terminal.tasks.run'
2018-05-16 12:10:22.512  CFY <examples> [qemu_vm_jvv6jt.create] Sending task 'cloudify_libvirt.domain_tasks.snapshot_create'
...
2018-05-16 12:10:47.604  CFY <examples> [example_node_s4bgna] Done cloudify.interfaces.freeze.fs_finalize
2018-05-16 12:10:47.604  CFY <examples> [qemu_vm_jvv6jt] Done cloudify.interfaces.snapshot.create
2018-05-16 12:10:47.681  CFY <examples> [example_node_s4bgna] Done cloudify.interfaces.freeze.fs_prepare
2018-05-16 12:10:47.767  LOG <examples> INFO: Backuped to u'backup_example'
2018-05-16 12:10:47.768  CFY <examples> 'backup' workflow execution succeeded
```

Restore backup:

```shell
$ cfy executions start restore -b examples -p snapshot_name=backup_example --task-retry-interval 30
2018-05-16 12:12:43.913  CFY <examples> Starting 'restore' workflow execution
2018-05-16 12:12:43.917  CFY <examples> [example_node_s4bgna] Starting to cloudify.interfaces.freeze.fs_finalize
2018-05-16 12:12:43.917  CFY <examples> [qemu_vm_jvv6jt] Starting to cloudify.interfaces.snapshot.apply
2018-05-16 12:12:43.917  CFY <examples> [example_node_s4bgna] Starting to cloudify.interfaces.freeze.fs_prepare
...
2018-05-16 12:13:13.114  CFY <examples> [example_node_s4bgna] Done cloudify.interfaces.freeze.fs_prepare
2018-05-16 12:13:13.229  CFY <examples> [example_node_s4bgna] Done cloudify.interfaces.freeze.fs_finalize
2018-05-16 12:13:13.314  LOG <examples> INFO: Restored from u'backup_example'
2018-05-16 12:13:13.314  CFY <examples> 'restore' workflow execution succeeded
```

Delete backup:

```shell
$ cfy executions start remove_backup -b examples -p snapshot_name=backup_example --task-retry-interval 30
2018-05-16 12:14:42.171  CFY <examples> Starting 'remove_backup' workflow execution
2018-05-16 12:14:42.174  CFY <examples> [qemu_vm_jvv6jt] Starting to cloudify.interfaces.snapshot.delete
2018-05-16 12:14:42.275  CFY <examples> [qemu_vm_jvv6jt.delete] Sending task 'cloudify_libvirt.domain_tasks.snapshot_delete'
2018-05-16 12:14:42.322  CFY <examples> [qemu_vm_jvv6jt.delete] Task started 'cloudify_libvirt.domain_tasks.snapshot_delete'
2018-05-16 12:14:42.364  LOG <examples> [qemu_vm_jvv6jt.delete] INFO: remove_backup
2018-05-16 12:14:42.429  LOG <examples> [qemu_vm_jvv6jt.delete] INFO: Backup deleted: vm-backup_example
2018-05-16 12:14:42.430  CFY <examples> [qemu_vm_jvv6jt.delete] Task succeeded 'cloudify_libvirt.domain_tasks.snapshot_delete'
2018-05-16 12:14:42.499  CFY <examples> [qemu_vm_jvv6jt] Done cloudify.interfaces.snapshot.delete
2018-05-16 12:14:42.578  LOG <examples> INFO: Removed u'backup_example'
2018-05-16 12:14:42.578  CFY <examples> 'remove_backup' workflow execution succeeded
```
