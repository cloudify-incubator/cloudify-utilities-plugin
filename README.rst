========
Overview
========

The deployment proxy plugin connects two deployments in order to allow deployment coordination.
The source blueprint that wishes to depend on another blueprint,
for example a web tier that wants to depend on a database, includes the cloudify.nodes.
DeploymentProxy node in the blueprint and creates a depends-on or other relationship with it.
The DeploymentProxy node waits until deployment will be in terminated state.

===============
Node properties
===============

The DeploymentProxy node itself has the following properties that govern it's behavior::

    - deployment_id          : the deployment to depend on
    - inherit_outputs        : a list of outputs that are should be inherited from depployment proxy outputs.
                               Default: empty list.
    - inherit_inputs         : Flag that indicated if it is necessary to inherit deployment inputs
    - timeout                : number of seconds to wait.  When timeout expires, a "RecoverableError" is thrown.
                               Default=30.

The BlueprintDeployment node has the following properties::

    - blueprint_id                : blueprint ID to create deployment from
    - inputs                      : inputs for the deployment
    - ignore_live_nodes_on_delete : ignore live nodes during deletion for a deployment

How it works? Let's take a look at multi-part Nodecellar blueprint nodes::

  mongodb_host_deployment:
    type: cloudify.nodes.BlueprintDeployment
    properties:
      blueprint_id: { get_input: mongodb_host_blueprint_id }
      inputs:
        vcloud_username: { get_input: vcloud_username }
        vcloud_password: { get_input: vcloud_password }
        vcloud_token: { get_input: vcloud_token }
        vcloud_url: { get_input: vcloud_url }
        vcloud_service: { get_input: vcloud_service }
        vcloud_service_type: { get_input: vcloud_service_type }
        vcloud_instance: { get_input: vcloud_instance }
        vcloud_api_version: { get_input: vcloud_api_version }
        mongo_ssh: { get_input: mongo_ssh }
        vcloud_org_url: { get_input: vcloud_org_url }
        vcloud_org: { get_input: vcloud_org }
        vcloud_vdc: { get_input: vcloud_vdc }
        catalog: { get_input: catalog}
        template: { get_input: template }
        server_cpu: { get_input: server_cpu }
        server_memory: { get_input: server_memory }
        network_use_existing: { get_input: network_use_existing }
        common_network_name: { get_input: common_network_name }
        mongo_ip_address: { get_input: mongo_ip_address }
        common_network_public_nat_use_existing: { get_input: common_network_public_nat_use_existing }
        edge_gateway: { get_input: edge_gateway }
        server_user: { get_input: server_user }
        user_public_key: { get_input: user_public_key }
        user_private_key: { get_input: user_private_key }

This node has specific implementation of the lifecycle::

    On create: Creates a deployment with given inputs
    On start: Installs a deployment
    On stop: Uninstalls a deployment
    On delete: Deletes a deployment

Given node has runtime property::

    deployment_id

it represents a deployment id of newly create deployment instance inside Cloudify.

Next node consumes that deployment id as an input for next blueprint deployment::

 mongodb_application_deployment:
    type: cloudify.nodes.BlueprintDeployment
    properties:
      blueprint_id: { get_input: mongodb_application_blueprint_id }
    cloudify.interfaces.lifecycle:
      create:
        inputs:
          deployment_inputs:
            mongodb_host_deployment_id: { get_attribute: [ mongodb_host_deployment, deployment_id ]}
    relationships:
      - target: mongodb_host_deployment
        type: cloudify.relationships.depends_on

In given case it was decided to split VM and networking provisioning into one blueprint with defined outputs.
Next blueprint describes software installation within Fabric plugin.

=============
Usage example
=============

First of all please take a look at samples folder to see blueprints examples.
In most cases it is necessary to get deployment outputs in runtime during installing another deployment.
In case of Nodecellar example, as user i want to attach MongoDB to NodeJS application, MongoDB is available within other deployment.
As user i'd like to chain deployments within proxy pattern - define a deployment proxy node template and consume its attributes within blueprint.
Here's how proxy object looks like::

    mongodb_proxy_deployment:
        type: cloudify.nodes.DeploymentProxy
        properties:
           deployment_id: { get_input: mongodb_deployment_id }
           inherit_inputs: True
           inherit_outputs:
                - 'mongodb_internal_ip'
                - 'mongodb_public_ip'


Within NodeJS example blueprint composers are able to access proxy deployment attributes
within TOSCA functions in the next manner::

    MONGO_HOST: { get_attribute: [ mongodb_proxy_deployment, mongodb_internal_ip ] }

If it is necessary to access proxy deployment outputs it is possible to do in the next manner::

    network_name: { get_attribute: [ mongodb_proxy_deployment, proxy_deployment_inputs, common_network_name ] }



NOTE!! get_property function of TOSCA doesn't work with node properties.

==========
Disclaimer
==========

Tested on::

    Cloudify 3.2.1


Available blueprints::

    vCloud Air Nodecellar multi-blueprint application

Operating system::

    Given code OS-agnostic

==========================================
How to run multi-part Nodecellar blueprint
==========================================

In order to test multi-part blueprint deployment you have to execute next operations::

    upload blueprint vcloud-mongodb-host-nodecellar-multipart-blueprint.yaml
    upload blueprint vcloud-mongodb-application-nodecellar-multipart-blueprint.yaml
    upload blueprint vcloud-nodejs-host-nodecellar-multipart-blueprint.yaml
    upload blueprint vcloud-nodejs-application-nodecellar-multipart-blueprint.yaml
    upload blueprint vcloud-nodecellar-multipart-blueprint.yaml
    create a deployment for blueprint vcloud-nodecellar-multipart-blueprint.yaml
    run installation for deployment of the blueprint vcloud-nodecellar-multipart-blueprint.yaml

