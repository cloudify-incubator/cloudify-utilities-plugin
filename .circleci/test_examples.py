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
import pytest

from ecosystem_tests.dorkl import (
    basic_blueprint_test,
    cleanup_on_failure, prepare_test
)

prepare_test(secrets={})

blueprint_list = [
    'cloudify_cloudinit/examples/simple.yaml',
    'cloudify_ssh_key/examples/create-secret-agent-key.yaml',
    'cloudify_secrets/examples/write-secret-blueprint.yaml',
    'cloudify_rest/examples/example-1-blueprint.yaml'
]


@pytest.fixture(scope='function', params=blueprint_list)
def blueprint_examples(request):
    test_name = os.path.dirname(request.param).split('/')[-1:][0]
    try:
        basic_blueprint_test(
            request.param,
            test_name
        )
    except:
        cleanup_on_failure(test_name)
        raise


def test_blueprints(blueprint_examples):
    assert blueprint_examples is None
