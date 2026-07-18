import os
import re

# Base workspace path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')

def minify_css(css_content):
    # Remove block comments
    css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
    # Compress whitespace
    css_content = re.sub(r'\s+', ' ', css_content)
    css_content = re.sub(r'\s*([\{\};:,])\s*', r'\1', css_content)
    return css_content.strip()

def minify_js(js_content):
    # Tokenizer pattern to match strings, comments, and regular code chunks safely
    pattern = re.compile(
        r'(?P<dquote>"([^"\\]|\\.)*")|'
        r'(?P<squote>\'([^\'\\]|\\.)*\')|'
        r'(?P<template>`([^`\\]|\\.)*`)|'
        r'(?P<block>/\*.*?\*/)|'
        r'(?P<line>//[^\r\n]*)|'
        r'(?P<other>[^"\'`/]+|/[^/*"\'`]+)',
        re.DOTALL | re.MULTILINE
    )
    
    result = []
    for m in pattern.finditer(js_content):
        d = m.groupdict()
        if d['block'] or d['line']:
            # Comments are stripped out
            continue
        elif d['dquote']:
            result.append(d['dquote'])
        elif d['squote']:
            result.append(d['squote'])
        elif d['template']:
            result.append(d['template'])
        else:
            result.append(m.group(0))
            
    minified = "".join(result)
    
    # Safely compress whitespace by removing empty lines and trimming margins
    # keeping newlines prevents ASI (automatic semicolon insertion) parser failures
    lines = minified.splitlines()
    cleaned_lines = []
    for line in lines:
        line_stripped = line.strip()
        if line_stripped:
            cleaned_lines.append(line_stripped)
            
    return "\n".join(cleaned_lines)

def run_minification():
    # 1. Minify style.css
    style_path = os.path.join(FRONTEND_DIR, 'css', 'style.css')
    style_min_path = os.path.join(FRONTEND_DIR, 'css', 'style.min.css')
    if os.path.exists(style_path):
        with open(style_path, 'r', encoding='utf-8') as f:
            content = f.read()
        minified = minify_css(content)
        with open(style_min_path, 'w', encoding='utf-8') as f:
            f.write(minified)
        print(f"[OK] Minified style.css: {len(content)} -> {len(minified)} bytes")
    
    # 2. Minify landing.css
    landing_path = os.path.join(FRONTEND_DIR, 'css', 'landing.css')
    landing_min_path = os.path.join(FRONTEND_DIR, 'css', 'landing.min.css')
    if os.path.exists(landing_path):
        with open(landing_path, 'r', encoding='utf-8') as f:
            content = f.read()
        minified = minify_css(content)
        with open(landing_min_path, 'w', encoding='utf-8') as f:
            f.write(minified)
        print(f"[OK] Minified landing.css: {len(content)} -> {len(minified)} bytes")

    # 3. Minify feedback.js
    feedback_path = os.path.join(FRONTEND_DIR, 'js', 'feedback.js')
    feedback_min_path = os.path.join(FRONTEND_DIR, 'js', 'feedback.min.js')
    if os.path.exists(feedback_path):
        with open(feedback_path, 'r', encoding='utf-8') as f:
            content = f.read()
        minified = minify_js(content)
        with open(feedback_min_path, 'w', encoding='utf-8') as f:
            f.write(minified)
        print(f"[OK] Minified feedback.js: {len(content)} -> {len(minified)} bytes")

if __name__ == '__main__':
    run_minification()
