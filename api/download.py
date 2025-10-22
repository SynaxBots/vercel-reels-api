# api/download.py

import json
import re
from http.server import BaseHTTPRequestHandler
from urllib.parse import unquote
import requests
from bs4 import BeautifulSoup

def log_message(message):
    print(message)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        log_message("=== New Request (Manual Scraper) ===")
        try:
            query_string = self.path.split('?', 1)[1]
            params = dict(qc.split('=') for qc in query_string.split('&'))
            reel_url = unquote(params.get('url'))
        except IndexError:
            self.send_error(400, "Missing 'url' parameter")
            return

        if not reel_url:
            self.send_error(400, "Missing 'url' parameter")
            return

        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(reel_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Instagram embeds data in different script tags. We'll search a few common patterns.
            script_tags = soup.find_all('script', type='application/ld+json')
            video_url = None
            
            for tag in script_tags:
                try:
                    data = json.loads(tag.string)
                    # The data can be a single object or a list. We need to handle both.
                    if isinstance(data, list):
                        data = data[0]
                    if 'video' in data and 'contentUrl' in data['video']:
                        video_url = data['video']['contentUrl']
                        break
                except (json.JSONDecodeError, TypeError, KeyError):
                    continue
            
            # Fallback: sometimes it's in a different format
            if not video_url:
                # This is a more fragile regex search for a specific pattern
                match = re.search(r'"video_url":"([^"]+)"', response.text)
                if match:
                    video_url = match.group(1).replace(r'\u0026', '&')

            if not video_url:
                log_message("Error: Could not find video URL in page source.")
                self.send_error(404, "Could not find video URL. Instagram may have changed its page structure.")
                return

            response_data = {"download_url": video_url}
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode())
            return

        except requests.exceptions.RequestException as e:
            log_message(f"Request failed: {e}")
            self.send_error(500, f"Failed to fetch the URL: {e}")
            return
        except Exception as e:
            log_message(f"An unexpected error occurred: {e}")
            self.send_error(500, f"An unexpected error occurred: {e}")
            return
