# Built-in Imports
import os

# Cloudify Imports
from ecosystem_tests import TestLocal, utils


SSH_KEY_BP_ZIP = 'https://github.com/cloudify-examples/' \
                 'helpful-blueprint/archive/master.zip'


class TestUtilities(TestLocal):

    def setup_cfy_local(self):
        return

    def install_manager(self):
        return

    def uninstall_manager(self):
        return

    def inputs(self):
        try:
            return {}
        except KeyError:
            raise

    def setUp(self):
        os.environ['ECOSYSTEM_SESSION_PASSWORD'] = 'admin'
        super(TestUtilities, self).setUp('azure.yaml')
        if 'ECOSYSTEM_SESSION_MANAGER_IP' not in os.environ:
            self.manager_ip = 'localhost'
        os.environ['ECOSYSTEM_SESSION_MANAGER_IP'] = self.manager_ip

    def install_ssh_key(self, blueprint_id):
        utils.upload_blueprint(
            SSH_KEY_BP_ZIP,
            blueprint_id,
            'keys.yaml')
        utils.create_deployment(
            blueprint_id)
        utils.execute_install(blueprint_id)
        delete_dep_command = \
            'cfy deployments delete -f {0}'.format(blueprint_id)
        utils.execute_command(delete_dep_command)
        if not utils.get_secrets('agent_key_private') or not \
                utils.get_secrets('agent_key_public'):
            raise Exception(
                'agent_key_private or agent_key_public not in secrets')

    def install_deployment_proxy_new(self, blueprint_id):
        parent_id = '{0}-parent'.format(blueprint_id)
        utils.execute_command(
            'cfy blueprints upload cloudify_deployment_proxy/'
            'examples/test-blueprint.yaml -b {0}'.format(
                parent_id))
        utils.create_deployment(
            parent_id, inputs={'test_id': blueprint_id})
        utils.execute_install(parent_id)
        rs = utils.get_deployment_resources_by_node_type_substring(
            parent_id,
            'cloudify.nodes.DeploymentProxy')
        deployment_outputs = \
            rs[0]['instances'][0]['runtime_properties']['deployment']
        if 'output1' not in deployment_outputs['outputs']:
            raise Exception(
                'output1 not in {0}'.format(deployment_outputs))

    def install_deployment_proxy_external(self, blueprint_id):
        parent_id = '{0}-existing'.format(blueprint_id)
        utils.execute_command(
            'cfy blueprints upload cloudify_deployment_proxy/'
            'examples/test-blueprint-existing.yaml -b {0}'.format(
                parent_id))
        utils.create_deployment(
            parent_id,
            inputs={'test_id': blueprint_id})
        utils.execute_install(parent_id)
        rs = utils.get_deployment_resources_by_node_type_substring(
            parent_id,
            'cloudify.nodes.DeploymentProxy')
        deployment_outputs = \
            rs[0]['instances'][0]['runtime_properties']['deployment']
        if 'output1' not in deployment_outputs['outputs']:
            raise Exception(
                'output1 not in {0}'.format(deployment_outputs))

    def install_blueprints(self):
        ssh_id = 'sshkey-{0}'.format(
            os.environ['CIRCLE_BUILD_NUM'])
        proxy_id = 'proxy-{0}'.format(
            os.environ['CIRCLE_BUILD_NUM'])
        self.install_ssh_key(ssh_id)
        self.install_deployment_proxy_new(proxy_id)
        self.install_deployment_proxy_external(proxy_id)

    def test_blueprints(self):
        utils.update_plugin_yaml(
            os.environ['CIRCLE_SHA1'], 'cfy_util')
        workspace_path = os.path.join(
            os.path.abspath('workspace'),
            'build')
        utils.upload_plugin(
            utils.get_wagon_path(workspace_path))
        for plugin in self.plugins_to_upload:
            utils.upload_plugin(plugin[0], plugin[1])
        self.install_blueprints()
