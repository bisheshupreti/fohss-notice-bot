import os
import requests
import fitz  # PyMuPDF
from bs4 import BeautifulSoup

# ===========================
# Configuration
# ===========================

BASE_URL = "https://fohss.tu.edu.np"
NOTICE_URL = f"{BASE_URL}/notices"

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

KEYWORDS = [
    "BCA",
    "Bachelor of Computer Application"
    "Bachelor of Computer Applications"
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/137.0 Safari/537.36"
    )
}

LAST_NOTICE_FILE = "last_notice.txt"
MAX_NOTICES = 5


# ===========================
# Fetch Latest Notices
# ===========================

def get_latest_notices():
    response = requests.get(
        NOTICE_URL,
        headers=HEADERS,
        timeout=30
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    notices = []

    # Find all notice links
    links = soup.select("a[href*='/notices/']")

    seen = set()

    for link in links:
        href = link.get("href", "").strip()
        title = link.get_text(" ", strip=True)

        if not href or not title:
            continue

        if not href.startswith("http"):
            href = BASE_URL + href

        # Skip duplicates
        if href in seen:
            continue
        seen.add(href)

        notices.append({
            "id": href.split("/")[-1],
            "title": title,
            "url": href
        })

        if len(notices) >= MAX_NOTICES:
            break

    return notices


# ===========================
# Processed Notice Management
# ===========================

def get_processed_ids():
    """Read processed notice IDs from file."""
    if not os.path.exists(LAST_NOTICE_FILE):
        return set()

    with open(LAST_NOTICE_FILE, "r", encoding="utf-8") as file:
        return set(line.strip() for line in file if line.strip())


def save_processed_id(notice_id):
    """Save a processed notice ID."""
    with open(LAST_NOTICE_FILE, "a", encoding="utf-8") as file:
        file.write(f"{notice_id}\n")


# ===========================
# Telegram Notification
# ===========================

def send_telegram_message(title, url):
    """Send a Telegram notification."""

    message = (
        "🔔 *New BCA Notice Detected!*\n\n"
        f"📌 *Title:*\n{title}\n\n"
        f"🔗 *Notice:*\n{url}"
    )

    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        api_url,
        data={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False
        },
        timeout=30
    )

    response.raise_for_status()


# ===========================
# Title Keyword Detection
# ===========================

def is_bca_in_title(title):
    """Check if the notice title contains any BCA keyword."""
    
    title = title.upper()

    for keyword in KEYWORDS:
        if keyword.upper() in title:
            return True

    return False

# ===========================
# PDF Keyword Detection
# ===========================

def is_bca_in_pdf(notice_url):
    """
    Open the notice page, download the attached PDF,
    and search for BCA keywords.
    """

    try:
        # Open notice page
        response = requests.get(
            notice_url,
            headers=HEADERS,
            timeout=30
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        # Find first PDF link
        pdf_link = None

        for link in soup.find_all("a", href=True):
            href = link["href"]

            if href.lower().endswith(".pdf"):
                pdf_link = href
                break

        if not pdf_link:
            return False

        if not pdf_link.startswith("http"):
            pdf_link = BASE_URL + pdf_link

        # Download PDF
        pdf_response = requests.get(
            pdf_link,
            headers=HEADERS,
            timeout=30
        )
        pdf_response.raise_for_status()

        # Read PDF from memory
        document = fitz.open(
            stream=pdf_response.content,
            filetype="pdf"
        )

        text = ""

        for page in document:
            text += page.get_text()

        document.close()

        text = text.upper()

        for keyword in KEYWORDS:
            if keyword.upper() in text:
                return True

        return False

    except Exception as e:
        print(f"[PDF ERROR] {e}")
        return False

# ===========================
# Main
# ===========================

def main():
    print("Checking latest notices...")

    processed_ids = get_processed_ids()
    notices = get_latest_notices()

    for notice in notices:
        notice_id = notice["id"]
        title = notice["title"]
        url = notice["url"]

        # Skip if already processed
        if notice_id in processed_ids:
            continue

        print(f"Checking: {title}")

        should_notify = False

        # Check title first
        if is_bca_in_title(title):
            should_notify = True
        else:
            # Check PDF only if title doesn't contain BCA
            should_notify = is_bca_in_pdf(url)

        if should_notify:
            print("✓ BCA notice found.")
            send_telegram_message(title, url)
        else:
            print("✗ Not a BCA notice.")

        # Mark as processed (whether BCA or not)
        save_processed_id(notice_id)


if __name__ == "__main__":
    main()
