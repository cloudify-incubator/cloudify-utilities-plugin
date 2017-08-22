[![Build Status](https://circleci.com/gh/cloudify-incubator/cloudify-utilities-plugin.svg?style=shield&circle-token=:circle-token)](https://circleci.com/gh/cloudify-incubator/cloudify-utilities-plugin)

# Cloudify Utilities

Utilities for extending Cloudify features.


## Contents:

- [Cloudify Cloud-Init](cloudify_cloudinit/README.md)
- [Cloudify Deployment Proxy](cloudify_deployment_proxy/README.md)
- [Cloudify File](cloudify_files/README.md)
- [Cloudify SSH Key](cloudify_ssh_key/README.md)
- [Cloudify Configuration](cloudify_configuration/README.md)
- [Cloudify Terminal](cloudify_terminal/README.md)


## Versions:

  - v1.0.0: First stable version.
  - v1.1.0: Add Cloudify SHH Key Plugin. Combine BlueprintDeployment node type and DeploymentProxy node type.
  - v1.1.1: Fixed an issue where deployments may be re-installed.
  - v1.2.0: Add NodeInstanceProxy node type.
            Add cloudify rest client mock.
            Added more tests.
  - v1.2.1: Public Key Runtime Property.
  - v1.2.2: Add ability to store to runtime properties.
  - v1.2.3: Add support for:
            * [configuration plugin](cloudify_configuration/README.md).
            * [terminal plugin](cloudify_configuration/README.md).
            Significant improvements to deployment/blueprint as external resource support.
  - v1.2.4: Add support for:
            * handling paging in long executions in the deployment proxy
            * added configuration plugin examples
  - v1.2.5: Added Cloud-init type.
  - v1.3.0: Added File type.
