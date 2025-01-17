#
# This module contains all the functionality related to the anonymous tracking of data-diff use.
#

import logging
import os
import json
import platform
from time import time
from typing import Any, Dict, Optional
import urllib.request
from uuid import uuid4

import toml

TRACK_URL = "https://api.perfalytics.com/track"
START_EVENT = "os_diff_run_start"
END_EVENT = "os_diff_run_end"
TOKEN = "ccb8c3a6-3b6f-445c-ad67-994efa7bd020"
TIMEOUT = 8

DEFAULT_PROFILE = os.path.expanduser("~/.datadiff.toml")


def _load_profile():
    try:
        with open(DEFAULT_PROFILE) as f:
            conf = toml.load(f)
    except FileNotFoundError:
        conf = {}

    if "anonymous_id" not in conf:
        conf["anonymous_id"] = str(uuid4())
        with open(DEFAULT_PROFILE, "w") as f:
            toml.dump(conf, f)
    return conf


g_tracking_enabled = True
g_anonymous_id = None


def disable_tracking():
    global g_tracking_enabled
    g_tracking_enabled = False


def is_tracking_enabled():
    return g_tracking_enabled


def get_anonymous_id():
    global g_anonymous_id
    if g_anonymous_id is None:
        profile = _load_profile()
        g_anonymous_id = profile["anonymous_id"]
    return g_anonymous_id


def create_start_event_json(diff_options: Dict[str, Any]):
    return {
        "event": "os_diff_run_start",
        "properties": {
            "distinct_id": get_anonymous_id(),
            "token": TOKEN,
            "time": time(),
            "os_type": os.name,
            "os_version": platform.platform(),
            "python_version": f"{platform.python_version()}/{platform.python_implementation()}",
            "diff_options": diff_options,
        },
    }


def create_end_event_json(
    is_success: bool,
    runtime_seconds: float,
    db1: str,
    db2: str,
    table1_count: int,
    table2_count: int,
    diff_count: int,
    error: Optional[str],
):
    return {
        "event": "os_diff_run_end",
        "properties": {
            "distinct_id": get_anonymous_id(),
            "token": TOKEN,
            "time": time(),
            "is_success": is_success,
            "runtime_seconds": runtime_seconds,
            "data_source_1_type": db1,
            "data_source_2_type": db2,
            "table_1_rows_cnt": table1_count,
            "table_2_rows_cnt": table2_count,
            "diff_rows_cnt": diff_count,
            "error_message": error,
        },
    }


def send_event_json(event_json):
    if not g_tracking_enabled:
        raise RuntimeError("Won't send; tracking is disabled!")

    headers = {"Content-Type": "application/json"}
    data = json.dumps(event_json).encode()
    try:
        req = urllib.request.Request(TRACK_URL, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as f:
            res = f.read()
            if f.code != 200:
                raise RuntimeError(res)
    except Exception as e:
        logging.debug(f"Failed to post to freshpaint: {e}")
