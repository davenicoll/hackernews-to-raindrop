#!/bin/bash
# Script borrowed from github stars / gists syncing

MARKDOWN_FILE="hackernews.txt"
LINKS_FILE="hackernews-links.html"
TOKEN=""

# Get the id of the target raindrop.io collection
COLLECTION_ID=$(curl -H "Authorization: Bearer $TOKEN" https://api.raindrop.io/rest/v1/collections | jq -rc '.items[] | select(.title=="Hacker News") ._id')

# Get only http(s) links from the file
cat "$MARKDOWN_FILE" | grep -Eo "(http|https)://[a-zA-Z0-9./?=_%:-]*" > "$LINKS_FILE"

# Add batches of 100 links to raindrop.io
while mapfile -t -n 100 links && ((${#links[@]})); do
    LINKS=$(printf '%s\n' "${links[@]}" | awk -F: '{print "{ \"link\":\"",$0,"\",\"collection\": {  \"$ref\": \"collections\", \"$id\": '$COLLECTION_ID', \"oid\": -1 } },"}' | sed 's/\" http/\"http/g' | sed 's/ \",\"coll/\",\"coll/g')
    JSON=$( echo '{ "items": [ '${LINKS::-1}' ] }' | jq -rc '.')
    curl -X POST -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" -d "$JSON" https://api.raindrop.io/rest/v1/raindrops
done < $LINKS_FILE
