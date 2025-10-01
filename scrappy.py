import os
import sys
import asyncio
import aiohttp
from urllib.parse import urljoin, urlparse
from selectolax.parser import HTMLParser
import functools

# ---------------- Constants ----------------
OUTPUT_FILE = "LotsOfF*ckingData.txt"
MAX_BUFFER = 1000
URL_FETCHERS = 20  # number of URL extraction workers
INFO_WORKERS = 40  # number of info extraction workers
PRINT_WORKERS = 6  # number of print workers for smooth output

RED = '\033[38;5;196m'
BLUE = "\033[34m"
RESET = '\033[0m'
BOLD = '\033[1m'
ORANGE = '\033[33m'
GREEN = '\033[32m'

# ---------------- Clear Screen (full) ----------------
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# ---------------- Smart line-clear print ----------------
last_message_lines = 0

def clear_last_message():
    global last_message_lines
    for _ in range(last_message_lines):
        sys.stdout.write('\x1b[1A')  # Move cursor up one line
        sys.stdout.write('\x1b[2K')  # Clear entire line
    sys.stdout.flush()
    last_message_lines = 0

def print_status(message):
    global last_message_lines
    clear_last_message()
    print(message, end='', flush=True)
    last_message_lines = message.count('\n') + 1

# ---------------- Fast Parser using selectolax ----------------
def parse_links(html, base_url):
    tree = HTMLParser(html)
    links = []
    for a in tree.css('a[href]'):
        href = a.attributes.get('href')
        if href:
            full_url = urljoin(base_url, href)
            scheme = urlparse(full_url).scheme
            if scheme in ('http', 'https'):
                links.append(full_url)
    return links

def parse_full_page(html, base_url):
    tree = HTMLParser(html)
    
    title_node = tree.css_first('title')
    tit = title_node.text(strip=True) if title_node else 'No title found'
    html_length = len(html)

    for node in tree.css('script, style, noscript'):
        node.decompose()

    text_content = '\n'.join(
        line.strip() for line in tree.text(separator='\n').splitlines() if line.strip()
    )

    features = []
    feature_set = set()
    for section in tree.css('ul.features-list, ul.feature-list, ul.features, ul.feature, div.features-list, div.feature-list, div.features, div.feature'):
        for li in section.css('li'):
            text = li.text(strip=True)
            if text and text not in feature_set:
                feature_set.add(text)
                features.append(text)

    images = []
    for img in tree.css('img[src]'):
        src = img.attributes.get('src')
        if src:
            images.append(urljoin(base_url, src))

    metas = {}
    for meta in tree.css('meta[name][content]'):
        name = meta.attributes.get('name', '').lower()
        content = meta.attributes.get('content', '')
        if name and content:
            metas[name] = content

    headings = {}
    for i in range(1, 7):
        headings[f'h{i}'] = [h.text(strip=True) for h in tree.css(f'h{i}')]

    return {
        'Tit': tit,
        'HTML length': html_length,
        'HTML code': html,
        'Text content': text_content,
        'Features': features,
        'Images (filenames)': images,
        'Meta tags': metas,
        'Headings': headings,
    }

# ---------------- Efficient Async Write ----------------
def _write_to_file(data_batch):
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        for url, data in data_batch.items():
            f.write(f"URL: {url}\nTit: {data.get('Tit', 'No title')}\nHTML length: {data.get('HTML length', 'N/A')}\n\n")
            f.write("=== HTML Code ===\n" + data.get('HTML code', '') + "\n\n")
            f.write("=== Text Content ===\n" + data.get('Text content', '') + "\n\n")
            f.write("=== Features ===\n" + "\n".join(data.get('Features', [])) + "\n")
            f.write("=== Images ===\n" + "\n".join(data.get('Images (filenames)', [])) + "\n")
            f.write("=== Meta Tags ===\n" + "\n".join(f"{k}: {v}" for k, v in data.get('Meta tags', {}).items()) + "\n")
            f.write("=== Headings ===\n")
            for level, texts in data.get('Headings', {}).items():
                f.write(f"{level}:\n")
                for text in texts:
                    f.write(f"  {text}\n")
            f.write("\n" + "="*40 + "\n\n")

async def dump_all_data(all_data):
    print_status(f"{BOLD}{ORANGE}Dumping data into {OUTPUT_FILE}{RESET}\n")
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, functools.partial(_write_to_file, all_data))
    all_data.clear()
    print_status(f"{BOLD}{GREEN}Memory cleared, continuing...{RESET}\n")

# ---------------- Async Fetch ----------------
async def fetch(session, url):
    headers = {
        "User-Agent": "CAM_WithaPrettyCoolScraper:D",
        "X-Greeting": "Hi",
        "From": "A random freshman goober... :D.test",
    }
    try:
        async with session.get(url, headers=headers, timeout=10) as response:
            response.raise_for_status()
            return await response.text()
    except Exception:
        return None

# ---------------- URL Fetcher Worker ----------------
async def url_fetcher(name, session, url_queue, info_queue, visited, max_depth):
    while True:
        try:
            url, depth = await asyncio.wait_for(url_queue.get(), timeout=10)
        except asyncio.TimeoutError:
            break

        html = await fetch(session, url)
        if html:
            links = parse_links(html, url)
            if depth < max_depth:
                for link in links:
                    if link not in visited:
                        visited.add(link)
                        await url_queue.put((link, depth + 1))
                        await info_queue.put((link, depth + 1))
            await info_queue.put((url, depth))
        url_queue.task_done()

# ---------------- Info Worker ----------------
async def info_worker(name, session, info_queue, all_data, link_counter, print_queue):
    while True:
        try:
            url, depth = await asyncio.wait_for(info_queue.get(), timeout=15)
        except asyncio.TimeoutError:
            break

        html = await fetch(session, url)
        if html:
            data = parse_full_page(html, url)
            all_data[url] = data
            link_counter[0] += 1

            msg = (
                f"{BOLD}{ORANGE}[{link_counter[0]}]{RESET}{BOLD}{GREEN} (depth {depth}): {RESET}"
                f"{BOLD}{BLUE}{url}{RESET}\n"
            )
            await print_queue.put(msg)

            if link_counter[0] >= MAX_BUFFER:
                await dump_all_data(all_data)
                link_counter[0] = 0
        info_queue.task_done()

# ---------------- Print Worker ----------------
async def print_worker(name, print_queue):
    while True:
        try:
            message = await asyncio.wait_for(print_queue.get(), timeout=30)
        except asyncio.TimeoutError:
            break
        print_status(message)
        print_queue.task_done()

# ---------------- Main Crawl Function ----------------
async def crawl(start_url, max_depth):
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    visited = set([start_url])
    url_queue = asyncio.Queue()
    info_queue = asyncio.Queue()
    print_queue = asyncio.Queue()
    all_data = {}
    link_counter = [0]

    await url_queue.put((start_url, 0))
    await info_queue.put((start_url, 0))

    conn = aiohttp.TCPConnector(limit=None, ttl_dns_cache=300)
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        url_fetchers = [
            asyncio.create_task(url_fetcher(i+1, session, url_queue, info_queue, visited, max_depth))
            for i in range(URL_FETCHERS)
        ]

        info_workers = [
            asyncio.create_task(info_worker(i+1, session, info_queue, all_data, link_counter, print_queue))
            for i in range(INFO_WORKERS)
        ]

        print_workers = [
            asyncio.create_task(print_worker(i+1, print_queue))
            for i in range(PRINT_WORKERS)
        ]

        await url_queue.join()
        await info_queue.join()
        await print_queue.join()

        for task in url_fetchers + info_workers + print_workers:
            task.cancel()
        await asyncio.gather(*url_fetchers, *info_workers, *print_workers, return_exceptions=True)

        if all_data:
            await dump_all_data(all_data)

        return all_data  # <-- return data for interactive viewing

# ---------------- Interactive display functions ----------------
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
        if not value:
            print("  (Nothing here)")
            return
        for k, v in value.items():
            print(f"  {k}: {v}")
    else:
        print(f"  {value}")

def display_data_menu(data):
    keys = list(data.keys())
    while True:
        clear_screen()
        print("=== Crawled URLs ===")
        for i, url in enumerate(keys, 1):
            print(f"{BOLD}{ORANGE}{i}: {BLUE}{url}{RESET}")
        print("0. Back/Quit")

        choice = input("Number to check URL (or 0 to quit): ").strip()
        if choice == '0':
            break
        if choice.isdigit() and 1 <= int(choice) <= len(keys):
            url = keys[int(choice)-1]
            fields = list(data[url].keys())
            while True:
                clear_screen()
                print(f"Viewing data for: {BLUE}{url}{RESET}\n")
                for i, field in enumerate(fields, 1):
                    print(f"{i}. {field}")
                print("0. Back")

                field_choice = input("Select field to view: ").strip()
                if field_choice == '0':
                    break
                if field_choice.isdigit() and 1 <= int(field_choice) <= len(fields):
                    field = fields[int(field_choice)-1]
                    show_data(field, data[url][field])
                    input("\nPress Enter to continue...")

# ---------------- Main Entry Point ----------------
async def main():
    print("Welcome to the mega-optimized async scraper with separated workers\n")
    try:
        while True:
            url = input("Enter URL to scrape: ").strip()
            if not url:
                continue

            depth_str = input("Crawl depth (0 = just this page): ").strip()
            try:
                depth = int(depth_str)
                if depth < 0:
                    depth = 0
            except:
                depth = 0

            clear_screen()
            print(f"Starting crawl on {url} with depth {depth}...\n")
            all_data = await crawl(url, depth)

            if all_data:
                print(f"\n{GREEN}Crawl finished! Press Enter to view data or Ctrl+C to quit.{RESET}\n")
                input()
                display_data_menu(all_data)

            print(f"\n{GREEN}Done viewing data. Press Enter to start another or Ctrl+C to quit.{RESET}\n")
            input()

    except KeyboardInterrupt:
        print(f"\n\n{RED}{BOLD}KeyboardInterrupt received. Deleting scraped output file...{RESET}")
        if os.path.exists(OUTPUT_FILE):
            os.remove(OUTPUT_FILE)
        print(f"{GREEN}{BOLD}Scraped file deleted. Goodbye!{RESET}")

if __name__ == "__main__":
    asyncio.run(main())
