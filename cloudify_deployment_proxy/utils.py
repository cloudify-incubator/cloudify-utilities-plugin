# Copyright (c) 2017 GigaSpaces Technologies Ltd. All rights reserved
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

from cloudify import ctx


def get_desired_value(key,
                      args,
                      instance_attr,
                      node_prop):

    return (args.get(key) or
            instance_attr.get(key) or
            node_prop.get(key))


def update_attributes(_type, _key, _value):
    ctx.instance.runtime_properties[_type][_key] = _value
