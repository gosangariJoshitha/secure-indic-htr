"""scripts/check_imports.py
Simple import checker for critical OCR and app modules.
Runs under the project's venv to surface missing dependencies or import errors.
"""
import traceback
import os
import sys

# Ensure repository root is on sys.path so package imports work when this
# script is executed from the scripts/ folder.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

modules = [
    'app_pages.OCR',
    'utils.layout_pipeline',
    'utils.predictor',
    'utils.segment',
    'utils.exporters',
    'utils.helpers',
    'components.ui_helpers',
]

def try_import(name):
    print(f"Importing {name}...")
    try:
        __import__(name)
        print(f"  OK: {name}")
    except Exception as e:
        print(f"  ERROR importing {name}: {e}")
        traceback.print_exc()

if __name__ == '__main__':
    for m in modules:
        try_import(m)
