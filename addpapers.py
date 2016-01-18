import queryCiteFile
import librarybase
import pywikibot
from epmclib.getPMCID import getPMCID
from epmclib.exceptions import IDNotResolvedException

citefile = queryCiteFile.CiteFile()
citations = citefile.findRowsWithIDType('pmc')
for citation in citations[:100]:
	print('trying to add' + citation[5])
	site = pywikibot.Site("librarybase", "librarybase")
	item = librarybase.JournalArticlePage(site)
	pmcidobj = getPMCID(citation[5])
	try:
		pmcidobj.getBBasicMetadata()
	except IDNotResolvedException:
		print('Couldn\'t find in EPMC:' + citation[5])
		continue
	metadata = pmcidobj.metadata
	if not item.articleAlreadyExists(metadata['pmcid']):
		print('Item doesn\'t seem to exist. Setting metadata for: ' + metadata['pmcid'])
		item.setMetaData(metadata)
	else:
		print("{} already exists. Doing nothing".format(metadata['pmcid']))