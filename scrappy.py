import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import hashlib

INPUT_DELAY = 0.5  # Delay input so it doesn’t go crazy fast
SAVE_DIR = "scraped_texts"
os.makedirs(SAVE_DIR, exist_ok=True)  # Make sure save folder exists

def delayed_input(prompt):
   time.sleep(INPUT_DELAY)  # Chill a sec before input
   return input(prompt)

def clear_screen():
   os.system('cls' if os.name == 'nt' else 'clear')  # Clear the damn screen

def get_filename_from_url(url):
   parsed = urlparse(url)
   return os.path.basename(parsed.path) or url  # Get filename from URL path or fallback

def safe_filename(url):
   """Make a safe-ass filename using SHA256."""
   h = hashlib.sha256(url.encode()).hexdigest()
   return f"{h}.txt"

def save_scraped_data_to_file(url, data):
   filename = safe_filename(url)
   filepath = os.path.join(SAVE_DIR, filename)
   print(f"[DEBUG] Saving data for {url} into file {filepath}")

   # Build file content, no fancy shit
   content = f"URL: {url}\n"
   content += f"Title: {data.get('Title', 'No title')}\n"
   content += f"HTML length: {data.get('HTML length', 'N/A')}\n\n"
   content += "=== HTML Code ===\n"
   content += data.get('HTML code', '') + "\n\n"
   content += "=== Text Content ===\n"
   content += data.get('Text content', '') + "\n\n"
   content += "=== Links ===\n"
   content += "\n".join(data.get('Links', [])) + "\n"

   with open(filepath, "w", encoding="utf-8") as f:
       f.write(content)
   print(f"[DEBUG] Saved scraped data to {filepath}")

def cleanup_other_files(selected_url, all_urls):
   """Trash files for URLs you ain’t checking."""
   valid_files = {safe_filename(url) for url in all_urls}
   for filename in os.listdir(SAVE_DIR):
       if filename not in valid_files:
           path = os.path.join(SAVE_DIR, filename)
           try:
               os.remove(path)
               print(f"[DEBUG] Deleted file {path}")
           except Exception as e:
               print(f"Error deleting file {path}: {e}")

def scrape_page(url, headers=None, retry=3, delay=2):
   if headers is None:
       headers = {
           "User-agent": "CAM_WithaPrettyCoolScraper:D",
           "X-Greeting": "Hi from your friendly scrapper! excuse me if i spam, im new ot python! :D",
           "From": "A random freshman goober... :D.test",
       }

   tries = 0
   while tries < retry:
       try:
           response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
           response.raise_for_status()
           return response.text
       except requests.RequestException as e:
           tries += 1
           print(f"Request failed for {url} (try {tries}/{retry}): {e}")
           if tries < retry:
               print(f"Retrying in {delay} seconds... chill")
               time.sleep(delay)
           else:
               print("Giving up. This site sucks or you do.")
               return None

def parse_page(html, base_url):
   soup = BeautifulSoup(html, 'html.parser')

   title = soup.title.string.strip() if soup.title and soup.title.string else 'No title found'
   html_length = len(html)

   # Strip scripts and crap, leave only visible text
   for script_or_style in soup(['script', 'style', 'noscript']):
       script_or_style.decompose()  # Get rid of annoying shit
   text_content = soup.get_text(separator='\n')

   # Clean blank lines so it’s not a mess
   lines = [line.strip() for line in text_content.splitlines()]
   lines = [line for line in lines if line]
   clean_text = '\n'.join(lines)

   links = []
   for a in soup.find_all('a', href=True):
       href = urljoin(base_url, a['href'])
       links.append(href)

   features = []
   feature_sections = soup.find_all(['ul', 'div'], class_=['features-list', 'feature-list', 'features', 'feature'])
   if feature_sections:
       for section in feature_sections:
           for li in section.find_all('li'):
               text = li.get_text(strip=True)
               if text and text not in features:
                   features.append(text)
   else:
       for div in soup.find_all('div', class_=lambda x: x and 'feature' in x):
           for li in div.find_all('li'):
               text = li.get_text(strip=True)
               if text and text not in features:
                   features.append(text)

   images = []
   for img in soup.find_all('img', src=True):
       img_url = urljoin(base_url, img['src'])
       filename = get_filename_from_url(img_url)
       if filename and filename not in images:
           images.append(filename)

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
       'Title': title,
       'HTML length': html_length,
       'HTML code': html,
       'Text content': clean_text,
       'Links': links,
       'Features': features,
       'Images (filenames)': images,
       'Meta tags': metas,
       'Headings': headings,
   }

def confirm_long_display(key):
   while True:
       confirm = delayed_input(f"\n'{key}' can be pretty damn long. Show it? (yes/no): ").strip().lower()
       if confirm in ('yes', 'y'):
           return True
       elif confirm in ('no', 'n'):
           return False
       else:
           print("Say 'yes' or 'no', dumbass.")

def show_data(key, value):
   clear_screen()
   print(f"\n{key}:")
   if isinstance(value, list):
       if not value:
           print("  (Nothing here, bro)")
           return
       for i, item in enumerate(value[:20], 1):
           print(f"  {i}. {item}")
       if len(value) > 20:
           print(f"  ... and {len(value) - 20} more")
   elif isinstance(value, dict):
       if not value:
           print("  (Nada here)")
           return
       for k, v in value.items():
           if isinstance(v, list):
               print(f"  {k} ({len(v)} items):")
               for i, item in enumerate(v[:10], 1):
                   print(f"    {i}. {item}")
               if len(v) > 10:
                   print(f"    ... and {len(v) - 10} more")
           else:
               print(f"  {k}: {v}")
   else:
       if key.lower() == 'html length':
           print(f"  {value} characters")
       elif key.lower() in ('html code', 'text content'):
           if confirm_long_display(key):
               print(value)
           else:
               print("  (Skipped showing that crap.)")
       else:
           print(f"  {value}")

def print_all(data):
   clear_screen()
   print("\n=== ALL SCRAPED DATA ===")
   for key, value in data.items():
       show_data(key, value)
   print("="*30)

def display_data_menu(data, url, all_urls):
   """Pick what part of data you wanna see."""
   keys = [k for k in data.keys() if k != 'Title']  # Title ain’t in menu
   print("\nStuff you can check on this page:")
   for i, key in enumerate(keys, 1):
       count = len(data[key]) if isinstance(data[key], list) else 1
       print(f"{i}. {key} ({count} items)")

   print("Type 'all' to see everything.")
   print("Type 'back' to go back to URL list.")

   save_scraped_data_to_file(url, data)  # Save when viewing, cuz why not
   cleanup_other_files(url, all_urls)    # Clean old shit

   while True:
       choice = delayed_input("Your choice: ").strip().lower()

       if choice == 'all':
           data_no_title = {k: v for k, v in data.items() if k != 'Title'}
           print_all(data_no_title)
           delayed_input("\nPress Enter to get back...")
           clear_screen()
           print("\nBack to data menu.")
           for i, key in enumerate(keys, 1):
               count = len(data[key]) if isinstance(data[key], list) else 1
               print(f"{i}. {key} ({count} items)")
           print("Type 'all' to see everything.")
           print("Type 'back' to go back.")
           continue

       if choice == 'back':
           return  # Back to URL list

       if choice.isdigit():
           choice_num = int(choice)
           if 1 <= choice_num <= len(keys):
               key = keys[choice_num - 1]
               show_data(key, data[key])
               delayed_input("\nPress Enter to get back...")
               clear_screen()
               print("\nBack to data menu.")
               for i, key in enumerate(keys, 1):
                   count = len(data[key]) if isinstance(data[key], list) else 1
                   print(f"{i}. {key} ({count} items)")
               print("Type 'all' to see everything.")
               print("Type 'back' to go back.")
               continue
           else:
               print("Dude, that number ain't valid.")
               continue

       matching_keys = [k for k in keys if k.lower() == choice]
       if matching_keys:
           key = matching_keys[0]
           show_data(key, data[key])
           delayed_input("\nPress Enter to get back...")
           clear_screen()
           print("\nBack to data menu.")
           for i, key in enumerate(keys, 1):
               count = len(data[key]) if isinstance(data[key], list) else 1
               print(f"{i}. {key} ({count} items)")
           print("Type 'all' to see everything.")
           print("Type 'back' to go back.")
           continue

       print("Invalid choice, try a number, name, 'all', or 'back'.")

def show_crawled_data(all_data, display_title_in_list=False):
   urls = list(all_data.keys())
   while True:
       clear_screen()
       print("\n=== Crawled URLs ===")
       for i, u in enumerate(urls, 1):
           title = all_data[u].get('Title', 'No title')
           if display_title_in_list:
               print(f"{i}. {title}  --  {u}")
           else:
               print(f"{i}. {u}  --  {title}")

       print("Type the number to check a URL, or 'quit' to bail.")
       choice = delayed_input("Choice: ").strip().lower()

       if choice == 'quit':
           break

       if choice.isdigit():
           choice_num = int(choice)
           if 1 <= choice_num <= len(urls):
               url = urls[choice_num - 1]
               data = all_data[url]
               display_data_menu(data, url, urls)  # Show data for that URL
           else:
               print("Number’s not right.")
               delayed_input("Press Enter to continue...")
       else:
           print("Invalid input.")
           delayed_input("Press Enter to continue...")

def main():
   print("Welcome to my sh*tty scraper")

   while True:
       url = delayed_input("\nEnter URL to scrape (or 'quit' to go back): ").strip()
       if url.lower() == 'quit':
           print("You suck")
           break

       use_title = delayed_input("Show page as title? (Y/n): ").strip().lower()
       display_title_in_list = (use_title in ('y', 'yes', ''))

       max_depth = delayed_input("Crawl depth (0 = just this page): ").strip()
       try:
           max_depth = int(max_depth)
           if max_depth < 0:
               print("Depth can't be negative, setting to 0.")
               max_depth = 0
       except ValueError:
           print("Invalid number, using 0.")
           max_depth = 0

       all_data = crawl(url, max_depth)
       if not all_data:
           print("No data scraped, that sucks ¯\\_(ツ)_/¯")
           continue

       show_crawled_data(all_data, display_title_in_list=display_title_in_list)

def crawl(url, max_depth):
   visited = set()
   to_visit = [(url, 0)]
   all_data = {}

   while to_visit:
       current_url, depth = to_visit.pop(0)
       if current_url in visited or depth > max_depth:
           continue
       print(f"\nScraping (depth {depth}): {current_url}")
       html = scrape_page(current_url)
       if not html:
           print(f"Failed to get {current_url}")
           visited.add(current_url)
           continue
       data = parse_page(html, current_url)
       all_data[current_url] = data
       visited.add(current_url)

       if depth < max_depth:
           for link in data['Links']:
               if link not in visited and urlparse(link).scheme in ('http', 'https'):
                   to_visit.append((link, depth + 1))
   return all_data

if __name__ == "__main__":
   main()
