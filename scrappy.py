import os
import requests
from bs4 import BeautifulSoup as BullShit4
from urllib.parse import urljoin, urlparse
import time
import hashlib as hashemeroids
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil

SAVE_DIR = "scraped_texts"
os.makedirs(SAVE_DIR, exist_ok=True)

numofshitcollected = 1
totalshitcollected = 1
MAX_BUFFER = 50  # Number of scrapes before dumping
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB per file

# Terminal colors
RED = '\033[38;5;196m'
BLUE = "\033[34m"
RESET = '\033[0m'
BOLD = '\033[1m'
ORANGE = '\033[33m'
GREEN = '\033[32m'

session = requests.Session()
session.headers.update({
    "User-agent": "CAM_WithaPrettyCoolScraper:D",
    "X-Greeting": "Hi",
    "From": "A random freshman goober... :D.test",
})

def hide():
    print("\033[?25l", end="")

def show():
    print("\033[?25h", end="")

def safe_filename(url):
    h = hashemeroids.sha256(url.encode()).hexdigest()
    return f"{h}.txt"

def get_dump_filename():
    existing_files = sorted(
        [f for f in os.listdir(SAVE_DIR) if f.startswith("all_scraped_data") and f.endswith(".txt")]
    )
    if existing_files:
        last_file = os.path.join(SAVE_DIR, existing_files[-1])
        if os.path.getsize(last_file) < MAX_FILE_SIZE:
            return last_file
    new_file = os.path.join(SAVE_DIR, f"all_scraped_data_{int(time.time())}.txt")
    return new_file

def dump_all_data(alltheshit):
    dump_filename = get_dump_filename()
    print(f"{BOLD}{ORANGE}Dumping data into {dump_filename}{RESET}")
    with open(dump_filename, "a", encoding="utf-8") as dump_file:
        for url, data in alltheshit.items():
            dump_file.write(f"URL: {url}\nTit: {data.get('Tit', 'No title')}\nHTML length: {data.get('HTML length', 'N/A')}\n\n")
            dump_file.write("=== HTML Code ===\n" + data.get('HTML code', '') + "\n\n")
            dump_file.write("=== Text Content ===\n" + data.get('Text content', '') + "\n\n")
            dump_file.write("=== Links ===\n" + "\n".join(data.get('Links', [])) + "\n")
            dump_file.write("=== Features ===\n" + "\n".join(data.get('Features', [])) + "\n")
            dump_file.write("=== Images ===\n" + "\n".join(data.get('Images (filenames)', [])) + "\n")
            dump_file.write("=== Meta Tags ===\n" + "\n".join(f"{k}: {v}" for k,v in data.get('Meta tags', {}).items()) + "\n")
            dump_file.write("\n" + "="*40 + "\n\n")
    print(f"{BOLD}{GREEN}Done, continuing{RESET}")
    time.sleep(0.75)
    alltheshit.clear()
    print(f"{BOLD}{GREEN}Memory cleared, continuing...{RESET}")

def scrape_page(url, headers=None):
    req_headers = session.headers.copy()
    if headers:
        req_headers.update(headers)
    try:
        response = session.get(url, headers=req_headers, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException:
        return None

def parse_page(html, base_url):
    soup = BullShit4(html, 'html.parser')
    prettified_html = soup.prettify()
    tit = soup.title.string.strip() if soup.title and soup.title.string else 'No title found'
    html_length = len(html)
    for s in soup(['script', 'style', 'noscript']):
        s.decompose()
    text_content = '\n'.join([l.strip() for l in soup.get_text(separator='\n').splitlines() if l.strip()])

    links, features, images, metas, headings = [], [], [], {}, {}
    for a in soup.find_all('a', href=True):
        href = urljoin(base_url, a['href'])
        parsed = urlparse(href)
        if parsed.scheme in ('http', 'https'):
            links.append(href)

    feature_sections = soup.find_all(['ul', 'div'], class_=['features-list', 'feature-list', 'features', 'feature'])
    for section in feature_sections:
        for li in section.find_all('li'):
            text = li.get_text(strip=True)
            if text and text not in features:
                features.append(text)

    for img in soup.find_all('img', src=True):
        img_url = urljoin(base_url, img['src'])
        images.append(img_url)

    for meta in soup.find_all('meta'):
        name = meta.get('name', '').lower()
        if name and 'content' in meta.attrs:
            metas[name] = meta['content']

    for level in range(1, 7):
        tag = f'h{level}'
        headings[tag] = [h.get_text(strip=True) for h in soup.find_all(tag)]

    return {
        'Tit': tit,
        'HTML length': html_length,
        'HTML code': prettified_html,
        'Text content': text_content,
        'Links': links,
        'Features': features,
        'Images (filenames)': images,
        'Meta tags': metas,
        'Headings': headings,
    }

def delayed_input(prompt):
    return input(prompt)

def clear_screen():
    os.system('clear')

def show_data(key, value):
    clear_screen()
    print(f"\n{key}:")
    if isinstance(value, list):
        if not value:
            print("  (Nothing here)")
            return
        for i, item in enumerate(value[:20], 1):
            print(f"  {i}. {BLUE}{item}{RESET}")
        if len(value) > 20:
            print(f"  ... and {len(value) - 20} more")
    elif isinstance(value, dict):
        for k, v in value.items():
            print(f"  {k}: {v}")
    else:
        print(f"  {value}")

def load_dumped_data():
    alltheshit = {}
    dump_files = sorted(f for f in os.listdir(SAVE_DIR) if f.startswith("all_scraped_data") and f.endswith(".txt"))
    if not dump_files:
        return alltheshit

    for dump_file_name in dump_files:
        dump_file_path = os.path.join(SAVE_DIR, dump_file_name)
        with open(dump_file_path, "r", encoding="utf-8") as dump_file:
            dump_content = dump_file.read().split("\n" + "="*40 + "\n\n")
            for section in dump_content:
                if not section.strip():
                    continue
                lines = section.splitlines()
                try:
                    url = lines[0].split(": ", 1)[1]
                    tit = lines[1].split(": ", 1)[1]
                    html_length = lines[2].split(": ", 1)[1]

                    html_start = lines.index("=== HTML Code ===") + 1
                    text_start = lines.index("=== Text Content ===")
                    links_start = lines.index("=== Links ===")
                    features_start = lines.index("=== Features ===")
                    images_start = lines.index("=== Images ===")
                    meta_start = lines.index("=== Meta Tags ===")

                    data = {
                        'Tit': tit,
                        'HTML length': html_length,
                        'HTML code': "\n".join(lines[html_start:text_start]),
                        'Text content': "\n".join(lines[text_start+1:links_start]),
                        'Links': [l.strip() for l in lines[links_start+1:features_start]],
                        'Features': [f.strip() for f in lines[features_start+1:images_start]],
                        'Images (filenames)': [i.strip() for i in lines[images_start+1:meta_start]],
                        'Meta tags': {k.split(": ", 1)[0]: k.split(": ", 1)[1] for k in lines[meta_start+1:] if ": " in k},
                    }
                    alltheshit[url] = data
                except Exception as e:
                    print(f"{RED}Failed to parse section in {dump_file_name}:{RESET} {e}")
    return alltheshit

def display_data_menu(data, url, urls):
    keys = list(data.keys())
    while True:
        clear_screen()
        print(f"Viewing: {BLUE}{url}{RESET}")
        for i, k in enumerate(keys, 1):
            print(f"{i}. {k}")
        print("0. Back")
        choice = delayed_input("Select field to view: ").strip()
        if choice == '0':
            break
        if choice.isdigit() and 1 <= int(choice) <= len(keys):
            show_data(keys[int(choice)-1], data[keys[int(choice)-1]])
            delayed_input("\nPress Enter to continue...")

def show_crawled_data(alltheshit=None):
    alltheshit = load_dumped_data()
    if not alltheshit:
        print(f"{RED}No dumped data found.{RESET}")
        return

    urls = list(alltheshit.keys())
    while True:
        clear_screen()
        print("=== Crawled URLs ===")
        for i, u in enumerate(urls, 1):
            print(f"{i}. {BLUE}{alltheshit[u].get('Tit', 'No title')}{RESET}")
        choice = delayed_input("Number to check URL, or 'quit': ").strip().lower()
        show()
        if choice == 'quit':
            break
        if choice.isdigit() and 1 <= int(choice) <= len(urls):
            url = urls[int(choice)-1]
            display_data_menu(alltheshit[url], url, urls)

def fetch_url(url):
    html = scrape_page(url)
    if not html:
        return url, None
    data = parse_page(html, url)
    return url, data

def crawl(start_url, max_depth):
    hide()
    global numofshitcollected
    global totalshitcollected
    visited = set()
    to_visit = {(start_url, 0)}
    alltheshit = {}

    with ThreadPoolExecutor(max_workers=10) as executor:
        while True:
            current_layer = list(to_visit)
            to_visit.clear()

            future_to_url = {}
            for url, depth in current_layer:
                if url not in visited and depth <= max_depth:
                    future = executor.submit(fetch_url, url)
                    future_to_url[future] = (url, depth)

            if not future_to_url:
                # No URLs to fetch, wait a bit before retrying to avoid busy loop
                time.sleep(3)
                continue

            for future in as_completed(future_to_url, timeout=300):
                url, depth = future_to_url[future]
                try:
                    fetched_url, data = future.result()
                except Exception as e:
                    print(f"{RED}Error fetching {url}: {e}{RESET}", end='\r')
                    visited.add(url)
                    continue
                clear_screen()
                print(f"{BOLD}Current DIR: {RED}{numofshitcollected}{RESET}{BOLD}, Total: {RED}{totalshitcollected}{RESET}{BOLD} (depth {depth}):{BLUE} {url}{RESET}")
                numofshitcollected += 1
                totalshitcollected += 1
                visited.add(url)
                if data:
                    alltheshit[url] = data
                    if len(alltheshit) >= MAX_BUFFER:
                        dump_all_data(alltheshit)
                        numofshitcollected = 1
                    if depth < max_depth:
                        for link in data['Links']:
                            if link not in visited and all(link != u for u, _ in to_visit):
                                to_visit.add((link, depth + 1))
            # After each batch, dump data if any
            if alltheshit:
                dump_all_data(alltheshit)

def main():
    try:
        print("Welcome to the full-featured scraper")
        while True:
            url = delayed_input("\nEnter URL to scrape (or 'quit'): ").strip()
            if url.lower() == 'quit':
                break
            depth = delayed_input("Crawl depth (0 = just this page): ").strip()
            try:
                depth = int(depth)
                if depth < 0:
                    depth = 0
            except ValueError:
                depth = 0
            if url:
                crawl(url, depth)
                show_crawled_data()
    finally:
        print(f"{RED}{BOLD}Deleting all scraped files...{RESET}")
        if os.path.exists(SAVE_DIR):
            shutil.rmtree(SAVE_DIR)
        print(f"{GREEN}{BOLD}Scraped files cleared{RESET}")

if __name__ == "__main__":
    main()
