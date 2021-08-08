from cloudify_common_sdk.utils import get_deployments_from_blueprint


def generate_group_id_from_blueprint(blueprint_id):
    deployments = get_deployments_from_blueprint(blueprint_id)
    if not deployments:
        return '{bp}-group'.format(bp=blueprint_id)
    else:
        return '{bp}-group-{i}'.format(bp=blueprint_id, i=len(deployments))


def generate_deployment_ids_from_group_id(group_id, deployments):
    return ['{g}-{i}'.format(g=group_id, i=i) for i in range(
        len(deployments))]


def generate_inputs_from_connected_deployments(inputs, deployments):
    inputs = inputs or []
    for iterator, deployment_id in enumerate(deployments):
    	inputs[iterator]['deployment'] = deployment_id
    return inputs


def generate_labels_from_inputs(inputs):
    return [{'csys-obj-parent': inp['deployment']} for inp in inputs]
