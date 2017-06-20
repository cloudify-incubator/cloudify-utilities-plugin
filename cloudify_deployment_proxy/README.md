# Cloudify Utilities: Deployment Proxy

This plugin enables a user to connect a deployment to another deployment, in effect enabling "chains" of applications or service.


### Notes

- Previously published as "Cloudify Proxy Plugin".
- A Cloudify Manager is required.
- Tested with Cloudify Manager 4.0.

## Examples:

- [Deployment Proxy Example](examples/test/deployment-proxy.yaml)
- [Node Instance Proxy Example](examples/test/node-instance-proxy.yaml)
- [etcd Cluster Example](https://github.com/cloudify-examples/deployment-proxy-blueprint)


## Test Example Instructions

The simple example is pretty trivial. It is meant to validate that the plugin is operational. It uploads a simple blueprint to the manager, creates a deployment, and installs that deployment. It then installs a new blueprint that uses the outputs of that deployment.


*Upload the plugin wagon to your manager:*

Plugins are packaged as wagons that include all of the dependencies of a particular plugin.

```shell
$ cfy plugins upload https://github.com/cloudify-incubator/cloudify-utilities-plugin/releases/download/[version]/cloudify_utilities_plugin-[version]-py27-none-linux_x86_64.1.wgn
```


*Install the test blueprint:*

```shell
$ cfy install https://github.com/cloudify-incubator/cloudify-utilities-plugin/archive/[version].zip -n cloudify_deployment_proxy/examples/test/deployment-proxy.yaml -b demo
```

You should see an output like this:

```shell
Uploading blueprint cloudify_deployment_proxy/examples/test/deployment-proxy.yaml...
blueprint.yaml |######################################################| 100.0%
Blueprint uploaded. The blueprint's id is test
Creating new deployment from blueprint test...
Deployment created. The deployment's id is test
Executing workflow install on deployment test [timeout=900 seconds]
Deployment environment creation is pending...
2017-04-26 11:23:44.500  CFY <test> Starting 'create_deployment_environment' workflow execution
2017-04-26 11:23:45.020  LOG <test> [,] INFO: Installing plugin: cfy_util
2017-04-26 11:23:44.923  CFY <test> [,] Sending task 'cloudify_agent.operations.install_plugins'
2017-04-26 11:23:44.965  CFY <test> [,] Task started 'cloudify_agent.operations.install_plugins'
2017-04-26 11:23:45.020  LOG <test> [,] INFO: Installing plugin: cfy_util
2017-04-26 11:23:45.614  LOG <test> [,] INFO: Installing plugin from source
2017-04-26 11:23:48.925  CFY <test> [,] Task succeeded 'cloudify_agent.operations.install_plugins'
2017-04-26 11:23:49.077  CFY <test> Skipping starting deployment policy engine core - no policies defined
2017-04-26 11:23:49.281  CFY <test> Creating deployment work directory
2017-04-26 11:23:49.615  CFY <test> 'create_deployment_environment' workflow execution succeeded
2017-04-26 11:23:53.503  CFY <test> Starting 'install' workflow execution
2017-04-26 11:23:54.151  CFY <test> [bp_dep_2fltcd] Creating node
2017-04-26 11:23:54.252  CFY <test> [bp_dep_2fltcd.create] Sending task 'cloudify_deployment_proxy.tasks.upload_blueprint'
2017-04-26 11:23:54.296  CFY <test> [bp_dep_2fltcd.create] Task started 'cloudify_deployment_proxy.tasks.upload_blueprint'
2017-04-26 11:23:56.379  CFY <test> [bp_dep_2fltcd.create] Task succeeded 'cloudify_deployment_proxy.tasks.upload_blueprint ('True')'
2017-04-26 11:23:56.815  CFY <test> [bp_dep_2fltcd] Configuring node
2017-04-26 11:23:56.994  CFY <test> [bp_dep_2fltcd.configure] Sending task 'cloudify_deployment_proxy.tasks.create_deployment'
2017-04-26 11:23:57.012  CFY <test> [bp_dep_2fltcd.configure] Task started 'cloudify_deployment_proxy.tasks.create_deployment'
2017-04-26 11:24:08.238  CFY <test> [bp_dep_2fltcd.configure] Task succeeded 'cloudify_deployment_proxy.tasks.create_deployment ('True')'
2017-04-26 11:24:08.782  CFY <test> [bp_dep_2fltcd] Starting node
2017-04-26 11:24:08.862  CFY <test> [bp_dep_2fltcd.start] Sending task 'cloudify_deployment_proxy.tasks.execute_start'
2017-04-26 11:24:08.879  CFY <test> [bp_dep_2fltcd.start] Task started 'cloudify_deployment_proxy.tasks.execute_start'
2017-04-26 11:24:19.947  CFY <test> [bp_dep_2fltcd.start] Task succeeded 'cloudify_deployment_proxy.tasks.execute_start ('True')'
2017-04-26 11:24:20.836  CFY <test> [dep_proxy_16u9kh] Creating node
2017-04-26 11:24:20.919  CFY <test> [dep_proxy_16u9kh.create] Sending task 'cloudify_deployment_proxy.tasks.wait_for_deployment_ready'
2017-04-26 11:24:20.938  CFY <test> [dep_proxy_16u9kh.create] Task started 'cloudify_deployment_proxy.tasks.wait_for_deployment_ready'
2017-04-26 11:24:21.780  CFY <test> [dep_proxy_16u9kh.create] Task succeeded 'cloudify_deployment_proxy.tasks.wait_for_deployment_ready ('True')'
2017-04-26 11:24:22.356  CFY <test> [dep_proxy_16u9kh] Configuring node
2017-04-26 11:24:22.941  CFY <test> [dep_proxy_16u9kh] Starting node
2017-04-26 11:24:23.039  CFY <test> [dep_proxy_16u9kh.start] Sending task 'cloudify_deployment_proxy.tasks.query_deployment_data'
2017-04-26 11:24:23.057  CFY <test> [dep_proxy_16u9kh.start] Task started 'cloudify_deployment_proxy.tasks.query_deployment_data'
2017-04-26 11:24:23.897  CFY <test> [dep_proxy_16u9kh.start] Task succeeded 'cloudify_deployment_proxy.tasks.query_deployment_data ('True')'
2017-04-26 11:24:24.523  CFY <test> 'install' workflow execution succeeded
Finished executing workflow install on deployment test
```

*Uninstall the blueprint:*

```shell
$ cfy uninstall test
```

You should see an output like this:

```shell
Executing workflow uninstall on deployment test [timeout=900 seconds]
2017-04-26 11:24:35.537  CFY <test> Starting 'uninstall' workflow execution
2017-04-26 11:24:36.076  CFY <test> [dep_proxy_16u9kh] Stopping node
2017-04-26 11:24:36.981  CFY <test> [dep_proxy_16u9kh] Deleting node
2017-04-26 11:24:37.585  CFY <test> [bp_dep_2fltcd] Stopping node
2017-04-26 11:24:37.789  CFY <test> [bp_dep_2fltcd.stop] Sending task 'cloudify_deployment_proxy.tasks.execute_start'
2017-04-26 11:24:37.827  CFY <test> [bp_dep_2fltcd.stop] Task started 'cloudify_deployment_proxy.tasks.execute_start'
2017-04-26 11:24:48.996  CFY <test> [bp_dep_2fltcd.stop] Task succeeded 'cloudify_deployment_proxy.tasks.execute_start ('True')'
2017-04-26 11:24:49.562  CFY <test> [bp_dep_2fltcd] Deleting node
2017-04-26 11:24:49.660  CFY <test> [bp_dep_2fltcd.delete] Sending task 'cloudify_deployment_proxy.tasks.delete_deployment'
2017-04-26 11:24:49.678  CFY <test> [bp_dep_2fltcd.delete] Task started 'cloudify_deployment_proxy.tasks.delete_deployment'
2017-04-26 11:24:50.953  CFY <test> [bp_dep_2fltcd.delete] Task succeeded 'cloudify_deployment_proxy.tasks.delete_deployment ('True')'
```
