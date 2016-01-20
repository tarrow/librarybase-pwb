import librarybase
import pywikibot


site = pywikibot.Site("librarybase", "librarybase")
print(site.siteinfo['extensions'])
searcher = librarybase.LibraryBaseSearch()
articles = searcher.findJournalArticlesMissingOntologicalData()
for item in articles:
    item.setItemType()

