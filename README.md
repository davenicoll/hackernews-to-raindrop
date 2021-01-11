# Hacker News upvoted posts saving and syncing

Hacker News doesn't have an API, and mobile apps usually implement their own post saving/bookmarking mechanism. Frustrated with the lack of searchability, I decided to sync posts which I upvote to my raindrop.io account.

## Getting Started

Run get-hn-upvoted.py first.

```
python3 get-hn-upvoted.py your-username your-password 
```

This'll create a file called `hackernews.txt` containing a list of links to posts you've upvoted.

To upload the links to raindrop.io, create an API token, and add it to import-hackernews-to-raindrop.sh. Run it.

```
./import-hackernews-to-raindrop.sh
```
