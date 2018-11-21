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

import yaml
import logging
import ast
import re
import xmltodict
from jinja2 import Template
import requests
from . import LOGGER_NAME
from .exceptions import (
    RecoverableStatusCodeCodeException,
    ExpectationException,
    WrongTemplateDataException,
    NonRecoverableResponseException,
    RecoverableResponseException)

logger = logging.getLogger(LOGGER_NAME)

TEMPLATE_PROPERTY_RETRY_ON_CONNECTION_ERROR = 'retry_on_connection_error'


#  request_props (port, ssl, verify, hosts )
def process(params, template, request_props):
    logger.debug('template : {}'.format(template))
    template_yaml = yaml.load(template)
    result_properties = {}
    calls = []
    for call in template_yaml['rest_calls']:
        call_with_request_props = request_props.copy()
        logger.debug('call \n {}'.format(call))
        # enrich params with items stored in runtime props by prev calls
        params.update(result_properties)
        call = str(call)
        # Remove quotation marks before and after jinja blocks
        call = re.sub(r'\'\{\%', '{%', call)
        call = re.sub(r'\%\}\'', '%}', call)
        template_engine = Template(call)
        rendered_call = template_engine.render(params)
        call = ast.literal_eval(rendered_call)
        calls.append(call)
        logger.debug('rendered call \n {}'.format(call))
        call_with_request_props.update(call)
        logger.info(
            'call_with_request_props \n {}'.format(call_with_request_props))
        response = _send_request(call_with_request_props)
        _process_response(response, call, result_properties)
    result_properties = {'result_properties': result_properties,
                         'calls': calls}
    return result_properties


def _send_request(call):
    logger.info(
        '_send_request request_props:{}'.format(call))
    port = call['port']
    ssl = call['ssl']
    if port == -1:
        port = 443 if ssl else 80
    if not call.get('hosts', None):
        call['hosts'] = [call['host']]
    for i, host in enumerate(call['hosts']):
        full_url = '{}://{}:{}{}'.format('https' if ssl else 'http', host,
                                         port,
                                         call['path'])
        logger.debug('full_url : {}'.format(full_url))
        # check if payload can be used as json
        if call.get('payload_format', 'json') == 'json':
            data = None
            json_payload = call.get('payload', None)
        else:
            data = call.get('payload', None)
            json_payload = None

        try:
            response = requests.request(call['method'], full_url,
                                        headers=call.get('headers', None),
                                        data=data,
                                        json=json_payload,
                                        verify=call['verify'])
        except requests.exceptions.ConnectionError as e:
            logger.debug('ConnectionError for host : {}'.format(host))

            if TEMPLATE_PROPERTY_RETRY_ON_CONNECTION_ERROR in call and \
                    call[TEMPLATE_PROPERTY_RETRY_ON_CONNECTION_ERROR]:

                raise RecoverableResponseException(
                    'ConnectionError {0} has occurred, but flag {1} is set. '
                    'Retrying...'
                    .format(
                        str(e),
                        TEMPLATE_PROPERTY_RETRY_ON_CONNECTION_ERROR
                    )
                )

            if i == len(call['hosts']) - 1:
                logger.error('No host from list available')
                raise

    logger.info(
        'Response \n content:{}\n status_code:{}\n'
        .format(response.content, response.status_code)
    )

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        if response.status_code in call.get('recoverable_codes', []):
            raise RecoverableStatusCodeCodeException(
                'Response code {} defined as recoverable'.format(
                    response.status_code))
        raise
    return response


def _process_response(response, call, store_props):
    logger.debug(
        '_process_response \n response:{}\n call:{}\n store_props:{}'.format(
            response,
            call, store_props))
    response_format = call.get('response_format', 'json').upper()

    if re.match('JSON|XML', response_format):
        if response_format == 'JSON':
            logger.debug('response_format json')
            json = response.json()
        else:  # XML
            logger.debug('response_format xml')
            json = xmltodict.parse(response.text)
            logger.debug('xml transformed to dict \n{}'.format(json))

        _check_response(json, call.get('nonrecoverable_response'), False)
        _check_response(json, call.get('response_expectation'), True)

        _translate_and_save(json, call.get('response_translation', None),
                            store_props)
    elif response_format == 'RAW':
        logger.debug('no action for raw response_format')
    else:
        raise WrongTemplateDataException(
            "Response_format {} is not supported. "
            "Only json or raw response_format is supported".format(
                response_format))


def _check_response(json, response, is_recoverable):
    if not is_recoverable:
        logger.debug(
            '_check_response (nonrecoverable)\n json:{}\n '
            'response:{} \n'.format(
                json, response))
    else:
        logger.debug(
            '_check_response (recoverable)\n json:{}\n '
            'response:{} \n'.format(
                json, response))

    if not response:
        return

    if not isinstance(response, list) and not is_recoverable:
        raise WrongTemplateDataException(
            "Response (nonrecoverable) had to be list. "
            "Type {} not supported. ".format(
                type(response)))

    if not isinstance(response, list) and is_recoverable:
        raise WrongTemplateDataException(
            "Response (recoverable) had to be list. "
            "Type {} not supported. ".format(
                type(response)))

    if isinstance(response[0], list):
        for item in response:
            _check_response(json, item, is_recoverable)
    else:
        pattern = response.pop(-1)
        for key in response:

            try:
                json = json[key]
            except (IndexError, KeyError):
                raise ExpectationException(
                        'No key or index "{}" in json {}'.format(key, json))

        if re.match(str(pattern), str(json)) and not is_recoverable:
            raise NonRecoverableResponseException(
                "Giving up... \n"
                "Response value: "
                "{} matches regexp:{} from nonrecoverable_response. ".format(
                    str(json), str(pattern)))
        if not re.match(str(pattern), str(json)) and is_recoverable:
            raise RecoverableResponseException(
                "Trying one more time...\n"
                "Response value:{} does not match regexp: {} "
                "from response_expectation".format(
                    str(json), str(pattern)))


def _check_if_v2(response_translation):
    # check if response_translation is list of list of 2 elements
    if isinstance(response_translation, list) and \
            isinstance(response_translation[0], list) and \
            len(response_translation[0]) == 2 and \
            isinstance(response_translation[0][0], list) and \
            isinstance(response_translation[0][1], list):
        return True
    return False


def _translate_and_save(response_json, response_translation, runtime_dict):
    if _check_if_v2(response_translation):
        _translate_and_save_v2(response_json, response_translation,
                               runtime_dict)
    else:
        _translate_and_save_v1(response_json, response_translation,
                               runtime_dict)


def _translate_and_save_v2(response_json, response_translation, runtime_dict):
    for translation in response_translation:
        json = response_json
        for idx, key in enumerate(translation[0]):
            if isinstance(key, list):
                _prepare_runtime_props_for_list(runtime_dict,
                                                translation[1],
                                                len(json))
                for response_list_idx, response_list_value in enumerate(json):
                    list_path = translation[0][idx+1:]
                    list_path.insert(0, key[0])
                    list_path.insert(0, response_list_idx)
                    list_path_arg = [[
                        list_path,
                        _prepare_runtime_props_path_for_list(
                            translation[1], response_list_idx)
                    ]]
                    _translate_and_save_v2(json, list_path_arg, runtime_dict)
                return
            else:
                json = json[key]
        _save(runtime_dict, translation[1], json)


def _translate_and_save_v1(response_json, response_translation, runtime_dict):
    if isinstance(response_translation, list):
        for idx, val in enumerate(response_translation):
            if isinstance(val, (list, dict)):
                _translate_and_save_v1(response_json[idx], val, runtime_dict)
            else:
                _save(runtime_dict, response_translation, response_json)
    elif isinstance(response_translation, dict):
        for key, value in response_translation.items():
            _translate_and_save_v1(response_json[key], value, runtime_dict)


def _save(runtime_properties_dict_or_subdict, list, value):
    first_el = list.pop(0)
    if len(list) == 0:
        runtime_properties_dict_or_subdict[first_el] = value
    else:
        runtime_properties_dict_or_subdict[
            first_el] = \
                runtime_properties_dict_or_subdict.get(
                    first_el, {}) if isinstance(
            runtime_properties_dict_or_subdict, dict) else \
                runtime_properties_dict_or_subdict[first_el]
        _save(runtime_properties_dict_or_subdict[first_el], list, value)


def _prepare_runtime_props_path_for_list(runtime_props_path, idx):
    path = list(runtime_props_path)
    last_one = path[-1]
    if isinstance(last_one, list):
        path.pop()
        path.append(idx)
        path.extend(last_one)
    else:
        path.append(idx)
    return path


def _prepare_runtime_props_for_list(runtime_props, runtime_props_path, count):
    for l_idx, value in enumerate(runtime_props_path):
        if value == runtime_props_path[-1] or \
                isinstance(runtime_props_path[l_idx+1], list):
            runtime_props[value] = [{}] * count
            return
        else:
            runtime_props[value] = runtime_props.get(value, {})
            runtime_props = runtime_props[value]
