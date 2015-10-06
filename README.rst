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
    - timeout                : number of seconds to wait.  When timeout expires, a "RecoverableError" is thrown.
                               Default=30.

