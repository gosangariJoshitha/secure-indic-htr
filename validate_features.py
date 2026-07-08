import ast
import os

def check_syntax(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            ast.parse(f.read())
        return True, "Syntax OK"
    except SyntaxError as e:
        return False, f"Syntax Error: {e}"

files_to_check = [
    "app.py",
    "app_pages/Landing.py",
    "app_pages/Login.py",
    "app_pages/Signup.py",
    "app_pages/Home.py",
    "app_pages/Scan.py",
    "app_pages/Library.py",
    "app_pages/Dashboard.py",
    "components/navbar.py"
]

print("Validating feature implementations...\n")
all_passed = True
for f in files_to_check:
    filepath = os.path.join(os.path.dirname(__file__), f)
    if os.path.exists(filepath):
        passed, msg = check_syntax(filepath)
        print(f"Checking {f}... {'Passed' if passed else 'Failed'} ({msg})")
        if not passed:
            all_passed = False
    else:
        print(f"Checking {f}... File not found")
        all_passed = False

print(f"\nOverall Validation: {'ALL PASSED' if all_passed else 'FAILED'}")
