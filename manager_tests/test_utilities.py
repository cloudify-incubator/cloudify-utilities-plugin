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
        return utils.get_secret('agent_key_private') or \
            utils.get_secret('agent_key_public')

    def install_deployment_proxy_new(self, blueprint_id):
        utils.execute_command(
            'cfy blueprints upload cloudify_deployment_proxy/'
            'examples/test-blueprint.yaml -b {0}'.format(
                blueprint_id))
        utils.create_deployment(
            blueprint_id, inputs={'test_id': blueprint_id})
        utils.execute_install(blueprint_id)
        deployment_outputs = utils.get_deployment_outputs(
            blueprint_id)
        if 'output1' not in deployment_outputs:
            return True
        return False

    def install_deployment_proxy_external(self, blueprint_id):
        blueprint_id_existing = '{0}-existing'.format(blueprint_id)
        utils.execute_command(
            'cfy blueprints upload cloudify_deployment_proxy/'
            'examples/test-blueprint-existing.yaml -b {0}'.format(
                blueprint_id_existing))
        utils.create_deployment(
            blueprint_id_existing,
            inputs={'test_id': blueprint_id})
        utils.execute_install(blueprint_id_existing)
        deployment_outputs = utils.get_deployment_outputs(
            blueprint_id)
        if 'output1' not in deployment_outputs:
            return True
        return False

    def install_blueprints(self):
        ssh_id = 'sshkey-{0}'.format(
            os.environ['CIRCLE_BUILD_NUM'])
        proxy_id = 'proxy-{0}'.format(
            os.environ['CIRCLE_BUILD_NUM'])

        result = self.install_ssh_key(ssh_id) or \
                self.install_deployment_proxy_new(proxy_id) or \
                self.install_deployment_proxy_external(proxy_id)
        if result:
            raise Exception('Failed to execute blueprint: {0}'.format(
                result))

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
