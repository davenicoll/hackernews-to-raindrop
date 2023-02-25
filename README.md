# Import Hacker News upvoted posts to raindrop.io

Hacker News doesn't have an API, and mobile apps usually implement their own post saving/bookmarking mechanism. For convenience, I decided to sync posts which I upvote to my raindrop.io account.

![SCR-20220928-eqn](https://user-images.githubusercontent.com/690117/192851124-735a47e5-6e0f-493e-a73f-09301ad97406.png)

## Getting Started

Install required dependencies
```
pip install -r requirements.txt
```

Then add your raindrop API token and collection ID to `import-hackernews-to-raindrop.py`
```
RAINDROP_API_TOKEN="your-token-goes-here"
RAINDROP_COLLECTION_ID="your-collection-id-goes-here"
```

Finally, run `import-hackernews-to-raindrop.py`

```
python3 import-hackernews-to-raindrop.py your-username your-password 
```
Voila!
