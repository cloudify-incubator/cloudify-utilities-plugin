# Built-in Imports
import os

# Cloudify Imports
from ecosystem_tests import TestLocal, utils


AZURE_WAGON = 'http://repository.cloudifysource.org/cloudify/' \
              'wagons/cloudify-azure-plugin/1.7.2/' \
              'cloudify_azure_plugin-1.7.2-py27-none' \
              '-linux_x86_64-centos-Core.wgn'
AZURE_YAML = 'http://www.getcloudify.org/spec/azure-plugin/' \
             '1.7.2/plugin.yaml'
AZURE_NETWORK_ZIP = 'https://github.com/cloudify-examples/' \
                    'azure-example-network/archive/master.zip'
HELLO_WORLD_ZIP = 'https://github.com/cloudify-examples/' \
                  'hello-world-blueprint/archive/master.zip'
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
            return {
                'password': self.password,
                'location': 'westus',
                'resource_prefix': 'trammell',
                'resource_suffix': os.environ['CIRCLE_BUILD_NUM'],
                'subscription_id': os.environ['AZURE_SUB_ID'],
                'tenant_id': os.environ['AZURE_TEN_ID'],
                'client_id': os.environ['AZURE_CLI_ID'],
                'client_secret': os.environ['AZURE_CLI_SE'],
                'large_image_size': 'Standard_H8m'
            }
        except KeyError:
            raise

    def teardown_failed_resource_group(self, resource_group_name):
        utils.execute_command(
            'az resource delete --name {0}'.format(
                resource_group_name))

    def setUp(self):
        sensitive_data = [
            os.environ['AZURE_CLI_SE'],
            os.environ['AZURE_CLI_ID'],
            os.environ['AZURE_TEN_ID'],
            os.environ['AZURE_SUB_ID']
        ]
        super(TestUtilities, self).setUp(
            'azure.yaml', sensitive_data=sensitive_data,
            plugins_to_upload=[(AZURE_WAGON, AZURE_YAML)])

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
        return utils.execute_command(delete_dep_command)

    def install_network(self, blueprint_id='azure-example-network'):
        resource_group_name = \
            'cfyresource_group{0}'.format(
                os.environ['CIRCLE_BUILD_NUM'])
        self.addCleanup(
            self.teardown_failed_resource_group,
            resource_group_name)
        network_inputs = {
            'location': 'westus',
            'resource_prefix': 'trammellnet',
            'resource_suffix': os.environ['CIRCLE_BUILD_NUM'],
            'subscription_id': os.environ['AZURE_SUB_ID'],
            'tenant_id': os.environ['AZURE_TEN_ID'],
            'client_id': os.environ['AZURE_CLI_ID'],
            'client_secret': os.environ['AZURE_CLI_SE'],
        }
        utils.upload_blueprint(
            AZURE_NETWORK_ZIP,
            blueprint_id,
            'simple-blueprint.yaml')
        utils.create_deployment(
            blueprint_id,
            inputs=network_inputs)
        return utils.execute_install(blueprint_id)

    def install_hello_world(self, blueprint_id):
        resource_group_name = \
            'cfyresource_group{0}'.format(
                os.environ['CIRCLE_BUILD_NUM'])
        self.addCleanup(
            self.teardown_failed_resource_group,
            resource_group_name)
        hello_world_inputs = {
            'location': 'westus',
            'resource_prefix': 'trammellhw',
            'resource_suffix': os.environ['CIRCLE_BUILD_NUM'],
            'subscription_id': os.environ['AZURE_SUB_ID'],
            'tenant_id': os.environ['AZURE_TEN_ID'],
            'client_id': os.environ['AZURE_CLI_ID'],
            'client_secret': os.environ['AZURE_CLI_SE'],
        }
        utils.upload_blueprint(
            HELLO_WORLD_ZIP,
            blueprint_id,
            'azure.yaml')
        utils.create_deployment(
            blueprint_id,
            inputs=hello_world_inputs)
        return utils.execute_install(blueprint_id)

    def install_blueprints(self):
        ssh_id = 'sshkey-{0}'.format(
            os.environ['CIRCLE_BUILD_NUM'])
        hw_id = 'hello-world-{0}'.format(
            os.environ['CIRCLE_BUILD_NUM'])
        if self.install_network() or \
                self.install_ssh_key(ssh_id) or \
                self.install_hello_world(hw_id) or \
                utils.execute_uninstall(hw_id) or \
                utils.execute_uninstall('azure-example-network'):
            raise Exception('Failed to execute blueprint.')

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
