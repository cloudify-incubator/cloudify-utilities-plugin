# Cloudify Deployment Proxy

This plugin enables a user to connect a deployment to another deployment, in effect enabling "chains" of applications or service.


### Notes

- Previously published as "Cloudify Proxy Plugin", the usage of which is deprecated.
- A Cloudify Manager is required.
- Tested with Cloudify Manager 4.0.
- Example blueprint requires AWS + VPC. (No provider context.)
- Example blueprint requires that AWS credentials are stored as secrets on the manager.


## Example Instructions

This example follows the [standard manager setup pattern](https://github.com/EarthmanT/installing-cloudify-4.0-manager).

The example demonstrates the following simple example:

- Install blueprint A.
- Blueprint A brings up a VM in the management environment and installs database on the VM.
- Leave the deployment running and install blueprint B.
- Blueprint B brings up another VM that "proxies" the previous deployment and installs a web application that uses the database.


#### AWS

1. Copy the example inputs file and edit it:

```shell
$ cp examples/nodecellar/inputs/aws.yaml.example inputs.yaml
```

Make sure the variables match those of the Cloudify Manager 4.0 AWS environment.


2. Install the MongoDB deployment:

```shell
$ cfy install examples/nodecellar/aws-mongo-blueprint.yaml -b mongo1 -i inputs.yaml
Uploading blueprint examples/nodecellar/aws-mongo-blueprint.yaml...
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
$ cfy install examples/nodecellar/aws-proxy-blueprint.yaml \
    -i inputs.yaml -b node1 -i "mongod_host_deployment_id=mongo1"
Uploading blueprint examples/nodecellar/aws-proxy-blueprint.yaml...
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
