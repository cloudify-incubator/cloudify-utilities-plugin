[![Build Status](https://circleci.com/gh/cloudify-incubator/cloudify-utilities-plugin.svg?style=shield&circle-token=:circle-token)](https://circleci.com/gh/cloudify-incubator/cloudify-utilities-plugin)

# Cloudify Utilities

Utilities for extending Cloudify features.


## Contents:

- [Cloudify Cloud-Init](cloudify_cloudinit/README.md)
- [Cloudify Configuration](cloudify_configuration/README.md)
- [Cloudify Custom Workflow](cloudify_custom_workflow/README.md)
- [Cloudify Deployment Proxy](cloudify_deployment_proxy/README.md)
- [Cloudify Files](cloudify_files/README.md)
- [Cloudify REST plugin](cloudify_rest/README.md)
- [Cloudify Scale List Workflow](cloudify_scalelist/README.md)
- [Cloudify SSH Key](cloudify_ssh_key/README.md)
- [Cloudify Suspend/Backup Workflows](cloudify_suspend/README.md)
- [Cloudify Terminal](cloudify_terminal/README.md)


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
  - v1.6.1: Improve REST Plugin Failure with recoverable errors.
  - v1.7.0: Add support for local blueprint archive
  - v1.7.1: Fix call sequence in backup workflow.
  - v1.7.2:
    * Rest Plugin Improvements
    * Update tests to use cirleci v2 and to use ecosystem test tools
    * Added integration tests for key, file, cloudinit, deployment proxy, and rest tools.
  - v1.7.3: Examples for use terminal plugin in relationships
  - v1.8.0: Add scale several scaling group in one transaction
  - v1.8.1: Scalelist Down: Additional examples for remove instances created
            by install workflow.
  - v1.8.2: Scalelist Down: Additional examples for remove instances by property value
            without transaction id.
  - v1.8.3: Scalelist Down: Additional example for update workflow.
  - v1.9.0:
    * Scalelist Down: Support deep check property value
    * Deployment Proxy: Install plugins and set secrets with create deployment.
  - v1.9.1:
    * Fix issue with deployment outputs when adding nodes derived from deployment proxy node