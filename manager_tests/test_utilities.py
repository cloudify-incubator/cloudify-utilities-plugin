# Built-in Imports
import os
import sys

# Cloudify Imports
from ecosystem_tests import EcosystemTestBase, utils, PasswordFilter


SSH_KEY_BP_ZIP = 'https://github.com/cloudify-examples/' \
                 'helpful-blueprint/archive/master.zip'


class TestUtilities(EcosystemTestBase):

    @classmethod
    def setUpClass(cls):
        os.environ['ECOSYSTEM_SESSION_PASSWORD'] = 'admin'

    @classmethod
    def tearDownClass(cls):
        try:
            del os.environ['ECOSYSTEM_SESSION_MANAGER_IP']
            del os.environ['ECOSYSTEM_SESSION_LOADED']
            del os.environ['ECOSYSTEM_SESSION_PASSWORD']
            del os.environ['CLOUDIFY_STORAGE_DIR']
            del os.environ['ECOSYSTEM_SESSION_BLUEPRINT_DIR']
        except KeyError:
            pass

    def setUp(self):
        if self.password not in self.sensitive_data:
            self.sensitive_data.append(self.password)
        sys.stdout = PasswordFilter(self.sensitive_data, sys.stdout)
        sys.stderr = PasswordFilter(self.sensitive_data, sys.stderr)
        if 'ECOSYSTEM_SESSION_MANAGER_IP' not in os.environ:
            self.upload_plugins('cfy_util')
        os.environ['ECOSYSTEM_SESSION_MANAGER_IP'] = 'localhost'

    @property
    def manager_ip(self):
        return 'localhost'

    @property
    def node_type_prefix(self):
        return 'cloudify.nodes.aws'

    @property
    def plugin_mapping(self):
        return 'awssdk'

    @property
    def blueprint_file_name(self):
        return 'aws.yaml'

    @property
    def external_id_key(self):
        return 'aws_resource_id'

    @property
    def server_ip_property(self):
        return 'ip'

    @property
    def sensitive_data(self):
        return [
            os.environ['AWS_SECRET_ACCESS_KEY'],
            os.environ['AWS_ACCESS_KEY_ID']
        ]

    @property
    def inputs(self):
        try:
            return {}
        except KeyError:
            raise

    def install_manager(self, _):
        pass

    @staticmethod
    def uninstall_manager(cfy_local):
        pass

    def test_install_ssh_key(self):
        blueprint_id = 'sshkey-{0}'.format(self.application_prefix)
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

    # There are two Deployment Proxy Tests and should be executed in order.
    # test_install_deployment_proxy_A_new
    # test_install_deployment_proxy_B_external
    # Nose executes according to alphabetical order.
    # The second test uses a deployment created in the first test.
    def test_install_deployment_proxy_A_new(self):
        blueprint_id = 'dp-{0}'.format(self.application_prefix)
        parent_id = 'dp-{0}-parent'.format(self.application_prefix)
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

    def test_install_deployment_proxy_B_external(self):
        blueprint_id = 'dp-{0}-parent'.format(self.application_prefix)
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

    def test_install_cloud_init(self):
        blueprint_id = 'cfyinit-{0}'.format(self.application_prefix)
        utils.execute_command(
            'cfy blueprints upload cloudify_cloudinit/'
            'examples/simple.yaml -b {0}'.format(
                blueprint_id))
        utils.create_deployment(blueprint_id)
        utils.execute_install(blueprint_id)
        rs = utils.get_deployment_resources_by_node_type_substring(
            blueprint_id,
            'cloudify.nodes.CloudInit.CloudConfig')
        cloud_config = \
            rs[0]['instances'][0]['runtime_properties']['cloud_config']
        if '#cloud-config' not in cloud_config:
            raise Exception(
                '{0} not in {1}'.format('#cloud-config', cloud_config))
        utils.execute_uninstall(blueprint_id)

    def test_install_file(self):
        blueprint_id = 'file-{0}'.format(self.application_prefix)
        file_path = '/tmp/{0}'.format(blueprint_id)
        utils.execute_command(
            'cfy blueprints upload cloudify_files/'
            'examples/simple.yaml -b {0}'.format(
                blueprint_id))
        utils.create_deployment(
            blueprint_id, inputs={'file_path': file_path})
        utils.execute_install(blueprint_id)
        if utils.execute_command(
                'docker exec cfy_manager stat {0}'.format(file_path)):
            raise Exception(
                '{0} not written.'.format(file_path))
        utils.execute_uninstall(blueprint_id)
        if not utils.execute_command(
                'docker exec cfy_manager stat {0}'.format(file_path)):
            raise Exception(
                '{0} not deleted.'.format(file_path))

    def test_install_rest(self):
        blueprint_id = 'rest-{0}'.format(self.application_prefix)
        utils.execute_command(
            'cfy blueprints upload cloudify_rest/'
            'examples/example-4-blueprint.yaml -b {0}'.format(
                blueprint_id))
        utils.create_deployment(
            blueprint_id, inputs={'commit': os.environ['CIRCLE_SHA1']})
        utils.execute_install(blueprint_id)
        rs = utils.get_deployment_resources_by_node_type_substring(
            blueprint_id,
            'cloudify.rest.Requests')
        rest_instance = rs[0]['instances'][0]['runtime_properties']
        if 'commit' not in rest_instance['result_propeties']:
            raise Exception(
                '{0} not in {1}'.format(
                    'commit', rest_instance['result_propeties']))
        utils.execute_uninstall(blueprint_id)
