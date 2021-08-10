########
# Copyright (c) 2014-2018 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


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


def generate_inputs_from_deployments(inputs, deployments):
    inputs = inputs or []
    for iterator, deployment_id in enumerate(deployments):
        try:
            inputs[iterator]['deployment'] = deployment_id
        except IndexError:
            inputs.append({'deployment': deployment_id})
    return inputs


def generate_labels_from_inputs(inputs):
    return [{'csys-obj-parent': inp['deployment']} for inp in inputs]
