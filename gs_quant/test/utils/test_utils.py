"""
Copyright 2019 Goldman Sachs.
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""
import json
import pathlib
from json.encoder import JSONEncoder

import pytest

from gs_quant.test.mock_data_test_utils import did_anything_fail, did_anything_run
from gs_quant.test.utils.mock_request import MockRequest


@pytest.mark.second_to_last
@pytest.mark.fixmockdata
def test_fix_mock_data():
    # This will only be run if you use "--fixmockdata" option to pytest
    if did_anything_fail():
        pytest.skip("Skipping test as another test failed")
    if not did_anything_run():
        pytest.skip("Skipping test as nothing ran or not setup correctly")
    MockRequest.reindex_test_files()
    MockRequest.remove_unused_files()


@pytest.mark.order("last")
def test_mock_data_file_sanity():
    # Important that this test runs last, it asserts all the test files are used so we can cleanup unused ones
    saved_files = MockRequest.get_saved_files()
    assert [] == saved_files, 'Did you accidentally commit with save_files=True?!'

    tests_passed = not did_anything_fail()

    suffix = '(Other tests FAILED this is probably a red herring)' if not tests_passed else \
        'Run pytest with --fixmockdata to fix this!'

    bad_index = MockRequest.reindex_test_files(report_only=True, log=tests_passed)
    assert bad_index == tuple(), f'Files with bad index. {suffix}'

    unused_files = MockRequest.get_unused_files(log=tests_passed)
    assert unused_files == tuple(), f'Cleanup your unused test files! {suffix}'


def _remove_unwanted(json_text):
    json_dict = json.loads(json_text)
    if "asOfTime" in json_dict:
        del json_dict["asOfTime"]
    return json_dict


def load_json_from_resource(test_file_name, json_file_name):
    with open(pathlib.Path(__file__).parents[1] / f'resources/{test_file_name}/{json_file_name}') as json_data:
        return json.load(json_data)


def mock_request(method, path, payload, test_file_name):
    queries = {
        'assetsDataGSNWithRic':
            '{"asOfTime": "2019-05-16T21:18:18.294Z", "limit": 4, "where": {"ric": ["GS.N"]}, "fields": ["ric", "id"]}',
        'assetsDataGSNWithId':
            '{"limit": 4, "fields": ["id", "ric"], "where": {"id": ["123456MW5E27U123456"]}}',
        'assetsDataSPXWithRic':
            '{"where": {"ric": [".SPX"]}, "limit": 4, "fields": ["ric", "id"]}',
        'assetsDataSPXWithId':
            '{"limit": 4, "fields": ["id", "ric"], "where": {"id": ["456123MW5E27U123456"]}}',
        'dataQueryRic':
            '{"fields": ["adjustedTradePrice"],'
            ' "format": "MessagePack", "where": {"assetId": ["123456MW5E27U123456"]}}',
        'dataQuerySPX':
            '{"fields": ["adjustedTradePrice"], "format": "MessagePack", "where": {"assetId": ["456123MW5E27U123456"]}}'
    }
    payload = _remove_unwanted(json.dumps(payload, cls=JSONEncoder) if payload else '{}')
    if method == 'GET':
        if path == '/data/datasets/TREOD':
            return load_json_from_resource(test_file_name, 'datasets_treod_response.json')
    elif method == 'POST':
        if path == '/assets/data/query':
            if payload == _remove_unwanted(queries['assetsDataGSNWithRic']) or \
                    payload == _remove_unwanted(queries['assetsDataGSNWithId']):
                return load_json_from_resource(test_file_name, 'assets_data_query_response_gsn.json')
            elif payload == _remove_unwanted(queries['assetsDataSPXWithRic']) or \
                    payload == _remove_unwanted(queries['assetsDataSPXWithId']):
                return load_json_from_resource(test_file_name, 'assets_data_query_response_spx.json')
        elif path == '/data/TREOD/query':
            if payload == _remove_unwanted(queries['dataQueryRic']):
                return load_json_from_resource(test_file_name, 'treod_query_response_gsn.json')
            elif payload == _remove_unwanted(queries['dataQuerySPX']):
                return load_json_from_resource(test_file_name, 'treod_query_response_spx.json')
    raise Exception(f'Unhandled request. Method: {method}, Path: {path}, payload: {payload} not recognized.')
