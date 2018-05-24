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
- [Cloudify Suspend Workflow](cloudify_suspend/README.md)


## Versions:

  - v1.0.0: First stable version.
  - v1.1.0: Add Cloudify SHH Key Plugin. Combine BlueprintDeployment node type
            and DeploymentProxy node type.
  - v1.1.1: Fixed an issue where deployments may be re-installed.
  - v1.2.0:
    * Add NodeInstanceProxy node type.
    * Add cloudify rest client mock.
    * Added more tests.
  - v1.2.1: Public Key Runtime Property.
  - v1.2.2: Add ability to store to runtime properties.
  - v1.2.3: Add support for:
    * [configuration plugin](cloudify_configuration/README.md).
    * [terminal plugin](cloudify_configuration/README.md).
    * Significant improvements to deployment/blueprint as external resource
      support.
  - v1.2.4: Add support for:
    * handling paging in long executions in the deployment proxy
    * added configuration plugin examples
  - v1.2.5: Added Cloud-init type.
  - v1.3.0: Added File type.
  - v1.3.1:
    * Adding Suspend/Resume Workflow
    * Adding Custom Workflow Tool
    * Removing Files Feature
    * Reorganizing Plugin YAMLs
  - v1.4.0: Added back the files feature in a simplified form.
  - v1.4.1: Configuration Plugin IP regression fixes.
  - v1.4.2: Handle parameters correctly in configuration update operation.
  - v1.4.3: Allow infinite timeout in deployment proxy.
  - v1.4.4: Fix issue with encoding event message in post deployment proxy
  - v1.4.5: Terminal Plugin Handle Socket Timeout.
  - v1.5.0: Add REST Plugin for generic interaction with REST APIs.
  - v1.5.0.1:
    * Deployment proxy bug fix.
    * Ensure that correct execution ID is polled for deployment,
      when workflow ID is identical.
  - v1.5.1: Support user configuration of failure success on certain responses
            in REST plugin.
  - v1.5.2: Bug fix for empty deployment outputs in deployment proxy.
  - v1.5.3: Handle retries in REST type.
  - v1.5.4: Add ability to send newline after answer question in terminal
            plugin.
  - v1.6.0:
    * Backup/Restore workflows.
    * Close connection after error in terminal plugin.
  - v1.6.1:
    * Improve REST Plugin Failure with recoverable errors.
  - v.1.7.0:
    * Add support for local blueprint archive
