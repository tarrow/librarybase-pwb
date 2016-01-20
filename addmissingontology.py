import librarybase
import pywikibot

site = pywikibot.Site("librarybase", "librarybase")
searcher = librarybase.LibraryBaseSearch()
articles = searcher.findJournalArticlesMissingOntologicalData()
for item in articles:
    item.setItemType()

