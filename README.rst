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

==========
Disclaimer
==========

Tested on::

    Cloudify 3.2.1


Available blueprints::

    vCloud Air Nodecellar multi-blueprint application

Operating system::

    Given code OS-agnostic

