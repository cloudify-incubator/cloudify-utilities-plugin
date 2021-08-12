# Cloudify Utilities: Resources

## Description
Added support for managing resources reservations from the blueprint level.

It is often needed to manage resources pools during deployment provisioning.
For instance we may have to provision the same blueprint as 3 deployments in a single datacenter with Openstack.
So far we needed to e.g. make sure if we are not putting any conflicting IPs as inputs.
If there was any mistake, deployment failed.

*Resources plugin* allows to define resources list - you need only to use a relationship to make a reservation on a particular resource.

With *resources plugin* you can make reservations on resources using a dedicated relationship (reserve_list_item).

## Node types

#### cloudify.nodes.resources.List

Node responsible for performing CUD operations on the set of resources.

Properties:
* ***resource_config*** - list of resources which you want to manage - they can be IPs, host IDs, anything!

Runtime properties:
* ***resource_config*** - list of resources which are being managed
* ***free_resources*** - list of resources which are available for reservation
* ***reservations*** - a key-value dictionary containing information about the resources & 
`cloudify.nodes.resources.ListItem` node instances, which holds the particular reservations, in format:
```
{
    "node_instance_xyz": resource0,
    "node_instance_abc": resource1,
    ...
}
```

#### cloudify.nodes.resources.ListItem

Node responsible for holding the reserved resource.

Runtime properties:
* ***reservation*** - contains the reserved resource.


## Examples

[Example](examples/blueprint.yaml)
