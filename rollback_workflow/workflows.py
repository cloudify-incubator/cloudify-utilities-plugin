# Copyright (c) 2016-2019 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from cloudify.decorators import workflow
from cloudify.plugins.workflows import execute_operation

@workflow(resumable=True)
def start(ctx, operation_parms, run_by_dependency_order, type_names, node_ids,
          node_instance_ids, **kwargs):
    execute_operation(ctx, 'cloudify.interfaces.lifecycle.start',
                      operation_parms, True, run_by_dependency_order,
                      type_names, node_ids, node_instance_ids, **kwargs)

@workflow(resumable=True)
def stop(ctx, operation_parms, run_by_dependency_order, type_names, node_ids,
         node_instance_ids, **kwargs):
    execute_operation(ctx, 'cloudify.interfaces.lifecycle.stop',
                      operation_parms, True, run_by_dependency_order,
                      type_names, node_ids, node_instance_ids, **kwargs)

@workflow(resumable=True)
def precreate(ctx, operation_parms, run_by_dependency_order, type_names, node_ids,
          node_instance_ids, **kwargs):
    execute_operation(ctx, 'cloudify.interfaces.lifecycle.precreate',
                      operation_parms, True, run_by_dependency_order,
                      type_names, node_ids, node_instance_ids, **kwargs)

@workflow(resumable=True)
def create(ctx, operation_parms, run_by_dependency_order, type_names, node_ids,
          node_instance_ids, **kwargs):
    execute_operation(ctx, 'cloudify.interfaces.lifecycle.create',
                      operation_parms, True, run_by_dependency_order,
                      type_names, node_ids, node_instance_ids, **kwargs)

@workflow(resumable=True)
def configure(ctx, operation_parms, run_by_dependency_order, type_names, node_ids,
          node_instance_ids, **kwargs):
    execute_operation(ctx, 'cloudify.interfaces.lifecycle.configure',
                      operation_parms, True, run_by_dependency_order,
                      type_names, node_ids, node_instance_ids, **kwargs)

@workflow(resumable=True)
def poststart(ctx, operation_parms, run_by_dependency_order, type_names, node_ids,
          node_instance_ids, **kwargs):
    execute_operation(ctx, 'cloudify.interfaces.lifecycle.poststart',
                      operation_parms, True, run_by_dependency_order,
                      type_names, node_ids, node_instance_ids, **kwargs)

@workflow(resumable=True)
def prestop(ctx, operation_parms, run_by_dependency_order, type_names, node_ids,
          node_instance_ids, **kwargs):
    execute_operation(ctx, 'cloudify.interfaces.lifecycle.prestop',
                      operation_parms, True, run_by_dependency_order,
                      type_names, node_ids, node_instance_ids, **kwargs)

@workflow(resumable=True)
def delete(ctx, operation_parms, run_by_dependency_order, type_names, node_ids,
          node_instance_ids, **kwargs):
    execute_operation(ctx, 'cloudify.interfaces.lifecycle.delete',
                      operation_parms, True, run_by_dependency_order,
                      type_names, node_ids, node_instance_ids, **kwargs)

@workflow(resumable=True)
def postdelete(ctx, operation_parms, run_by_dependency_order, type_names, node_ids,
          node_instance_ids, **kwargs):
    execute_operation(ctx, 'cloudify.interfaces.lifecycle.postdelete',
                      operation_parms, True, run_by_dependency_order,
                      type_names, node_ids, node_instance_ids, **kwargs)
