import os
import ast
import sys

imports = set()
for r, d, f in os.walk('c:/Users/kishu/Desktop/Ai Docmaster/backend'):
    if 'venv' in r or '__pycache__' in r:
        continue
    for file in f:
        if file.endswith('.py'):
            try:
                tree = ast.parse(open(os.path.join(r, file), 'r', encoding='utf-8').read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for n in node.names:
                            imports.add(n.name.split('.')[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.add(node.module.split('.')[0])
            except Exception as e:
                pass

print(sorted(list(imports)))
