NOTE: As of September 2024, the Nerdist and Geek & Sundry feeds have collapsed
into a single source. One was taken down, and the other appears to be well
maintained. CritRoleSync will resume fetching feeds under the geek-and-sundry
directory, so the nerdist directory will not be updated.

NOTE: As of early 2022, it seems that the Geek & Sundry feed is favored over
this Nerdist feed as being "official", according to critrole.com's list for
Campaign 1 podcast episodes. CritRoleSync favors the Nerdist feed because the
Geek & Sundry feed has historically had some problems with reliability and bad
data in the feed (e.g., zero-duration episodes).

This podcast feed's homepage is

http://critrole.nerdistind.libsynpro.com/website

and the feed is located at

http://critrole.nerdistind.libsynpro.com/rss

XML files were obtained using step-1-fetch-feeds.py or, equivalently, the following:

    wget -O feed-YYYY-MM-DD.xml http://critrole.nerdistind.libsynpro.com/rss

JSON files were derived from XML files using step-2-parse-feeds.py.

DIFF files were derived from JSON files using step-3-diff-feeds.py.
