# Cloudify SSH Key

This plugin enables a user to create a private and public key.


### Notes

- Tested with Cloudify Manager 4.0.
- For Cloudify Manager 4.0 and above: Private key can be stored in secret store.

## Examples:

- [SSH Key](#ssh-key-instructions)


## SSH Key Instructions

This basic example covers a trivial scenario:
- Create and store a private key in secret store.
- Create a public key.

1. Install:

```shell
$ cfy install cloudify_ssh/examples/ssh-key-blueprint.yaml -b key-test
Uploading blueprint cloudify_ssh/examples/ssh-key-blueprint.yaml...
 ssh-key-blueprint.... |################################################| 100.0%
Blueprint uploaded. The blueprint's id is key-test
Creating new deployment from blueprint key-test...
Deployment created. The deployment's id is key-test
Executing workflow install on deployment key-test [timeout=900 seconds]
Deployment environment creation is in progress...
2017-04-24 12:38:58.336  CFY <key-test> Starting 'create_deployment_environment' workflow execution
...
2017-04-24 12:39:10.654  CFY <key-test> Starting 'install' workflow execution
...
2017-04-20 20:25:15.218  CFY <key-test> 'install' workflow execution succeeded
Finished executing workflow install on deployment key-test
$ cfy secrets list
Listing all secrets...
Secrets:
+----------------------+--------------------------+--------------------------+------------+----------------+------------+
|         key          |        created_at        |        updated_at        | permission |  tenant_name   | created_by |
+----------------------+--------------------------+--------------------------+------------+----------------+------------+
|     example-key      | 2017-04-24 12:39:14.681  | 2017-04-24 12:39:14.681  |  creator   | default_tenant |   admin    |
+----------------------+--------------------------+--------------------------+------------+----------------+------------+
```

Notice the secret was created.


2. Uninstall:

```shell
$ cfy uninstall key-test -p ignore_failure=true
Executing workflow uninstall on deployment key-test [timeout=900 seconds]
2017-04-24 12:40:33.563  CFY <key-test> Starting 'uninstall' workflow execution
...
2017-04-24 12:40:38.439  CFY <key-test> 'uninstall' workflow execution succeeded
Finished executing workflow uninstall on deployment key-test
```
