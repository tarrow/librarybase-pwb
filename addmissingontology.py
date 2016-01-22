"""
This script uses a searcher to find all journal articles (those which have a PMCID)
and calls JournalArticle.setItemType() to add both source-type and itemtype.

We don't over add these statements because LibraryBaseItem.makeSimpleClaim()
doesn't allow adding exact duplicate statements by default
"""

import librarybase
import pywikibot

site = pywikibot.Site("librarybase", "librarybase")
searcher = librarybase.LibraryBaseSearch()
articles = searcher.findJournalArticlesMissingOntologicalData()
for item in articles:
    item.setItemType()

