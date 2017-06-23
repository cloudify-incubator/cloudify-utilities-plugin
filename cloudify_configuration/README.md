# Cloudify Utilities: Configuration

## Configuration plugin manual for VCPE solution

### Preparation
Create a list of parameters that take part in your deployment,
Map between the parameters you have listed and nodes you have, several parameters are going
to be used by almost every node and others are going to just be used by 2 or 3 nodes.

### Writing the Blueprint

# Create main input
This input will hole initial parameter for the deployment.
The input can be either in Dictionary or in JSON Formats.

### Example

```yaml
  parameters_json:
    default:
      Private: true
      Voice: true
      Public: true
      CPESerialNumber: CV3816AF0569
```

# Create configuration holder node
configuration holder will hold the entire configuration in it’s runtime properties
It will also be used as a target in relationships with nodes consuming the configuration

# Example

```yaml
  configuration:
    type: configuration_loader
    properties:
      parameters_json: { get_input: parameters_json }
```

# Create function nodes
Specify the relevant parameters
The relevant parameters specified will be taken from the global configuration
stored in the configuration node and populated in to the runtime properties of
the node instance. In the properties section create a key “params_list” inside
this key create a list of the relevant parameters for this node.

# Hard code parameters (Optional)
It is possible to hardcode and overwrite some of the parameters rather than
taking the from the global configuration. This is useful when you have similar
nodes with small differences that you want to hardcode. For example,
the `Master/Slave` node configuration will be similar except the setting
who is master and who is slave.

# Define the Interfaces
This can be done ether individually or by using a node type,
The interfaces usually are used are `start`, `stop` and `update`. The plugin will
call the update interface during the update workflow. The interface should use
the parameters found in “params” runtime properties, which is managed by the configuration plugin.

## Update interface
In the update interface, new keys are added to the `params` runtime property.
* `diff_params` - a list of changed parameters
* `old_params` - previous version of all parameters, (non recursive - will hold only one version back).

# Relationship to the configuration Node
This relationship calls the function which will populate the nodes runtime
properties with the values relevant as specified in the `params_list`

# Function Example

```yaml
  l3GW_primary:
    type: juniper_node_config
    properties:
      netconf_auth:
        user: { get_input: netconf_user }
        password: { get_input: netconf_password }
        ip: { get_input: l3gw_primary_ip }
        key_content: { get_input: netconf_key_content }
        port: { get_input: netconf_port }
      params_list:
        - RouteExternal
        - RouteInternal
        - JpPrimary
        - JpSecondary
        - RoutePublic
        - RouteNat
      params:
        JpPrimary: True
        JpSecondary: False
    interfaces:
      cloudify.interfaces.lifecycle:
        start:
          inputs:
            strict_check: false
            template: xmls/l3gw-start.txt
            deep_error_check: true
            params: { get_attribute: [SELF, params] }
        stop:
          inputs:
            strict_check: false
            template: xmls/l3gw-stop.txt
            deep_error_check: true
            params: { get_attribute: [SELF, params] }
        update:
          inputs:
            strict_check: false
            template: xmls/l3gw-update.txt
            deep_error_check: true
            params: { get_attribute: [SELF, params] }
    relationships:
      - type: load_from_config
        target: configuration
```

## Using the configuration plugin with templates
It is possible to benefit form a powerful combination when the configuration plugin
is combined with
[Terminal](https://github.com/cloudify-incubator/cloudify-utilities-plugin/tree/master/cloudify_terminal#cloudify-utilities-terminal), [Netconf](https://github.com/cloudify-cosmo/cloudify-netconf-plugin#cloudify-netconf-plugin) or
[Script](https://github.com/cloudify-cosmo/cloudify-script-plugin#cloudify-script-plugin) plugins.
The Templates are rendered via the Jinja2 framework that provides powerful capabilities including loops, statements and calculations.

# Netconf plugin
[Netconf plugin](https://github.com/cloudify-cosmo/cloudify-netconf-plugin#cloudify-netconf-plugin) supports templates and all have to be done
is point the params interface input to instance runtime properties parameters (which is populated via the configuration plugin).

# Example

```yaml
  start:
    inputs:
      strict_check: false
      template: xmls/l3gw-start.txt
      deep_error_check: true
      params: { get_attribute: [SELF, params] }
```

# Terminal plugin

[Terminal plugin](https://github.com/cloudify-incubator/cloudify-utilities-plugin/tree/master/cloudify_terminal#cloudify-utilities-terminal)
supports templates and all have to be done is point the params in call list to [instance](examples/simple.yaml)
runtime properties parameters (which is populated via the configuration plugin).

# Example

```yaml
  start:
    inputs:
      terminal_auth:
      ..
      calls:
        - template: templates/fortigate.cmd
          params:  { get_attribute: [SELF, params] }
```

# Script plugin
In [script plugin](https://github.com/cloudify-cosmo/cloudify-script-plugin#cloudify-script-plugin)
in order to use the templates functionality, you can use the `download_resource_and_render` function.
In the template point the parameters to the `params` runtime property.

## Example

### Blueprint:
```yaml
  start:
    Implementation: scriptis/example_start.sh
```

### Script:
```shell
#!/bin/bash
ctx download-resource-and-render templates/template.txt
```

### Template:
```shell
config global
config system interface
edit "{{ ctx.instance.runtime_properties.params.CustInterfaceName }}_IN"
```

# Provided types

## configuration_loader
Configuration loader holds the entire configuration in it’s runtime properties.

**Derived From:** `cloudify.nodes.ApplicationServer`

**Properties:**
* `parameters_json`: List of parameters for node.

**Workflow inputs**

* `configure`:
    * `parameters`: By default used values from `parameters_json` property.
    Store all values to runtime properties. Possible to use json encoded values or dictionary.

**Runtime properties:**

* `params`: storage for all configuration parameters, required for relationship lifecycle.

**Relationships:**

* `load_from_config`: Derived from `cloudify.relationships.depends_on` and must be used with target node only, e.g.: `cloudify.terminal.raw`.
Update `params` in depended node by filter in `params_list` and is called before `configuration` action in node.

**Examples:**

[Simple example](examples/simple.yaml)

# Provided workflow

## configuration_update

Workflow for update all nodes with types from `node_types_to_update` by values from `configuration_node_type`.

**Parameters:**
* `params`: list of parameters.
* `configuration_node_type`: type of configuration node, by default: `configuration_loader`.
* `node_types_to_update`: list of node types for update in workflow, by default: `juniper_node_config`, `fortinet_vnf_type`.
