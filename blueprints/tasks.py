# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

import uuid

import proxy_common

from cloudify import ctx
from cloudify import exceptions
from cloudify import manager

from cloudify.decorators import operation


@operation
def create_validation(**kwargs):
    ctx.logger.info("Entering create_validation event.")
    client = manager.get_rest_client()
    blueprint_id = ctx.node.properties['blueprint_id']
    use_existing_deployment = ctx.node.properties[
        'use_existing_deployment']
    if not use_existing_deployment:
        if not blueprint_id or blueprint_id == '':
            ctx.logger.error("Malformed blueprint ID.")
            raise exceptions.NonRecoverableError(
                "Blueprint ID is not specified.")
        try:
            client.blueprints.get(blueprint_id)
            ctx.logger.info("Success, blueprint exists.")
        except Exception as ex:
            ctx.logger.error("Error during obtaining blueprint {0}. "
                             "Reason: {1}."
                             .format(blueprint_id, str(ex)))
            raise exceptions.NonRecoverableError(
                "Error during obtaining blueprint {0}. "
                "Reason: {1}.".format(blueprint_id, str(ex)))

    ctx.logger.info("Exiting create_validation event.")


@operation
def create_deployment(deployment_inputs=None, **kwargs):
    ctx.logger.info("Entering create_deployment event.")
    client = manager.get_rest_client()
    blueprint_id = ctx.node.properties['blueprint_id']
    ctx.logger.info("Blueprint ID: %s" % blueprint_id)
    deployment_id = "{0}-{1}".format(blueprint_id,
                                     str(uuid.uuid4()))
    use_existing_deployment = ctx.node.properties['use_existing_deployment']
    existing_deployment_id = ctx.node.properties['existing_deployment_id']
    try:
        if not use_existing_deployment:
            ctx.logger.info("deployment ID to create: %s" % deployment_id)
            deployment = client.deployments.create(
                blueprint_id,
                deployment_id,
                inputs=deployment_inputs)
            ctx.logger.info("Deployment object {0}."
                            .format(str(deployment)))
        else:
            client.deployments.get(existing_deployment_id)
            deployment_id = existing_deployment_id
        ctx.logger.info("Instance runtime properties %s"
                        % str(ctx.instance.runtime_properties))
        proxy_common.poll_until_with_timeout(
            proxy_common.check_if_deployment_is_ready(
                client, deployment_id),
            expected_result=True,
            timeout=900)
        ctx.instance.runtime_properties.update(
            {'deployment_id': deployment_id})
    except Exception as ex:
        ctx.logger.error(str(ex))
        raise exceptions.NonRecoverableError(str(ex))

    ctx.logger.info("Exiting create_validation event.")


@operation
def delete_deployment(**kwargs):
    ctx.logger.info("Entering delete_deployment event.")

    if 'deployment_id' not in ctx.instance.runtime_properties:
        raise exceptions.NonRecoverableError(
            "Deployment ID as runtime property not specified.")

    client = manager.get_rest_client()
    deployment_id = ctx.instance.runtime_properties[
        'deployment_id']
    ignore = ctx.node.properties['ignore_live_nodes_on_delete']
    try:
        proxy_common.poll_until_with_timeout(
            proxy_common.check_if_deployment_is_ready(
                client, deployment_id),
            expected_result=True,
            timeout=900)
        client.deployments.delete(deployment_id,
                                  ignore_live_nodes=ignore)
    except Exception as ex:
        ctx.logger.error("Error during deployment deletion {0}. "
                         "Reason: {1}."
                         .format(deployment_id, str(ex)))
        raise exceptions.NonRecoverableError(
            "Error during deployment uninstall {0}. "
            "Reason: {1}.".format(deployment_id, str(ex)))
    ctx.logger.info("Exiting delete_deployment event.")
