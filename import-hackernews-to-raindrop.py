import sys
import time
import os
import logging
import requests
import threading
from itertools import zip_longest
from lxml import html

RAINDROP_API_TOKEN = "your-token-goes-here"
RAINDROP_COLLECTION_ID = "your-collection-id-goes-here"

logging.basicConfig(format="[%(levelname)s] %(message)s", level=logging.INFO)
logging.debug("Log level: " + logging.getLevelName(logging.root.getEffectiveLevel()))


if len(sys.argv) - 1 < 2:
    print("\033[91mERROR: Hackernews username and password were not specified!\033[00m")
    print("Usage: python[3] " + sys.argv[0] + " username password")
    exit(1)

username = sys.argv[1]
password = sys.argv[2]


def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


class raindrop:
    def __init__(self):
        self._existing_urls = set()

    def get_collection(self):
        logging.info("Getting raindrop collection")
        page = 0
        item_count = 50

        while item_count > 0:
            request_url = (
                "https://api.raindrop.io/rest/v1/raindrops/"
                + RAINDROP_COLLECTION_ID
                + "?page="
                + str(page)
                + "&perpage=50"
            )

            logging.debug("GET " + request_url)

            response = requests.get(
                request_url,
                headers={"Authorization": "Bearer " + RAINDROP_API_TOKEN},
            )

            if response.status_code == 200:
                items = response.json()["items"]
                item_count = len(items)
                for link in items:
                    self._existing_urls.add(link["link"])
                page += 1
            else:
                logging.fatal("Failed getting raindrop items")
                exit(1)

            time.sleep(1)

        logging.info("Loaded " + str(len(self._existing_urls)) + " existing raindrop URLs")

    def add(self, hackernews_items):
        # Filter out items already in raindrop
        new_items = [
            item for item in hackernews_items
            if item.link not in self._existing_urls
        ]

        logging.info(str(len(new_items)) + " new upvotes to add to raindrop (filtered " + str(len(hackernews_items) - len(new_items)) + " duplicates)")

        if len(new_items) > 0:
            items = [item.toDict() for item in new_items]

            for batch in grouper(items, 100):
                batch = [i for i in batch if i is not None]
                payload = {"items": batch}

                logging.debug("POST https://api.raindrop.io/rest/v1/raindrops")
                response = requests.post(
                    "https://api.raindrop.io/rest/v1/raindrops",
                    headers={"Authorization": "Bearer " + RAINDROP_API_TOKEN},
                    json=payload,
                )

                if response.status_code == 200:
                    logging.debug("Success")
                else:
                    logging.error(
                        "Couldn't post multiple items to raindrop ("
                        + str(response.status_code)
                        + ": "
                        + response.reason
                        + ")"
                    )
                    exit(1)

    def empty_collection(self):
        response = requests.delete(
            "https://api.raindrop.io/rest/v1/raindrops/" + RAINDROP_COLLECTION_ID,
            headers={"Authorization": "Bearer " + RAINDROP_API_TOKEN},
        )
        if response.status_code == 200:
            # empty the trash (collection id -99) to prevent filling it up with old deleted items
            requests.delete(
                "https://api.raindrop.io/rest/v1/raindrops/-99",
                headers={"Authorization": "Bearer " + RAINDROP_API_TOKEN},
            )
            logging.info("Collection emptied successfully")
        else:
            logging.error(
                "couldn't remove existing raindrops. Check your raindrop collection id and token are correct"
            )
            exit(1)


class hackernews:
    def __init__(self):
        self._items = []
        self._seen_urls = set()
        self._session = requests.Session()
        self._session.headers.update(
            {"User-Agent": "Mozilla/5.0 (compatible; hn2raindrop/1.0)"}
        )

    class _item:
        def __init__(self, title, link, date):
            self.title = title
            self.link = link
            self.created = date
            self.lastUpdate = date

        def toDict(self):
            return {
                "title": self.title,
                "excerpt": "",
                "tags": ["hackernews", "imported"],
                "link": self.link,
                "created": self.created,
                "lastUpdate": self.lastUpdate,
                "collection": {
                    "$ref": "collections",
                    "$id": RAINDROP_COLLECTION_ID,
                    "oid": "-1",
                },
            }

    def login(self):
        logging.info("Logging into hackernews")

        # Fetch the login page to get the CSRF token (fnid)
        login_page = self._session.get("https://news.ycombinator.com/login?goto=news")
        tree = html.fromstring(login_page.text)
        fnid_values = tree.xpath('//input[@name="fnid"]/@value')

        if fnid_values:
            fnid = fnid_values[0]
            p = self._session.post(
                "https://news.ycombinator.com/login",
                data={
                    "acct": username,
                    "pw": password,
                    "fnid": fnid,
                    "goto": "news",
                },
            )
        else:
            # Fallback: post directly without fnid
            logging.debug("No fnid found, attempting direct login")
            p = self._session.post(
                "https://news.ycombinator.com/login?goto=news",
                data={"acct": username, "pw": password},
            )

        if ("user?id=" + username) in p.text:
            logging.info("Hackernews - login successful")
        else:
            logging.fatal("Hackernews - login failed")
            exit(1)

    def _request_and_process(self, url):
        logging.debug("Hackernews - get " + url)
        response = self._session.get(url)
        tree = html.fromstring(response.text)

        titles = tree.xpath('//span[@class="titleline"]/a/text()')
        links = tree.xpath('//span[@class="titleline"]/a/@href')
        dates = tree.xpath('//span[@class="age"]/@title')

        for title, link, date in zip(titles, links, dates):
            if not link.startswith("item?id=") and link not in self._seen_urls:
                self._seen_urls.add(link)
                self._items.append(self._item(title, link, date))

        morelink = tree.xpath('string(//a[@class="morelink"]/@href)')
        return morelink

    def get_upvotes(self):
        logging.info("Getting hackernews upvotes")
        delay = 1

        morelink = self._request_and_process(
            "https://news.ycombinator.com/upvoted?id=" + username
        )

        while morelink:
            time.sleep(delay)
            logging.debug("GET https://news.ycombinator.com/" + morelink)
            response = self._session.get("https://news.ycombinator.com/" + morelink)

            if response.status_code == 429 or "Sorry" in response.text[:100]:
                delay = min(delay + 1, 10)
                logging.warning("HN rate limited, backing off to " + str(delay) + "s")
                continue

            tree = html.fromstring(response.text)
            titles = tree.xpath('//span[@class="titleline"]/a/text()')
            links = tree.xpath('//span[@class="titleline"]/a/@href')
            dates = tree.xpath('//span[@class="age"]/@title')

            for title, link, date in zip(titles, links, dates):
                if not link.startswith("item?id=") and link not in self._seen_urls:
                    self._seen_urls.add(link)
                    self._items.append(self._item(title, link, date))

            morelink = tree.xpath('string(//a[@class="morelink"]/@href)')

            # Reset delay on success
            delay = 1

        logging.info("Found " + str(len(self._items)) + " hackernews upvotes")

    def items(self):
        return self._items


# Login to hackernews first (before anything else)
hn = hackernews()
hn.login()

# Fetch raindrop collection and hackernews upvotes in parallel
rd = raindrop()
errors = []

def fetch_raindrop():
    try:
        rd.get_collection()
    except Exception as e:
        errors.append(e)

def fetch_hackernews():
    try:
        hn.get_upvotes()
    except Exception as e:
        errors.append(e)

raindrop_thread = threading.Thread(target=fetch_raindrop)
hackernews_thread = threading.Thread(target=fetch_hackernews)

raindrop_thread.start()
hackernews_thread.start()

raindrop_thread.join()
hackernews_thread.join()

if errors:
    for e in errors:
        logging.fatal(str(e))
    exit(1)

# Filter and add new items
rd.add(hn.items())

logging.info("Done!")
