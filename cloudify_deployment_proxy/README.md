# Cloudify Deployment Proxy

This plugin enables a user to connect a deployment to another deployment, in effect enabling "chains" of applications or service.


### Notes

- Previously published as "Cloudify Proxy Plugin", the usage of which is deprecated.
- A Cloudify Manager is required.
- Tested with Cloudify Manager 4.0.
- Nodecellar Example blueprint requires AWS + VPC. (No provider context.)
- Nodecellar Example blueprint requires that AWS credentials are stored as secrets on the manager.

## Examples:

- [Basic Example](#basic-example-instructions)
- [Nodecellar Example](#nodecellar-example-instructions)


## Basic Example Instructions

This basic example covers a trivial scenario:
- Create a "step1" deployment that sets some data.
- Create a "step2" deployment that consumes the data.

1. Install Step 1:

```shell
$ cfy install cloudify_deployment_proxy/examples/simple/step-1-blueprint.yaml
Uploading blueprint cloudify_deployment_proxy/examples/simple/step-1-blueprint.yaml...
 step-1-blueprint.... |################################################| 100.0%
Blueprint uploaded. The blueprint's id is simple
Creating new deployment from blueprint simple...
Deployment created. The deployment's id is simple
Executing workflow install on deployment simple [timeout=900 seconds]
Deployment environment creation is in progress...
2017-04-20 20:25:05.457  CFY <simple> Starting 'create_deployment_environment' workflow execution
...
2017-04-20 20:25:11.165  CFY <simple> Starting 'install' workflow execution
...
2017-04-20 20:25:15.218  CFY <simple> 'install' workflow execution succeeded
Finished executing workflow install on deployment simple
$ cfy deployments outputs simple
Retrieving outputs for deployment simple...
 - "environment":
     Description: The environment data.
     Value: ABCD01234
 - "application":
     Description: The application info.
     Value: 0:1:2:3:4
```

Notice the output data.


2. Install Step 2:

```shell
$ cfy install cloudify_deployment_proxy/examples/simple/step-2-blueprint.yaml -b simple2
Uploading blueprint cloudify_deployment_proxy/examples/simple/step-2-blueprint.yaml...
 step-2-blueprint.... |################################################| 100.0%
Blueprint uploaded. The blueprint's id is simple2
Creating new deployment from blueprint simple2...
Deployment created. The deployment's id is simple2
Executing workflow install on deployment simple2 [timeout=900 seconds]
Deployment environment creation is pending...
2017-04-20 20:26:26.007  CFY <simple2> Starting 'create_deployment_environment' workflow execution
...
2017-04-20 20:26:35.831  CFY <simple2> Starting 'install' workflow execution
...
2017-04-20 20:26:39.992  CFY <simple2> 'install' workflow execution succeeded
$ cfy deployments outputs simple2
Retrieving outputs for deployment simple2...
 - "environment":
     Description: The environment data.
     Value: ABCD01234
 - "application":
     Description: The application info.
     Value: 0:1:2:3:4
```

Notice that the deployment "simple2" has copied the "simple" deployment output data.

3. Uninstall Step 2:

```shell
$ cfy uninstall simple2
Executing workflow uninstall on deployment simple2 [timeout=900 seconds]
2017-04-20 20:27:03.381  CFY <simple2> Starting 'uninstall' workflow execution
...
2017-04-20 20:27:05.261  CFY <simple2> 'uninstall' workflow execution succeeded
Finished executing workflow uninstall on deployment simple2
```


4. Uninstall Step 1:

```shell
$ cfy uninstall simple
Executing workflow uninstall on deployment simple [timeout=900 seconds]
2017-04-20 20:27:46.701  CFY <simple> Starting 'uninstall' workflow execution
...
2017-04-20 20:27:48.327  CFY <simple> 'uninstall' workflow execution succeeded
Finished executing workflow uninstall on deployment simple
```


## Nodecellar Example Instructions

This example follows the [standard manager setup pattern](https://github.com/EarthmanT/installing-cloudify-4.0-manager).

The example demonstrates the following simple example:

- Install blueprint A.
- Blueprint A brings up a VM in the management environment and installs database on the VM.
- Leave the deployment running and install blueprint B.
- Blueprint B brings up another VM that "proxies" the previous deployment and installs a web application that uses the database.


#### AWS

1. Copy the example inputs file and edit it:

```shell
$ cp cloudify-utilities-plugin/cloudify_deployment_proxy/examples/nodecellar/inputs/aws.yaml.example inputs.yaml
```

Make sure the variables match those of the Cloudify Manager 4.0 AWS environment.


2. Install the MongoDB deployment:

```shell
$ cfy install cloudify-utilities-plugin/cloudify_deployment_proxy/examples/nodecellar/aws-mongo-blueprint.yaml -b mongo1 -i inputs.yaml
Uploading blueprint cloudify-utilities-plugin/cloudify_deployment_proxy/examples/nodecellar/aws-mongo-blueprint.yaml...
 aws-mongo-bluepri... |################################################| 100.0%
Blueprint uploaded. The blueprint's id is mongo1
Creating new deployment from blueprint mongo1...
Deployment created. The deployment's id is mongo1
Executing workflow install on deployment mongo1 [timeout=900 seconds]
Deployment environment creation is pending...
2017-04-20 00:00:00.000  CFY <mongo1> Starting 'create_deployment_environment' workflow execution
...
2017-04-20 00:00:00.000  CFY <mongo1> Starting 'install' workflow execution
...
2017-04-20 00:00:00.000  CFY <mongo1> 'install' workflow execution succeeded
Finished executing workflow install on deployment mongo1
```

This installed a MongoDB on a VM.


3. Install the Nodecellar deployment:

```shell
$ cfy install cloudify-utilities-plugin/cloudify_deployment_proxy/examples/nodecellar/aws-proxy-blueprint.yaml \
    -i inputs.yaml -b node1 -i "mongod_host_deployment_id=mongo1"
Uploading blueprint cloudify-utilities-plugin/cloudify_deployment_proxy/examples/nodecellar/aws-proxy-blueprint.yaml...
 aws-proxy-bluepri... |################################################| 100.0%
Blueprint uploaded. The blueprint's id is node1
Creating new deployment from blueprint node1...
Deployment created. The deployment's id is node1
Executing workflow install on deployment node1 [timeout=900 seconds]
Deployment environment creation is pending...
2017-04-20 00:00:00.000  CFY <node1> Starting 'create_deployment_environment' workflow execution
...
2017-04-20 00:00:00.000  CFY <node1> Starting 'install' workflow execution
...
2017-04-20 00:00:00.000  CFY <node1> 'install' workflow execution succeeded
Finished executing workflow install on deployment node1
```

This installed the Nodecellar web application and connected it to the database from the first deployment.


4. Check the deployment outputs for the application endpoint:

```shell
$ cfy deployments outputs node1
Retrieving outputs for deployment node1...
 - "endpoint":
     Description: Application UI
     Value: http://123.45.67.89:8080
```

5. At this point, try installing another web application deployment like in step 3 and 4.

*Hint: You will need to change the ```nodejs_host_key_name``` and ```nodejs_host_private_key_path``` input values since these will conflict with the step 3 deployment.**


6. Uninstall the Nodecellar deployment:

```shell
$ cfy install node1 --allow-custom-parameters -p ignore_failure=true
2017-04-20 00:00:00.000  CFY <node1> Starting 'uninstall' workflow execution
...
2017-04-20 00:00:00.000  CFY <node1> 'uninstall' workflow execution succeeded
```


7. Uninstall the Mongo deployment:

```shell
$ cfy install node1 --allow-custom-parameters -p ignore_failure=true
2017-04-20 00:00:00.000  CFY <mongo1> Starting 'uninstall' workflow execution
...
2017-04-20 00:00:00.000  CFY <mongo1> 'uninstall' workflow execution succeeded
```
