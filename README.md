[![Build Status](https://circleci.com/gh/cloudify-incubator/cloudify-utilities-plugin.svg?style=shield&circle-token=:circle-token)](https://circleci.com/gh/cloudify-incubator/cloudify-utilities-plugin)

# Cloudify Utilities

Utilities for extending Cloudify features.


## Contents:

- [Cloudify Deployment Proxy](cloudify_deployment_proxy/README.md)
- [Cloudify SSH Key](cloudify_ssh_key/README.md)
- [Cloudify Configuration](cloudify_configuration/README.md)
- [Cloudify Terminal](cloudify_terminal/README.md)


## Versions:

  - v1.0.0: First stable version.
  - v1.1.0: Add Cloudify SHH Key Plugin. Combine BlueprintDeployment node type and DeploymentProxy node type.
  - v1.1.1: Fixed an issue where deployments may be re-installed.
  - v1.2.0: Add NodeInstanceProxy node type.
            Add cloudify rest client mock
            Added more tests
  - v1.2.1: Public Key Runtime Property
  - v1.2.2: Add ability to store to runtime props
