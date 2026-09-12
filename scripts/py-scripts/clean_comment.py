import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "py-libraries"))
from utilities import remove_comments_and_docstrings

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remove comments and docstrings from files.")
    parser.add_argument("path", help="Path to a file or folder to clean.")
    args = parser.parse_args()
    
    if os.path.isdir(args.path):
        for root, dirs, files in os.walk(args.path):
            if 'node_modules' in root.split(os.sep):
                continue
            for file in files:
                filepath = os.path.join(root, file)
                remove_comments_and_docstrings(filepath)
    else:
        remove_comments_and_docstrings(args.path)

