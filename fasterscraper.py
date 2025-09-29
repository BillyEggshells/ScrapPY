import os
import requests
from bs4 import BeautifulSoup as BullShit4
from urllib.parse import urljoin, urlparse
import time
import hashlib as hashemeroids
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

SAVE_DIR = "scraped_texts"
os.makedirs(SAVE_DIR, exist_ok=True)

numofshitcollected = 1
MAX_BUFFER = 300  # Dump when this many scrapes collected

# Colors for terminal
RED = '\033[31m'
BLUE = "\033[34m"
RESET = '\033[0m'
BOLD = '\033[1m'
ORANGE = '\033[33m'
GREEN = '\033[32m'

# Session with headers
session = requests.Session()
session.headers.update({
    "User-agent": "CAM_WithaPrettyCoolScraper:D",
    "X-Greeting": "Hi from your friendly scrapper! excuse me if i spam, im new ot python! :D",
    "From": "A random freshman goober... :D.test",
})

def safe_filename(url):
    h = hashemeroids.sha256(url.encode()).hexdigest()
    return f"{h}.txt"

def save_scraped_data_to_file(url, data):
    filename = safe_filename(url)
    filepath = os.path.join(SAVE_DIR, filename)
    content = f"URL: {url}\nTit: {data.get('Tit', 'No title')}\nHTML length: {data.get('HTML length', 'N/A')}\n\n"
    content += "=== HTML Code ===\n" + data.get('HTML code', '') + "\n\n"
    content += "=== Text Content ===\n" + data.get('Text content', '') + "\n\n"
    content += "=== Links ===\n" + "\n".join(data.get('Links', [])) + "\n"
    content += "=== Features ===\n" + "\n".join(data.get('Features', [])) + "\n"
    content += "=== Images ===\n" + "\n".join(data.get('Images (filenames)', [])) + "\n"
    content += "=== Meta Tags ===\n" + "\n".join(f"{k}: {v}" for k,v in data.get('Meta tags', {}).items()) + "\n"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

def dump_all_data(alltheshit):
    # Dump all currently scraped data into one big file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_filename = os.path.join(SAVE_DIR, f"dump_{timestamp}.txt")
    print(f"{BOLD}{ORANGE}full, dumping data into {dump_filename}{RESET}")
    
    with open(dump_filename, "w", encoding="utf-8") as dump_file:
        for url, data in alltheshit.items():
            dump_file.write(f"URL: {url}\nTit: {data.get('Tit', 'No title')}\nHTML length: {data.get('HTML length', 'N/A')}\n\n")
            dump_file.write("=== HTML Code ===\n" + data.get('HTML code', '') + "\n\n")
            dump_file.write("=== Text Content ===\n" + data.get('Text content', '') + "\n\n")
            dump_file.write("=== Links ===\n" + "\n".join(data.get('Links', [])) + "\n")
            dump_file.write("=== Features ===\n" + "\n".join(data.get('Features', [])) + "\n")
            dump_file.write("=== Images ===\n" + "\n".join(data.get('Images (filenames)', [])) + "\n")
            dump_file.write("=== Meta Tags ===\n" + "\n".join(f"{k}: {v}" for k,v in data.get('Meta tags', {}).items()) + "\n")
            dump_file.write("\n" + "="*40 + "\n\n")
    
    print(f"{BOLD}{GREEN}done, continuing{RESET}")
    time.sleep(0.75)

def cleanup_other_shit(selected_url, all_urls):
    valid_files = {safe_filename(url) for url in all_urls}
    for filename in os.listdir(SAVE_DIR):
        if filename not in valid_files:
            path = os.path.join(SAVE_DIR, filename)
            try:
                os.remove(path)
                print(f"[DEBUG] Deleted file {path}")
            except Exception as e:
                print(f"Error deleting file {path}: {e}")

def scrape_page(url, headers=None, retry=3):
    req_headers = session.headers.copy()
    if headers:
        req_headers.update(headers)
    tries = 0
    while tries < retry:
        try:
            response = session.get(url, headers=req_headers, timeout=10, allow_redirects=True)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            tries += 1
            if tries == retry:
                return None

def parse_page(html, base_url):
    soup = BullShit4(html, 'html.parser')
    tit = soup.title.string.strip() if soup.title and soup.title.string else 'No title found'
    html_length = len(html)

    for s in soup(['script', 'style', 'noscript']):
        s.decompose()
    text_content = '\n'.join([l.strip() for l in soup.get_text(separator='\n').splitlines() if l.strip()])

    links = []
    for a in soup.find_all('a', href=True):
        href = urljoin(base_url, a['href'])
        parsed = urlparse(href)
        if parsed.scheme in ('http', 'https'):
            links.append(href)

    features = []
    feature_sections = soup.find_all(['ul', 'div'], class_=['features-list', 'feature-list', 'features', 'feature'])
    for section in feature_sections:
        for li in section.find_all('li'):
            text = li.get_text(strip=True)
            if text and text not in features:
                features.append(text)

    images = []
    for img in soup.find_all('img', src=True):
        img_url = urljoin(base_url, img['src'])
        images.append(img_url)

    metas = {}
    for meta in soup.find_all('meta'):
        name = meta.get('name', '').lower()
        if name and 'content' in meta.attrs:
            metas[name] = meta['content']

    headings = {}
    for level in range(1, 7):
        tag = f'h{level}'
        headings[tag] = [h.get_text(strip=True) for h in soup.find_all(tag)]

    return {
        'Tit': tit,
        'HTML length': html_length,
        'HTML code': html,
        'Text content': text_content,
        'Links': links,
        'Features': features,
        'Images (filenames)': images,
        'Meta tags': metas,
        'Headings': headings,
    }

def delayed_input(prompt):
    # No delay for max speed, just input prompt
    return input(prompt)

def clear_screen():
    print("\033[H\033[2J")

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

def display_data_menu(data, url, all_urls):
    keys = [k for k in data.keys() if k != 'Tit']
    save_scraped_data_to_file(url, data)
    cleanup_other_shit(url, all_urls)

    while True:
        clear_screen()
        print(f"\nPage: {data.get('Tit', 'No title')}")
        print("Check page data:")
        for i, key in enumerate(keys, 1):
            print(f"  {i}. {key}")
        print("Type 'back' to go back to URL list")

        choice = delayed_input("Pick a number: ").strip().lower()

        if choice == 'back':
            return

        if choice.isdigit() and 1 <= int(choice) <= len(keys):
            key = keys[int(choice)-1]
            show_data(key, data[key])
            delayed_input("\nPress Enter to return to the page menu...")
        else:
            print("Invalid choice.")
            delayed_input("Press Enter to try again...")

def show_crawled_data(alltheshit):
    urls = list(alltheshit.keys())
    while True:
        clear_screen()
        print("=== Crawled URLs ===")
        for i, u in enumerate(urls, 1):
            print(f"{i}. {BLUE}{alltheshit[u].get('Tit', 'No title')}{RESET}")
        choice = delayed_input("Number to check URL, or 'quit': ").strip().lower()
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
    global numofshitcollected
    visited = set()
    to_visit = {(start_url, 0)}
    alltheshit = {}

    with ThreadPoolExecutor(max_workers=10) as executor:
        while to_visit:
            current_layer = list(to_visit)
            to_visit.clear()

            future_to_url = {}
            for url, depth in current_layer:
                if url not in visited and depth <= max_depth:
                    future = executor.submit(fetch_url, url)
                    future_to_url[future] = (url, depth)

            if not future_to_url:
                break

            for future in as_completed(future_to_url, timeout=30):
                url, depth = future_to_url[future]
                try:
                    fetched_url, data = future.result()
                except Exception as e:
                    print(f"{RED}Error fetching {url}: {e}{RESET}", end='\r')
                    visited.add(url)
                    continue
                clear_screen()
                print(f"{BOLD}Scrape {numofshitcollected} (depth {depth}){BLUE}: {url}{RESET}")
                numofshitcollected += 1
                visited.add(url)
                if data:
                    alltheshit[url] = data
                    # Dump if full buffer reached
                    if len(alltheshit) >= MAX_BUFFER:
                        dump_all_data(alltheshit)
                        alltheshit.clear()
                        numofshitcollected = 1
                    if depth < max_depth:
                        for link in data['Links']:
                            if link not in visited and all(link != u for u, _ in to_visit):
                                to_visit.add((link, depth + 1))

    # Dump remaining if any left after crawl finishes
    if alltheshit:
        dump_all_data(alltheshit)

    print()
    return alltheshit

def main():
    print("Welcome to the full-featured scraper")
    while True:
        url = delayed_input("\nEnter URL to scrape (or 'quit'): ").strip()
        if url.lower() == 'quit':
            break
        depth = delayed_input("Crawl depth (0 = just this page): ").strip()
        try:
            depth = int(depth)
            if depth < 0: depth = 0
        except ValueError:
            depth = 0
        alltheshit = crawl(url, depth)
        if alltheshit:
            show_crawled_data(alltheshit)
        else:
            print("No data scraped.")

if __name__ == "__main__":
    main()
