import os
import json
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')

PAGES = [
    'index.html',
    'merge-pdf.html',
    'split-pdf.html',
    'compress-pdf.html',
    'ocr-pdf.html',
    'summarize-pdf.html',
    'chat-pdf.html',
    'ai-resume-builder.html',
    'pdf-to-word.html'
]

class SEOParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.meta_desc = None
        self.h1_count = 0
        self.h1_texts = []
        self.canonical = None
        self.json_ld = []
        self.in_title = False
        self.in_script = False
        self.in_h1 = False
        self.h1_content = []
        self.script_type = None
        self.script_content = []
        self.styles = []
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == 'title':
            self.in_title = True
        elif tag == 'meta' and attrs_dict.get('name') == 'description':
            self.meta_desc = attrs_dict.get('content')
        elif tag == 'link' and attrs_dict.get('rel') == 'canonical':
            self.canonical = attrs_dict.get('href')
        elif tag == 'link' and attrs_dict.get('rel') == 'stylesheet':
            if 'href' in attrs_dict:
                self.styles.append(attrs_dict['href'])
        elif tag == 'script':
            self.script_type = attrs_dict.get('type')
            if self.script_type == 'application/ld+json':
                self.in_script = True
                self.script_content = []
            if 'src' in attrs_dict:
                self.scripts.append(attrs_dict['src'])
        elif tag == 'h1':
            self.h1_count += 1
            self.in_h1 = True
            self.h1_content = []

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        elif self.in_script:
            self.script_content.append(data)
        elif self.in_h1:
            self.h1_content.append(data)

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
        elif tag == 'script' and self.in_script:
            self.in_script = False
            self.json_ld.append("".join(self.script_content))
        elif tag == 'h1':
            self.in_h1 = False
            self.h1_texts.append("".join(self.h1_content).strip())

def verify_files():
    print("==================================================")
    print("  AI DocMaster — Local SEO & Technical Verification")
    print("==================================================")
    
    titles = set()
    descriptions = set()
    failed = False

    for page in PAGES:
        path = os.path.join(FRONTEND_DIR, page)
        if not os.path.exists(path):
            print(f"[FAIL] File not found: {page}")
            failed = True
            continue

        with open(path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        parser = SEOParser()
        parser.feed(html_content)

        print(f"\nAnalyzing: {page}")
        
        # 1. Check title
        title = parser.title.strip()
        if not title:
            print("  [FAIL] Title is empty")
            failed = True
        else:
            print(f"  [OK] Title: '{title}'")
            if title in titles:
                print(f"  [FAIL] Duplicate Title detected!")
                failed = True
            titles.add(title)

        # 2. Check description
        desc = parser.meta_desc
        if not desc:
            print("  [FAIL] Meta description is missing")
            failed = True
        else:
            print(f"  [OK] Meta description: '{desc[:60]}...'")
            if desc in descriptions:
                print(f"  [FAIL] Duplicate Meta Description detected!")
                failed = True
            descriptions.add(desc)

        # 3. Check H1 count
        if parser.h1_count != 1:
            print(f"  [FAIL] Expected exactly 1 H1 tag, found {parser.h1_count} ({parser.h1_texts})")
            failed = True
        else:
            print(f"  [OK] Single H1: '{parser.h1_texts[0]}'")

        # 4. Check canonical
        expected_canonical = f"http://localhost:5500/{page}"
        if page == 'index.html':
            expected_canonical = "http://localhost:5500/index.html"
        
        if parser.canonical != expected_canonical:
            print(f"  [FAIL] Canonical link mismatch. Found: {parser.canonical}, Expected: {expected_canonical}")
            failed = True
        else:
            print(f"  [OK] Canonical matches: {parser.canonical}")

        # 5. Check JSON-LD Structured Data
        if not parser.json_ld:
            print("  [FAIL] JSON-LD block is missing")
            failed = True
        else:
            for jld_str in parser.json_ld:
                try:
                    jld_data = json.loads(jld_str)
                    print(f"  [OK] Valid JSON-LD Schema: type='{jld_data.get('@type')}'")
                except Exception as e:
                    print(f"  [FAIL] Failed to parse JSON-LD: {str(e)}")
                    failed = True

        # 6. Check minified asset usage
        style_links = parser.styles
        script_links = parser.scripts

        has_min_style = any('style.min.css' in s for s in style_links)
        has_min_landing = any('landing.min.css' in s for s in style_links)
        has_min_feedback = any('feedback.min.js' in s for s in script_links)

        if not has_min_style:
            print(f"  [FAIL] Missing style.min.css. Stylesheet links: {style_links}")
            failed = True
        if not has_min_landing:
            print(f"  [FAIL] Missing landing.min.css. Stylesheet links: {style_links}")
            failed = True
        if not has_min_feedback:
            print(f"  [FAIL] Missing feedback.min.js. Scripts loaded: {script_links}")
            failed = True
        
        if has_min_style and has_min_landing and has_min_feedback:
            print("  [OK] Minified assets linked properly")

    # 7. Verify sitemap.xml structure
    sitemap_path = os.path.join(FRONTEND_DIR, 'sitemap.xml')
    if not os.path.exists(sitemap_path):
        print("\n[FAIL] sitemap.xml is missing")
        failed = True
    else:
        try:
            tree = ET.parse(sitemap_path)
            root = tree.getroot()
            # Handle XML namespace
            ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            urls = [loc.text for loc in root.findall('.//ns:loc', ns)]
            print(f"\n[OK] sitemap.xml parsed. Found {len(urls)} URLs:")
            for url in urls:
                print(f"  - {url}")
            
            # Verify match with our pages list
            for p in PAGES:
                expected_url = f"http://localhost:5500/{p}"
                if expected_url not in urls:
                    print(f"  [FAIL] Expected URL {expected_url} missing from sitemap.xml")
                    failed = True
        except Exception as e:
            print(f"\n[FAIL] Failed to parse sitemap.xml: {str(e)}")
            failed = True

    # 8. Verify robots.txt structure
    robots_path = os.path.join(FRONTEND_DIR, 'robots.txt')
    if not os.path.exists(robots_path):
        print("\n[FAIL] robots.txt is missing")
        failed = True
    else:
        with open(robots_path, 'r') as r:
            lines = r.readlines()
        has_sitemap_directive = any(line.strip().startswith('Sitemap:') for line in lines)
        if not has_sitemap_directive:
            print("\n[FAIL] robots.txt is missing Sitemap directive")
            failed = True
        else:
            print("\n[OK] robots.txt has Sitemap directive")

    print("\n--------------------------------------------------")
    if failed:
        print("  [FAIL] SEO VERIFICATION FAILED! Please review logs.")
        exit(1)
    else:
        print("  [SUCCESS] ALL SEO TESTS PASSED SUCCESSFULLY!")
        exit(0)

if __name__ == '__main__':
    verify_files()
