#!/usr/bin/env python3
"""
Fetch Skip2Times app screenshots from the Apple App Store.
"""

import requests
import json
import re
import os
from urllib.parse import urlparse

# App Store URL and App ID
APP_ID = "6756554213"
APP_STORE_URL = f"https://apps.apple.com/us/app/skip2times/id{APP_ID}"
ITUNES_API_URL = f"https://itunes.apple.com/lookup?id={APP_ID}"

# Output directory
OUTPUT_DIR = "screenshots"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_from_itunes_api():
    """Try to fetch screenshots from iTunes Search API."""
    print(f"Fetching from iTunes API: {ITUNES_API_URL}")
    response = requests.get(ITUNES_API_URL)
    data = response.json()

    if data.get("resultCount", 0) > 0:
        app_data = data["results"][0]
        screenshot_urls = []

        # iPhone screenshots
        if "screenshotUrls" in app_data:
            screenshot_urls.extend(app_data["screenshotUrls"])

        # iPad screenshots
        if "ipadScreenshotUrls" in app_data:
            screenshot_urls.extend(app_data["ipadScreenshotUrls"])

        if screenshot_urls:
            print(f"Found {len(screenshot_urls)} screenshots via iTunes API")
            return screenshot_urls
        else:
            print("No screenshots found in iTunes API response")
    else:
        print("No app found in iTunes API")

    return []


def fetch_from_app_store_page():
    """Try to scrape screenshots from the App Store webpage."""
    print(f"Fetching from App Store page: {APP_STORE_URL}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    response = requests.get(APP_STORE_URL, headers=headers)
    html = response.text

    # Use a dict to track unique screenshots by their image ID
    # Key: unique image identifier (file path), Value: URL
    screenshot_map = {}

    # More flexible pattern - find any mzstatic image URLs
    pattern = r'(https://is\d-ssl\.mzstatic\.com/image/thumb/[^\s"\'<>]+?\.(?:jpg|png))'

    for match in re.finditer(pattern, html):
        url = match.group(1)
        url = url.replace('\u002F', '/')
        url = url.rstrip(',')  # Remove trailing comma

        # Filter out unwanted images
        if (url and
            'AppIcon' not in url and
            'artwork' not in url.lower() and
            '1x1.gif' not in url and
            'Placeholder' not in url and
            'video-control' not in url):

            # Clean the URL - remove any size/resolution specs at the end to get base URL
            # This helps deduplicate different resolutions of the same image
            clean_url = re.sub(r'/\d+x\d+bb[-\w]*\.?\w*$', '', url)
            clean_url = re.sub(r'/\d+x\d+bb.*$', '', clean_url)

            # Add high-res suffix
            high_res_url = f"{clean_url}/1242x2208bb.jpg"

            # Use the base path as the key to deduplicate
            base_path = urlparse(clean_url).path

            if base_path not in screenshot_map:
                screenshot_map[base_path] = high_res_url

    # Convert to list and limit
    screenshots = list(screenshot_map.values())[:10]

    if screenshots:
        print(f"Found {len(screenshots)} unique screenshot URLs via page scrape")
        for i, s in enumerate(screenshots[:5], 1):
            print(f"  {i}. {urlparse(s).path.split('/')[-2][:40]}...")
    else:
        print("No screenshots found via page scrape")

    return screenshots


def download_screenshot(url, index):
    """Download a screenshot from URL."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            content = response.content

            # Filter out very small files (likely errors or placeholders)
            MIN_SIZE = 10000  # 10KB minimum
            if len(content) < MIN_SIZE:
                print(f"  Skipped {urlparse(url).path.split('/')[-1][:30]}... (too small: {len(content)} bytes)")
                return False

            # Determine file extension
            ext = ".png"
            if ".jpg" in url:
                ext = ".jpg"

            filename = os.path.join(OUTPUT_DIR, f"screenshot{index}{ext}")
            with open(filename, "wb") as f:
                f.write(content)

            print(f"  Downloaded: screenshot{index}{ext} ({len(content)} bytes)")
            return True
        else:
            print(f"  Failed to download {urlparse(url).path.split('/')[-1][:30]}...: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"  Error downloading {url}: {e}")
        return False


def main():
    print("=" * 60)
    print("Skip2Times Screenshot Fetcher")
    print("=" * 60)

    all_screenshots = []

    # Try iTunes API first
    api_screenshots = fetch_from_itunes_api()
    all_screenshots.extend(api_screenshots)

    # Try scraping the webpage
    if not all_screenshots:
        page_screenshots = fetch_from_app_store_page()
        all_screenshots.extend(page_screenshots)

    # Download screenshots
    if all_screenshots:
        print(f"\nDownloading {len(all_screenshots)} screenshots...")
        for i, url in enumerate(all_screenshots[:6], 1):  # Limit to first 6
            download_screenshot(url, i)
        print(f"\nScreenshots saved to '{OUTPUT_DIR}/' directory")
    else:
        print("\nNo screenshots found.")
        print("The app may not have screenshots uploaded to the App Store yet.")
        print("You can manually add screenshots to the 'screenshots/' folder.")


if __name__ == "__main__":
    main()
