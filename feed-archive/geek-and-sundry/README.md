NOTE: According to the Internet Archive's WayBack Machine (as of 2023-04-17):
critrole.com's podcast listings for Campaign 1 switched from the Nerdist feed to
this new Geek & Sundry feed sometime between 2021-10-31 and 2022-02-17. The
earliest snapshot for this feed's Podbean homepage is dated 2022-01-18. The
earliest snapshot of the XML feed is dated 2022-03-26. CritRoleSync favors the
Nerdist feed because the Geek & Sundry feed has historically had some problems
with reliability and bad data in the feed (e.g., zero-duration episodes).

This podcast's homepage is

https://geekandsundry.podbean.com/

and the feed is located at

https://feed.podbean.com/geekandsundry/feed.xml

XML files were obtained using step-1-fetch-feeds.py or, equivalently, the following:

    wget -O feed-YYYY-MM-DD.xml https://feed.podbean.com/geekandsundry/feed.xml

JSON files were derived from XML files using step-2-parse-feeds.py.

DIFF files were derived from JSON files using step-3-diff-feeds.py.
