import re
import os
import argparse

def remove_comments_and_docstrings(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    with open(filepath, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Remove docstrings (triple double quotes)
    dq = chr(34)
    docstring_pattern = dq + dq + dq + r'[\s\S]*?' + dq + dq + dq
    content = re.sub(docstring_pattern, '', content)
    
    # Remove SQL style comments
    content = re.sub(r'--.*', '', content)
    
    # Remove Python style comments
    content = re.sub(r'#.*', '', content)
    
    # Remove empty lines resulting from cleanup
    lines = [line for line in content.split('\n') if line.strip()]
    
    with open(filepath, 'w', encoding='utf-8') as file:
        file.write('\n'.join(lines))
    print(f"Cleaned: {filepath}")

def main():
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

if __name__ == "__main__":
    main()

