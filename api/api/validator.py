# Copyright (C) 2022, Wrixte
# Created by Wrixte InfoSec Pvt Ltd. <info@wrixte.co>.
# This program is a free software; you can redistribute it and/or modify it under the terms of GPLv2

import os
import re
from typing import Dict, List

from defusedxml import ElementTree as ET
from jsonschema import draft4_format_checker

from wazuh.core import common

_alphanumeric_param = re.compile(r'^[\w,\-.+\s:]+$')
_symbols_alphanumeric_param = re.compile(r'^[\w,<>!\-.+\s:/()\[\]\'\"|=~#]+$')
_array_numbers = re.compile(r'^\d+(,\d+)*$')
_array_names = re.compile(r'^[\w\-.%]+(,[\w\-.%]+)*$')
_base64 = re.compile(r'^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$')
_boolean = re.compile(r'^true$|^false$')
_dates = re.compile(r'^\d{8}$')
_empty_boolean = re.compile(r'^$|(^true$|^false$)')
_group_names = re.compile(r'^(?!^(\.{1,2}|all)$)[\w.\-]+$')
_group_names_or_all = re.compile(r'^(?!^\.{1,2}$)[\w.\-]+$')
_hashes = re.compile(r'^(?:[\da-fA-F]{32})?$|(?:[\da-fA-F]{40})?$|(?:[\da-fA-F]{56})?$|(?:[\da-fA-F]{64})?$|(?:['
                     r'\da-fA-F]{96})?$|(?:[\da-fA-F]{128})?$')
_ips = re.compile(
    r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?:/(?:[0-9]|[1-2]['
    r'0-9]|3[0-2]))?$|^any$|^ANY$')
_iso8601_date = re.compile(r'^([0-9]{4})-(1[0-2]|0[1-9])-(3[01]|0[1-9]|[12][0-9])$')
_iso8601_date_time = re.compile(
    r'^([0-9]{4})-(1[0-2]|0[1-9])-(3[01]|0[1-9]|[12][0-9])[tT](2[0-3]|[01][0-9]):([0-5][0-9]):([0-5][0-9])(\.['
    r'0-9]+)?([zZ]|[+-](?:2[0-3]|[01][0-9]):[0-5][0-9])$')
_names = re.compile(r'^[\w\-.%]+$')
_numbers = re.compile(r'^\d+$')
_numbers_or_all = re.compile(r'^(\d+|all)$')
_wazuh_key = re.compile(r'[a-zA-Z0-9]+$')
_wazuh_version = re.compile(r'^(?:wazuh |)v?\d+\.\d+\.\d+$', re.IGNORECASE)
_paths = re.compile(r'^[\w\-.\\/:]+$')
_cdb_filename_path = re.compile(r'^[\-\w]+$')
_xml_filename_path = re.compile(r'^[\w\-]+\.xml$')
_xml_filename = re.compile(r'^[\w\-]+\.xml(,[\w\-]+\.xml)*$')
_query_param = re.compile(r"^[\w.\-]+(?:=|!=|<|>|~)[\w.\- ]+(?:[;,][\w.\-]+(?:=|!=|<|>|~)[\w.\- ]+)*$")
_ranges = re.compile(r'[\d]+$|^[\d]{1,2}-[\d]{1,2}$')
_get_dirnames_path = re.compile(r'^(((etc|ruleset)/(decoders|rules)[\w\-/]*)|(etc/lists[\w\-/]*))$')
_search_param = re.compile(r'^[^;|&^*>]+$')
_sort_param = re.compile(r'^[\w_\-,\s+.]+$')
_timeframe_type = re.compile(r'^(\d+[dhms]?)$')
_type_format = re.compile(r'^xml$|^json$')
_yes_no_boolean = re.compile(r'^yes$|^no$')

security_config_schema = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "auth_token_exp_timeout": {"type": "integer"},
        "rbac_mode": {"type": "string", "enum": ["white", "black"]}
    }
}

api_config_schema = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "host": {"type": "string"},
        "port": {"type": "number"},
        "use_only_authd": {"type": "boolean"},  # Deprecated. To be removed on later versions
        "drop_privileges": {"type": "boolean"},
        "experimental_features": {"type": "boolean"},
        "max_upload_size": {"type": "integer", "minimum": 0},
        "intervals": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "request_timeout": {"type": "number", "minimum": 0}
            },
        },
        "https": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "enabled": {"type": "boolean"},
                "key": {"type": "string",
                        "pattern": r"^[\w\-.]+$"},
                "cert": {"type": "string",
                         "pattern": r"^[\w\-.]+$"},
                "use_ca": {"type": "boolean"},
                "ca": {"type": "string",
                       "pattern": r"^[\w\-.]+$"},
                "ssl_protocol": {"type": "string", "enum": ["tls", "tlsv1", "tlsv1.1", "tlsv1.2", "TLS",
                                                            "TLSv1", "TLSv1.1", "TLSv1.2"]},
                "ssl_ciphers": {"type": "string"}
            },
        },
        "logs": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "level": {"type": "string"},
                "path": {"type": "string"},  # Deprecated. To be removed on later versions
                "format": {"type": "string", "enum": ["plain", "json", "plain,json", "json,plain"]}
            },
        },
        "cors": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "enabled": {"type": "boolean"},
                "source_route": {"type": "string"},
                "expose_headers": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}}
                    ]
                },
                "allow_headers": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}}
                    ]
                },
                "allow_credentials": {"type": "boolean"},
            },
        },
        "cache": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "enabled": {"type": "boolean"},
                "time": {"type": "number"},
            },
        },
        "access": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "max_login_attempts": {"type": "integer"},
                "block_time": {"type": "integer"},
                "max_request_per_minute": {"type": "integer"},
            },
        },
        "remote_commands": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "localfile": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "exceptions": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "wodle_command": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "exceptions": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
        },
    },
}


def check_exp(exp: str, regex: re.Pattern) -> bool:
    """Function to check if an expression matches a regex.
    
    Parameters
    ----------
    exp : str
        Expression to check.
    regex : re.Pattern
        Regular Expression used to do the matching.

    Returns
    -------
    bool
        True if expression is matched. False otherwise.
    """
    if not isinstance(exp, str):
        return True
    return regex.match(exp) is not None


def check_xml(xml_string: str) -> bool:
    """Function to check if an XML string is correct.
    
    Parameters
    ----------
    xml_string : str
        XML string to check.

    Returns
    -------
    bool
        True if the XML is OK. False otherwise.
    """
    try:
        ET.fromstring(xml_string)
    except ET.ParseError:
        return False
    except Exception:
        return False

    return True


def allowed_fields(filters: Dict) -> List:
    """Return a list with allowed fields.
    
    Parameters
    ----------
    filters : dict
        Dictionary with valid fields.

    Returns
    -------
    list
        List with allowed filters.
    """
    return [field for field in filters]


def is_safe_path(path: str, basedir: str = common.WAZUH_PATH, relative: bool = True) -> bool:
    """Check if a path is correct.
    
    Parameters
    ----------
    path : str
        Path to be checked.
    basedir : str
        Wazuh installation directory.
    relative : bool
        True if path is relative. False otherwise (absolute).

    Returns
    -------
    bool
        True if path is correct. False otherwise.
    """
    # Protect path
    if './' in path or '../' in path:
        return False

    # Resolve symbolic links if present
    full_path = os.path.realpath(os.path.join(basedir, path.lstrip("/")) if relative else path)
    full_basedir = os.path.abspath(basedir)

    return os.path.commonpath([full_path, full_basedir]) == full_basedir


@draft4_format_checker.checks("alphanumeric")
def format_alphanumeric(value):
    return check_exp(value, _alphanumeric_param)


@draft4_format_checker.checks("alphanumeric_symbols")
def format_alphanumeric_symbols(value):
    return check_exp(value, _symbols_alphanumeric_param)


@draft4_format_checker.checks("base64")
def format_base64(value):
    return check_exp(value, _base64)


@draft4_format_checker.checks("get_dirnames_path")
def format_get_dirnames_path(relative_path):
    if not is_safe_path(relative_path):
        return False

    return check_exp(relative_path, _get_dirnames_path)


@draft4_format_checker.checks("hash")
def format_hash(value):
    return check_exp(value, _hashes)


@draft4_format_checker.checks("names")
def format_names(value):
    return check_exp(value, _names)


@draft4_format_checker.checks("numbers")
def format_numbers(value):
    return check_exp(value, _numbers)


@draft4_format_checker.checks("numbers_or_all")
def format_numbers_or_all(value):
    return check_exp(value, _numbers_or_all)


@draft4_format_checker.checks("cdb_filename_path")
def format_cdb_filename_path(value):
    return check_exp(value, _cdb_filename_path)


@draft4_format_checker.checks("xml_filename")
def format_xml_filename(value):
    return check_exp(value, _xml_filename)


@draft4_format_checker.checks("xml_filename_path")
def format_xml_filename_path(value):
    return check_exp(value, _xml_filename_path)


@draft4_format_checker.checks("path")
def format_path(value):
    if not is_safe_path(value):
        return False
    return check_exp(value, _paths)


@draft4_format_checker.checks("wazuh_path")
def format_wazuh_path(value):
    if not is_safe_path(value, relative=False):
        return False
    return check_exp(value, _paths)


@draft4_format_checker.checks("query")
def format_query(value):
    return check_exp(value, _query_param)


@draft4_format_checker.checks("range")
def format_range(value):
    return check_exp(value, _ranges)


@draft4_format_checker.checks("search")
def format_search(value):
    return check_exp(value, _search_param)


@draft4_format_checker.checks("sort")
def format_sort(value):
    return check_exp(value, _sort_param)


@draft4_format_checker.checks("timeframe")
def format_timeframe(value):
    return check_exp(value, _timeframe_type)


@draft4_format_checker.checks("wazuh_key")
def format_wazuh_key(value):
    return check_exp(value, _wazuh_key)


@draft4_format_checker.checks("wazuh_version")
def format_wazuh_version(value):
    return check_exp(value, _wazuh_version)


@draft4_format_checker.checks("date")
def format_date(value):
    return check_exp(value, _iso8601_date)


@draft4_format_checker.checks("date-time")
def format_datetime(value):
    return check_exp(value, _iso8601_date_time)


@draft4_format_checker.checks("hash_or_empty")
def format_hash_or_empty(value):
    return True if value == "" else format_hash(value)


@draft4_format_checker.checks("names_or_empty")
def format_names_or_empty(value):
    return True if value == "" else format_names(value)


@draft4_format_checker.checks("numbers_or_empty")
def format_numbers_or_empty(value):
    return True if value == "" else format_numbers(value)


@draft4_format_checker.checks("date-time_or_empty")
def format_datetime_or_empty(value):
    return True if value == "" else format_datetime(value)


@draft4_format_checker.checks("group_names")
def format_group_names(value):
    return check_exp(value, _group_names)


@draft4_format_checker.checks("group_names_or_all")
def format_group_names_or_all(value):
    return check_exp(value, _group_names_or_all)
