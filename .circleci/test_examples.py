########
# Copyright (c) 2014-2019 Cloudify Platform Ltd. All rights reserved
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


import os
import json
import pytest

from ecosystem_tests.dorkl import (
    basic_blueprint_test,
    cleanup_on_failure, prepare_test
)

prepare_test(secrets={}, execute_bundle_upload=False)

blueprint_list = [
    'examples/blueprint-examples/utilities-examples/cloudify_cloudinit/simple.yaml',
    'examples/blueprint-examples/utilities-examples/cloudify_ssh_key/create-secret-agent-key.yaml',
    'examples/blueprint-examples/utilities-examples/cloudify_secrets/write-secret-blueprint.yaml',
    'examples/blueprint-examples/utilities-examples/cloudify_rest/example-github-status.yaml'
]


@pytest.fixture(scope='function', params=blueprint_list)
def blueprint_examples(request):
    test_name = os.path.dirname(request.param).split('/')[-1:][0]
    try:
        basic_blueprint_test(
            request.param,
            test_name,
            inputs=json.dumps({})
        )
    except:
        cleanup_on_failure(test_name)
        raise


def test_blueprints(blueprint_examples):
    assert blueprint_examples is None
