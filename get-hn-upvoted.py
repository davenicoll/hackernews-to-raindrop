from lxml import html
import requests
import sys
import os

if len(sys.argv) - 1 < 2:
    print("\033[91mERROR: Username and password were not specified!\033[00m")
    print("Usage: python[3] " + sys.argv[0] + " username password [output-file]")
    exit()

username = sys.argv[1]
password = sys.argv[2]

try:
    output_file = sys.argv[3]
except IndexError:
    output_file = "hackernews.txt"

def get_links(session, url):
    print("Fetching", url)
    response = session.get(url)
    tree = html.fromstring(response.content)

    #titles = tree.xpath('//a[@class="storylink"]/text()')
    links = tree.xpath('//a[@class="storylink"]/@href')

    try:
        f = open(output_file, "a")
    except IOError:
        print("\033[91mERROR: Can't write to " + output_file + "\033[00m")
        exit()

    for i in links:
        if "item?id=" in i:
            i = "https://news.ycombinator.com/" + i
        f.write(i + "\n")
    f.close()

    morelink = tree.xpath('string(//a[@class="morelink"]/@href)')

    return morelink

if os.path.exists(output_file):
  os.remove(output_file)

with requests.Session() as session:
    p = session.post('https://news.ycombinator.com/login?goto=news', data={'acct': username,'pw': password})
    if ("user?id=" + username) in p.text:
        print("Login successful")
    else:
        print("\033[91mERROR: Login failed\033[00m")
        exit()

    morelink = get_links(session, 'https://news.ycombinator.com/upvoted?id=' + username)

    while morelink:
        morelink = get_links(session, "https://news.ycombinator.com/" + morelink)