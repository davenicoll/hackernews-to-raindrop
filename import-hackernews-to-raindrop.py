from lxml import html
import requests
import sys
import os
import time
import numpy
import json

RAINDROP_API_TOKEN=""
RAINDROP_COLLECTION_ID=""

if len(sys.argv) - 1 < 2:
    print("\033[91mERROR: Username and password were not specified!\033[00m")
    print("Usage: python[3] " + sys.argv[0] + " username password [output-file]")
    exit()

username = sys.argv[1]
password = sys.argv[2]

def get_suggested_tags(raindrop_id):
    response = requests.get('https://api.raindrop.io/rest/v1/tags/suggest/'+raindrop_id, headers={'Authorization': "Bearer " + RAINDROP_API_TOKEN } )   
    if response.status_code == 200:
        if response.json().get("result"):
            return response.json().get("tags")
        else:
            return

def get_suggested_tags(raindrop_id):
    response = requests.get('https://api.raindrop.io/rest/v1/tags/suggest/'+raindrop_id, headers={'Authorization': "Bearer " + RAINDROP_API_TOKEN } )   
    if response.status_code == 200:
        if response.json().get("result"):
            return response.json().get("tags")
        else:
            return

def remove_existing_links():
    response = requests.delete('https://api.raindrop.io/rest/v1/raindrops/'+RAINDROP_COLLECTION_ID, headers={'Authorization': "Bearer " + RAINDROP_API_TOKEN } )
    if response.status_code != 200:
        print("\033[91mERROR: couldn't remove existing links. Check your raindrop collection id and token are correct\033[00m")
        exit(1)
    else:
        # empty the trash (collection id -99) to prevent filling it up with old deleted items
        requests.delete('https://api.raindrop.io/rest/v1/raindrops/-99', headers={'Authorization': "Bearer " + RAINDROP_API_TOKEN } )
        print("Old links removed")

def add_to_raindrop(title, link, created):
    print("  title : " + title)
    print("  link  : " + link)
    print("  date  : " + created)

    item = {
        "title":title,
        "excerpt":"",
        "tags": [ "hackernews", "imported" ],
        "link":link,
        "created":created,
        "lastUpdate":created,
        "collection": {
            "$ref": "collections",
            "$id": RAINDROP_COLLECTION_ID,
            "oid": "-1"
        }
    }

    response = requests.post('https://api.raindrop.io/rest/v1/raindrop', headers={'Authorization': "Bearer " + RAINDROP_API_TOKEN }, json=item )
    if response.status_code != 200:
        print("\033[91mERROR: Couldn't post to raindrop\033[00m")
        print(response.text)
        exit(1)

    raindrop_id = str(response.json()['item']['_id'])
    tags = get_suggested_tags(raindrop_id)
    # if there are no tags to update, don't do a pointless update
    if tags is None:
        print("  tags  : nothing suggested ")
        print("  -------")
        return
    else:
        tags.append("hackernews")
        tags.append("imported")

    print("  tags  : " + str(tags))

    item = {
        "title":title,
        "excerpt":"",
        "tags": tags,
        "link":link,
        "created":created,
        "lastUpdate":created,
        "collection": {
            "$ref": "collections",
            "$id": RAINDROP_COLLECTION_ID,
            "oid": "-1"
        }
    }    

    response = requests.put('https://api.raindrop.io/rest/v1/raindrop/'+raindrop_id, headers={'Authorization': "Bearer " + RAINDROP_API_TOKEN }, json=item )
    if response.status_code != 200:
        print("\033[91mERROR: Couldn't update raindrop\033[00m")
        print(response.text)
        exit(1)    

    print("  -------")
    
    time.sleep(0.8)

def get_links(session, url):
    print("Fetching", url)
    response = session.get(url)
    tree = html.fromstring(response.text)
    
    titles = tree.xpath('//span[@class="titleline"]/a/text()')
    links = tree.xpath('//span[@class="titleline"]/a/@href')
    dates = tree.xpath('//span[@class="age"]/@title')
    
    items = numpy.stack((titles, links, dates), axis=1)

    for item in items:
        add_to_raindrop(item[0], item[1], item[2])

    morelink = tree.xpath('string(//a[@class="morelink"]/@href)')
    return morelink

with requests.Session() as session:
    p = session.post('https://news.ycombinator.com/login?goto=news', data={'acct': username,'pw': password})
    if ("user?id=" + username) in p.text:
        print("Login successful")
    else:
        print("\033[91mERROR: Login failed\033[00m")
        exit()

    remove_existing_links()
    #print(get_suggested_tags())
    #exit()

    morelink = get_links(session, 'https://news.ycombinator.com/upvoted?id=' + username)

    while morelink:
        # Mandatory delay between requests, otherwise hackernews complains
        time.sleep(5)

        morelink = get_links(session, "https://news.ycombinator.com/" + morelink)
