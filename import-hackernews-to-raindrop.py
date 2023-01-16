import sys
import time
import os
import tempfile
import logging
import requests
import numpy
from os import path
from itertools import zip_longest
from lxml import html

# SET THIS TO YOUR RAINDROP API TOKEN
RAINDROP_API_TOKEN = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

# SET THIS TO YOUR RAINDROP COLLECTION ID
RAINDROP_COLLECTION_ID = "xxxxxxxx"

TEMP_FILE = os.path.join(tempfile.gettempdir(), "hn2rdtemp")

logging.basicConfig(format="[%(levelname)s] %(message)s", level=logging.INFO)
logging.debug("Log level: " + logging.getLevelName(logging.root.getEffectiveLevel()))


if len(sys.argv) - 1 < 2:
    print("\033[91mERROR: Hackernews username and password were not specified!\033[00m")
    print("Usage: python[3] " + sys.argv[0] + " username password")
    exit(1)

username = sys.argv[1]
password = sys.argv[2]


# remove any old temp files
if path.exists(TEMP_FILE):
    os.remove(TEMP_FILE)


def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


class raindrop:
    def __init__(self):
        self.get_collection()

    def url_exists(self, url):
        if not path.exists(TEMP_FILE):
            logging.debug("History file does NOT exist")
            return False

        with open(TEMP_FILE) as f:
            if url in f.read():
                # logging.debug("URL already exists in raindrop (" + url + ")")
                return True

        # logging.debug("URL does NOT exist in raindrop (" + url + ")")
        return False

    def get_collection(self):
        logging.info("Getting raindrop collection")
        PAGE = 0
        ITEM_COUNT = 50

        while ITEM_COUNT > 0:
            request_url = (
                "https://api.raindrop.io/rest/v1/raindrops/"
                + RAINDROP_COLLECTION_ID
                + "?page="
                + str(PAGE)
                + "&perpage=50"
            )

            logging.debug("GET " + request_url)

            response = requests.get(
                request_url,
                headers={"Authorization": "Bearer " + RAINDROP_API_TOKEN},
            )

            if response.status_code == 200:
                ITEM_COUNT = len(response.json()["items"])
                for LINK in response.json()["items"]:
                    history_file = open(TEMP_FILE, "a")
                    logging.debug("Save " + LINK["link"] + " to " + TEMP_FILE)
                    history_file.write(LINK["link"] + "\n")
                    history_file.close()
                PAGE += 1
            else:
                logging.fatal("Failed getting raindrop items")
                exit(1)

            # Avoid 502 bad gateway errors
            time.sleep(5)

    def add(self, hackernews_items):
        logging.info(str(len(hackernews_items)) + " upvotes to add to raindrop")
        if len(hackernews_items) > 0:
            items = []
            for group in grouper(hackernews_items, 100):
                for item in group:
                    if item is not None:
                        items.append(item.toDict())

            items = {"items": items}

            logging.debug(items)

            logging.debug("POST https://api.raindrop.io/rest/v1/raindrops")
            response = requests.post(
                "https://api.raindrop.io/rest/v1/raindrops",
                headers={"Authorization": "Bearer " + RAINDROP_API_TOKEN},
                json=items,
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
        self.get_upvotes()

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

        # def toJSON(self):
        #     return str(
        #         json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)
        #     )

    def _request_and_process(self, session, url):
        logging.debug("Hackernews - get " + url)
        response = session.get(url)
        tree = html.fromstring(response.text)

        titles = tree.xpath('//span[@class="titleline"]/a/text()')
        links = tree.xpath('//span[@class="titleline"]/a/@href')
        dates = tree.xpath('//span[@class="age"]/@title')

        items = numpy.stack((titles, links, dates), axis=1)

        for item in items:
            if item[1].startswith("item?id=") is False:
                if rd.url_exists(item[1]) is False:
                    self._items.append(self._item(item[0], item[1], item[2]))

        morelink = tree.xpath('string(//a[@class="morelink"]/@href)')
        return morelink

    def get_upvotes(self):
        logging.info("Getting hackernews upvotes")
        with requests.Session() as session:
            p = session.post(
                "https://news.ycombinator.com/login?goto=news",
                data={"acct": username, "pw": password},
            )
            if ("user?id=" + username) in p.text:
                logging.debug("Hackernews - login successful")
            else:
                logging.fatal("Hackernews - login failed")
                exit(1)

            logging.debug("GET https://news.ycombinator.com/upvoted?id=" + username)
            morelink = self._request_and_process(
                session, "https://news.ycombinator.com/upvoted?id=" + username
            )

        while morelink:
            # Mandatory delay between requests, otherwise hackernews complains
            time.sleep(5)
            logging.debug("GET https://news.ycombinator.com/" + morelink)
            morelink = self._request_and_process(
                session, "https://news.ycombinator.com/" + morelink
            )

    def items(self):
        return self._items


rd = raindrop()
hn = hackernews()
rd.add(hn.items())

logging.info("Done!")
