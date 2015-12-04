import pywikibot
#import epmc
import wikieupmcanalytics
from SPARQLWrapper import SPARQLWrapper, JSON

class LibraryBasePage(pywikibot.ItemPage):
	def makeSimpleClaim(self, property, target):
		if not hasattr(self, 'claims'):
			self.get()
		claim = pywikibot.Claim(self.site, property)
		claim.setTarget(target)
		self.addClaim(claim)


class AuthorPage(LibraryBasePage):
	def setName(self, name):
		self.editLabels( {'en': {'language': 'en', 'value': name}} )

	def addOrcid(self, orcid):
			self.makeSimpleClaim('P18', orcid)


class JournalArticlePage(LibraryBasePage):

	def setTitle(self, title):
		self.editLabels( {'en': {'language': 'en', 'value': title}} )
		#self.makeSimpleClaim('P2', title)
		#Type of source = journal article
		journalarticlepage = pywikibot.ItemPage(self.site, title='Q10')
		self.makeSimpleClaim('P3', journalarticlepage)

	def addAuthor(self, author):
		authorPage=AuthorPage(self.site)
		if author in metadata['orcids']:
			existingauthor = self.authorAlreadyExists(metadata['orcids'][author])
			if existingauthor == False :

				authorPage.addOrcid(metadata['orcids'][author])
			else:
				authorPage=AuthorPage(self.site, existingauthor)
		else:
			authorPage.setName(author)
		self.makeSimpleClaim('P2', authorPage)


	def setAuthors(self, authors):
		for author in authors:
			self.addAuthor(author)

	def setDate(self, rawdate):
		splitdate = rawdate.split('-')
		date=pywikibot.WbTime(year=int(splitdate[0]), month=int(splitdate[1]), day=int(splitdate[2]), site=self.site)
		self.makeSimpleClaim('P5', date)
		#self.makeSimpleClaim('P5', rawdate)

	def setVolume(self, volume):
		self.makeSimpleClaim('P9', volume)

	def setIssue(self, issue):
		self.makeSimpleClaim('P10', issue)

	def setPages(self, pages):
		self.makeSimpleClaim('P11', pages)

	def setDOI(self, doi):
		self.makeSimpleClaim('P13', doi)

	def setISSN(self, issn):
		self.makeSimpleClaim('P14', issn)

	def setPMID(self, pmid):
		self.makeSimpleClaim('P15', pmid)

	def setPMCID(self, pmcid):
		self.makeSimpleClaim('P17', pmcid)

	def setArticles(self, pmcid):
		articles = wikieupmcanalytics.findPagesIDAppears(pmcid)
		for idx, article in enumerate(articles):
			print(idx)
			self.addArticle(article)

	def addArticle(self, article):
		self.makeSimpleClaim('P8', article)

	def setJournal(self, journal):
		journalpage = pywikibot.ItemPage(self.site)
		journalpage.editLabels( {'en': {'language': 'en', 'value': journal}} )

		self.makeSimpleClaim('P4', journalpage)

	def setMetaData(self, metadata):
		self.setTitle(metadata['title'])
		self.setDate(metadata['date'])
		self.setVolume(metadata['volume'])
		self.setIssue(metadata['issue'])
		self.setPages(metadata['pages'])
		self.setJournal(metadata['journal'])
		self.setDOI(metadata['doi'])
		self.setISSN(metadata['issn'])
		self.setPMID(metadata['pmid'])
		self.setPMCID(metadata['pmcid'])
		self.setAuthors(metadata['authors'])
		self.setArticles(metadata['pmcid'])

	def itemAlreadyExists(self, id):
		sparql = SPARQLWrapper("http://sparql.librarybase.wmflabs.org/bigdata/namespace/wdq/sparql")
		querystring = """
		PREFIX wdt: <http://librarybase.wmflabs.org/prop/direct/>
		SELECT ?s WHERE {
		?s wdt:P17 "%s" .
 		}""" % id
		sparql.setQuery(querystring)
		sparql.setReturnFormat(JSON)
		results = sparql.query().convert()
		if len(results["results"]["bindings"]) >= 1:
			return True
		else:
			return False

	def authorAlreadyExists(self, orcid):
		sparql = SPARQLWrapper("http://sparql.librarybase.wmflabs.org/bigdata/namespace/wdq/sparql")
		querystring = """
		PREFIX wdt: <http://librarybase.wmflabs.org/prop/direct/>
		SELECT ?s WHERE {
		?s wdt:P18 "%s" .
 		}""" % orcid
		sparql.setQuery(querystring)
		sparql.setReturnFormat(JSON)
		results = sparql.query().convert()
		if len(results["results"]["bindings"]) >= 1:
			return results["results"]["bindings"][0]["s"]["value"][38:]
		else:
			return False



site = pywikibot.Site("librarybase", "librarybase")
#repo = site.data_repository()
item = JournalArticlePage(site)

pmcid = 'PMC514446'

metadata = epmclib.searchByPmid(pmcid);

#print(item.authorAlreadyExists('0000-0002-1298-7653'))

if not item.itemAlreadyExists(pmcid):
	item.setMetaData(metadata)
else:
	print("%s already exists") % pmcid

#print(metadata)

#item.setMetaData(metadata)

#wikieupmcanalytics.findPagesIDAppears('139241')

#print(item.get())
#print(item.get())

