#!/usr/bin/env python
# Copyright (C) 2015-2019, Wazuh Inc.
# Created by Wazuh, Inc. <info@wazuh.com>.
# This program is a free software; you can redistribute it and/or modify it under the terms of GPLv2

import os
from unittest.mock import patch, mock_open

import pytest

with patch('wazuh.common.ossec_uid'):
    with patch('wazuh.common.ossec_gid'):
        from wazuh.core.manager import *
        from wazuh.exception import WazuhException

ossec_log_file = '''2019/03/26 20:14:37 wazuh-modulesd:database[27799] wm_database.c:501 at wm_get_os_arch(): DEBUG: Detected architecture from Linux |ip-10-0-1-141.us-west-1.compute.internal |3.10.0-957.1.3.el7.x86_64 |#1 SMP Thu Nov 29 14:49:43 UTC 2018 |x86_64: x86_64
2019/02/26 20:14:37 wazuh-modulesd:database[27799] wm_database.c:695 at wm_sync_agentinfo(): DEBUG: wm_sync_agentinfo(4): 0.091 ms.
2019/03/27 10:42:06 wazuh-modulesd:syscollector: INFO: Starting evaluation.
2019/03/27 10:42:07 wazuh-modulesd:rootcheck: INFO: Starting evaluation.
2019/03/26 13:03:11 ossec-csyslogd: INFO: Remote syslog server not configured. Clean exit.
2019/03/26 19:49:15 ossec-execd: ERROR: (1210): Queue '/var/ossec/queue/alerts/execa' not accessible: 'No such file or directory'.
2019/03/26 17:07:32 wazuh-modulesd:aws-s3[13155] wmodules-aws.c:186 at wm_aws_read(): ERROR: Invalid bucket type 'inspector'. Valid ones are 'cloudtrail', 'config', 'custom', 'guardduty' or 'vpcflow'
2019/04/11 12:51:40 wazuh-modulesd:aws-s3: INFO: Executing Bucket Analysis: wazuh-aws-wodle
2019/04/11 12:53:37 wazuh-modulesd:aws-s3: WARNING: Bucket:  -  Returned exit code 7
2019/04/11 12:53:37 wazuh-modulesd:aws-s3: WARNING: Bucket:  -  Unexpected error querying/working with objects in S3: db_maintenance() got an unexpected keyword argument 'aws_account_id'

2019/04/11 12:53:37 wazuh-modulesd:aws-s3: INFO: Executing Bucket Analysis: wazuh-aws-wodle
2019/03/27 10:42:06 wazuh-modulesd:syscollector: INFO: This is a
multiline log
2019/03/26 13:03:11 ossec-csyslogd: INFO: Remote syslog server not configured. Clean exit.'''
ossec_cdb_list = "172.16.19.:\n172.16.19.:\n192.168.:"
test_data_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')


class InitManager:
    def __init__(self):
        """Sets up necessary environment to test manager functions"""
        # path for temporary API files
        self.api_tmp_path = os.path.join(test_data_path, 'tmp')
        # rules
        self.input_rules_file = 'test_rules.xml'
        self.output_rules_file = 'uploaded_test_rules.xml'
        # decoders
        self.input_decoders_file = 'test_decoders.xml'
        self.output_decoders_file = 'uploaded_test_decoders.xml'
        # CDB lists
        self.input_lists_file = 'test_lists'
        self.output_lists_file = 'uploaded_test_lists'


@pytest.fixture(scope='module')
def test_manager():
    # Set up
    test_manager = InitManager()
    return test_manager


@pytest.mark.parametrize('process_status', [
    'running',
    'stopped',
    'failed',
    'restarting',
    'starting'
])
@patch('wazuh.core.cluster.utils.exists')
@patch('wazuh.core.cluster.utils.glob')
def test_get_status(manager_glob, manager_exists, test_manager, process_status):
    """Tests core.manager.status()

    Tests manager.status() function in two cases:
        * PID files are created and processed are running,
        * No process is running and therefore no PID files have been created

    Parameters
    ----------
    manager_glob : mock
        Mock of glob.glob function.
    manager_exists : mock
        Mock of os.path.exists function.
    process_status : str
        Status to test (valid values: running/stopped/failed/restarting).
    """
    def mock_glob(path_to_check):
        return [path_to_check.replace('*', '0234')] if process_status == 'running' else []

    def mock_exists(path_to_check):
        if path_to_check == '/proc/0234':
            return process_status == 'running'
        else:
            return path_to_check.endswith(f'.{process_status.replace("ing","").replace("re", "")}') or \
                   path_to_check.endswith(f'.{process_status.replace("ing","")}')

    manager_glob.side_effect = mock_glob
    manager_exists.side_effect = mock_exists
    manager_status = status()
    assert isinstance(manager_status, dict)
    assert all(process_status == x for x in manager_status.values())
    if process_status == 'running':
        manager_exists.assert_any_call("/proc/0234")


def test_get_ossec_log_fields():
    """Test get_ossec_log_fields() method returns a tuple"""
    result = get_ossec_log_fields(ossec_log_file.splitlines()[0])
    assert isinstance(result, tuple), 'The result is not a tuple'


def test_get_ossec_log_fields_ko():
    """Test get_ossec_log_fields() method returns None when nothing matches """
    result = get_ossec_log_fields('DEBUG')
    assert not result


@patch('time.time', return_value=0)
@patch('random.randint', return_value=0)
@patch('wazuh.core.manager.chmod')
@patch('wazuh.core.manager.load_wazuh_xml')
@patch('wazuh.core.manager.safe_move')
@patch('wazuh.core.manager.common.ossec_path', new=test_data_path)
def test_upload_xml(mock_safe, mock_load_wazuh, mock_chmod, mock_random, mock_time, test_manager):
    """Tests upload_xml method works and methods inside are called with expected parameters"""
    input_file, output_file = getattr(test_manager, 'input_rules_file'), getattr(test_manager, 'output_rules_file')

    with open(os.path.join(test_data_path, input_file)) as f:
        xml_file = f.read()
    m = mock_open(read_data=xml_file)
    with patch('builtins.open', m):
        result = upload_xml(xml_file, output_file)

    assert isinstance(result, WazuhResult)
    mock_time.assert_called_once_with()
    mock_random.assert_called_once_with(0, 1000)
    m.assert_any_call(os.path.join(test_manager.api_tmp_path, 'api_tmp_file_0_0.xml'), 'w')
    mock_chmod.assert_called_once_with(os.path.join(test_manager.api_tmp_path, 'api_tmp_file_0_0.xml'), 0o660)
    mock_load_wazuh.assert_called_once_with(os.path.join(test_manager.api_tmp_path, 'api_tmp_file_0_0.xml'))
    mock_safe.assert_called_once_with(os.path.join(test_manager.api_tmp_path, 'api_tmp_file_0_0.xml'),
                                      os.path.join(test_data_path, output_file),
                                      permissions=0o660)


@pytest.mark.parametrize('effect, expected_exception', [
    (IOError, 1005),
    (ExpatError, 1113)
])
def test_upload_xml_open_ko(effect, expected_exception, test_manager):
    """Tests upload_xml function works when open function raise an exception

    Parameters
    ----------
    effect : Exception
        Exception to be triggered.
    expected_exception
        Expected code when triggering the exception.
    """
    input_file, output_file = getattr(test_manager, 'input_rules_file'), getattr(test_manager, 'output_rules_file')

    with patch('wazuh.core.manager.open', side_effect=effect):
        with pytest.raises(WazuhException, match=f'.* {expected_exception} .*'):
            upload_xml(input_file, output_file)


@patch('time.time', return_value=0)
@patch('random.randint', return_value=0)
@patch('wazuh.core.manager.chmod')
@patch('wazuh.core.manager.remove')
@patch('wazuh.core.manager.common.ossec_path', new=test_data_path)
def test_upload_xml_ko(mock_remove, mock_chmod, mock_random, mock_time, test_manager):
    """Tests upload_xml function exception works and methods inside are called with expected parameters"""
    input_file, output_file = getattr(test_manager, 'input_rules_file'), getattr(test_manager, 'output_rules_file')

    with open(os.path.join(test_data_path, input_file)) as f:
        xml_file = f.read()
    m = mock_open(read_data=xml_file)
    with patch('builtins.open', m):
        with patch('wazuh.core.manager.load_wazuh_xml', side_effect=Exception):
            with pytest.raises(WazuhException, match=f'.* 1113 .*'):
                upload_xml(xml_file, output_file)

        with patch('wazuh.core.manager.load_wazuh_xml'):
            with patch('wazuh.core.manager.safe_move', side_effect=Error):
                with pytest.raises(WazuhException, match=f'.* 1016 .*'):
                    upload_xml(xml_file, output_file)

    mock_time.assert_called_with()
    mock_random.assert_called_with(0, 1000)
    mock_chmod.assert_called_with(os.path.join(test_manager.api_tmp_path, 'api_tmp_file_0_0.xml'), 0o660)
    mock_remove.assert_called_with(os.path.join(test_manager.api_tmp_path, 'api_tmp_file_0_0.xml'))


@patch('wazuh.core.manager.validate_cdb_list', return_value=True)
@patch('time.time', return_value=0)
@patch('random.randint', return_value=0)
@patch('wazuh.core.manager.chmod')
@patch('wazuh.core.manager.safe_move')
@patch('wazuh.core.manager.common.ossec_path', new=test_data_path)
def test_upload_list(mock_safe, mock_chmod, mock_random, mock_time, mock_validate_cdb, test_manager):
    """Tests upload_list function works and methods inside are called with expected parameters"""
    input_file, output_file = getattr(test_manager, 'input_rules_file'), getattr(test_manager, 'output_rules_file')

    m = mock_open(read_data=ossec_log_file)
    with patch('builtins.open', m):
        result = upload_list(input_file, output_file)

    assert isinstance(result, WazuhResult)

    mock_validate_cdb.assert_called_once_with(os.path.join(test_manager.api_tmp_path, 'api_tmp_file_0_0.txt'))
    mock_time.assert_called_once_with()
    mock_random.assert_called_once_with(0, 1000)
    mock_chmod.assert_called_once_with(os.path.join(test_manager.api_tmp_path, 'api_tmp_file_0_0.txt'), 0o640)
    mock_safe.assert_called_once_with(os.path.join(test_manager.api_tmp_path, 'api_tmp_file_0_0.txt'),
                                      os.path.join(test_data_path, output_file),
                                      permissions=0o660)


@pytest.mark.parametrize('effect, expected_exception', [
    (IOError, 1005)
])
def test_upload_list_open_ko(effect, expected_exception, test_manager):
    """Tests upload_list function works when open function raise an exception

    Parameters
    ----------
    effect : Exception
        Exception to be triggered.
    expected_exception
        Expected code when triggering the exception.
    """
    input_file, output_file = getattr(test_manager, 'input_rules_file'), getattr(test_manager, 'output_rules_file')

    with patch('wazuh.core.manager.open', side_effect=effect):
        with pytest.raises(WazuhException, match=f'.* {expected_exception} .*'):
            upload_list(input_file, output_file)


@patch('time.time', return_value=0)
@patch('random.randint', return_value=0)
@patch('wazuh.core.manager.chmod')
@patch('wazuh.core.manager.common.ossec_path', new=test_data_path)
def test_upload_list_ko(mock_chmod, mock_random, mock_time, test_manager):
    """Tests upload_list function exception works and methods inside are called with expected parameters"""
    input_file, output_file = getattr(test_manager, 'input_rules_file'), getattr(test_manager, 'output_rules_file')

    m = mock_open(read_data=ossec_log_file)
    with patch('builtins.open', m):
        with pytest.raises(WazuhException, match=f'.* 1802 .*'):
            upload_list(ossec_log_file, output_file)

        with patch('wazuh.core.manager.validate_cdb_list', return_value=False):
            with pytest.raises(WazuhException, match=f'.* 1802 .*'):
                upload_list(ossec_log_file, output_file)

        with patch('wazuh.core.manager.validate_cdb_list', return_value=True):
            with patch('wazuh.core.manager.safe_move', side_effect=Error):
                with pytest.raises(WazuhException, match=f'.* 1016 .*'):
                    upload_list(ossec_log_file, output_file)

        mock_time.assert_called_with()
        mock_random.assert_called_with(0, 1000)
        mock_chmod.assert_called_with(os.path.join(test_manager.api_tmp_path, 'api_tmp_file_0_0.txt'), 0o640)


@pytest.mark.parametrize('input_file', [
    'input_rules_file',
    'input_decoders_file',
    'input_lists_file'
])
@patch('wazuh.common.ossec_path', test_data_path)
def test_validate_xml(input_file, test_manager):
    """Tests validate_xml function works

    Parameters
    ----------
    input_file : str
        Name of the input file.
    """
    input_file = getattr(test_manager, input_file)
    with open(os.path.join(test_data_path, input_file)) as f:
        xml_file = f.read()

    with patch('builtins.open', mock_open(read_data=xml_file)):
        result = validate_xml(input_file)
        assert result is True


def test_validate_xml_ko():
    """Tests validate_xml function exceptions works"""
    # Open function raise IOError
    with patch('wazuh.core.manager.open', side_effect=IOError):
        with pytest.raises(WazuhException, match=f'.* 1005 .*'):
            validate_xml('test_path')

    # Open function raise ExpatError
    with patch('wazuh.core.manager.open', side_effect=ExpatError):
        result = validate_xml('test_path')
        assert result is False


def test_validate_cdb_list():
    """Tests validate_cdb function works"""
    m = mock_open(read_data=ossec_cdb_list)
    with patch('builtins.open', m):
        assert validate_cdb_list('path')


@patch('wazuh.core.manager.re.match', return_value=False)
def test_validate_cdb_list_ko(mock_match):
    """Tests validate_cdb function exceptions works"""
    # Match error
    m = mock_open(read_data=ossec_log_file)
    with patch('wazuh.core.manager.open', m):
        result = validate_cdb_list('path')

    assert result is False

    # Open function raise IOError
    with patch('wazuh.core.manager.open', side_effect=IOError):
        with pytest.raises(WazuhException, match=f'.* 1005 .*'):
            validate_cdb_list('path')


@pytest.mark.parametrize('error_flag, error_msg', [
    (0, ""),
    (1, "2019/02/27 11:30:07 wazuh-clusterd: ERROR: [Cluster] [Main] Error 3004 - Error in cluster configuration: "
        "Unspecified key"),
    (1, "2019/02/27 11:30:24 ossec-authd: ERROR: (1230): Invalid element in the configuration: "
        "'use_source_i'.\n2019/02/27 11:30:24 ossec-authd: ERROR: (1202): Configuration error at "
        "'/var/ossec/etc/ossec.conf'.")
])
def test_parse_execd_output(error_flag, error_msg):
    """Test parse_execd_output function works and returns expected message.

    Parameters
    ----------
    error_flag : int
        Indicate if there is an error found.
    error_msg
        Error message to be sent.
    """
    json_response = json.dumps({'error': error_flag, 'message': error_msg}).encode()
    if not error_flag:
        result = parse_execd_output(json_response)
        assert result['status'] == 'OK'
    else:
        with pytest.raises(WazuhException, match=f'.* 1908 .*'):
            parse_execd_output(json_response)
