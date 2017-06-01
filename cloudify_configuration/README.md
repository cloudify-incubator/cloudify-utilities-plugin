# Cloudify Utilities: Configuration

## Configuration plugin manual for VCPE solution

### Preparation
Create a list of parameter that take part in you reployment,
Map between the parameters you have listed and nodes you have, Several parameter are going to be used by Almost every node and others are going to just be used by 2 or 3 nodes.

### Writing the Blueprint

# Create main input
This input will hole initial parameter for the deployment.
The input can be either in Dict  or in JSON Formats.

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
The relevant parameters specified will be taken from the global configuration stored in the configuration node and populated in to the runtime properties of ne hode instance.
In the properties section create a key “params_list” inside this key create a list of the relevant params for this node.

# Hard code parameters (Optional)
It is possible to hardcode and override  some of the parameters rather than taking the from the global configuration. This is usefull when you have similar nodes with small differences that you want to hardcode. For example the Master / Slave node configuration will be similar except the setting who is master and who is slave.

# Define the Interfaces
This can be done Ether individually or by using a node type,
The interfaces usually are used are start stop and update, The plugin will call the update interface during the update workflow.
The interface should use the parameters found in “params” runtime properties, wich is managed by the configuration plugin.
Update interface
In the update interface new keys are added to the params runtime prop.
diff_params - a list of changed parameters
old_params - previous version of all parameters, (non recursive - will hold only one version back)

# Relationship to the configuration Node
This relationship calls the function which will populate the nodes runtime properties with the values relevant as specified in the “params_list”

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

Using the configuration plugin with templates
It is possible to benefit form a powerful combination When the configuration plugin is combined with Terminal, Netcong or script plugins.
The Templates re rendered Via the Jinja2 framework that provides powerful capabilities including loops, statements and calculations.

# Netconf plugin
Netconf plugin supports templates all have to be done is point the params interface input to instance runtime properties parameters (which is populated via the configuration plugin)

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
Terminal plugin supports templates all have to be done is point the params in call list  to instance runtime properties parameters (which is populated via the configuration plugin)
# Example

```yaml
  start:
    inputs:
      terminal_auth:
      ..
      calls:
        - template templates/fortigate.cmd
          params:  { get_attribute: [SELF, params] }
```

# Script plugin
In script plugin in order to use the teplates functionality you use the download_resource_and_render function. In the template point the paramters to the params runtime propertiy

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
