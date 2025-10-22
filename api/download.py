# api/download.py

import re
import json
from http.server import BaseHTTPRequestHandler
import instaloader

# --- Initialize Instaloader ---
# It's better to initialize it inside the handler to avoid issues with cold starts
# and concurrency, but for low-traffic apps, initializing it globally is fine.
# Let's keep it simple for now.
L = instaloader.Instaloader()

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 1. Parse the query parameters from the path
        # The path will be something like "/api/download?url=..."
        try:
            query_string = self.path.split('?', 1)[1]
            params = dict(qc.split('=') for qc in query_string.split('&'))
            reel_url = params.get('url')
        except IndexError:
            reel_url = None

        if not reel_url:
            self.send_error(400, "Missing 'url' parameter")
            return

        # 2. Extract the shortcode from the URL
        try:
            shortcode = re.search(r"/reel/([a-zA-Z0-9_-]+)", reel_url).group(1)
        except (AttributeError, IndexError):
            self.send_error(400, "Invalid Instagram Reel URL format")
            return

        # 3. Fetch the post data using Instaloader
        try:
            post = instaloader.Post.from_shortcode(L.context, shortcode)
        except instaloader.exceptions.ProfileNotExist:
            self.send_error(404, "Post not found or profile is private")
            return
        except Exception as e:
            # Log the error for debugging
            print(f"An Instaloader error occurred: {e}")
            self.send_error(500, f"Failed to fetch post data: {str(e)}")
            return

        # 4. Prepare the JSON response
        if not post.is_video:
            self.send_error(400, "The provided URL is not a video post.")
            return

        response_data = {
            "shortcode": post.shortcode,
            "download_url": post.video_url,
            "caption": post.caption,
            "owner_username": post.owner_username,
            "view_count": post.video_view_count,
            "like_count": post.likes,
            "thumbnail_url": post.url
        }

        # 5. Send the successful response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode())
        return
