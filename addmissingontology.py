import librarybase
import pywikibot



site = pywikibot.Site("librarybase", "librarybase")
searcher = librarybase.LibraryBaseSearch()
articles = searcher.findJournalArticlesMissingOntologicalData()
for item in articles:
	if item.getItemType() == 'unspecified':
		claim = pywikibot.Claim(site, 'P19')
		claim.setTarget(pywikibot.ItemPage(site, title='Q264'))
		if item.claims:
			if 'P19' in item.claims:
				target = i.getTarget() for i in item.claims['P19']
				print(target)