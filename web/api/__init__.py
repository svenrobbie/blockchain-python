# coding:utf-8
"""
Web API Module

Initializes path for all API modules.
"""
import sys
import os

_api_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(os.path.dirname(_api_dir))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
