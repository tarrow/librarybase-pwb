import pywikibot
from pywikibot.pagegenerators import PagesFromTitlesGenerator, WikibaseItemGenerator
from epmclib.getPMCID import getPMCID
import queryCiteFile
from SPARQLWrapper import SPARQLWrapper, JSON
from collections import defaultdict
import urllib.error
import time

global sparqlepointurl
sparqlepointurl = "http://sparql.librarybase.wmflabs.org/"
#sparqlepointurl = "http://localhost:9999/"

class LibraryBaseSearch():
    """
    A searcher tool for librarybase that utilises the SPARQL endpoint available at
    sparql.librarybase.wmflabs.org
    """

    def __init__(self, sparqlepointurl="http://sparql.librarybase.wmflabs.org/"):
        self.sparqlepointurl = sparqlepointurl
        pass

    def rawquery(self,querystring):
        """
        Takes a SPARQL query and does the grunt work of submitting it before adding it
        self.results as JSON

        :param querystring: A sparql query string
        :return:
        """
        sparql = SPARQLWrapper("{}bigdata/namespace/lb/sparql".format(self.sparqlepointurl))
        sparql.setQuery(querystring)
        sparql.setReturnFormat(JSON)
        attempts = 0
        while attempts < 10:
            try:
                results = sparql.query().convert()
                break
            except (urllib.error.URLError, urllib.error.HTTPError) as neterror:
                attempts += 1
                continue
        else:
            raise neterror
        self.results = results

    def JournalArticleGenerator(self,gen):
        """
        Converts a generic ItemPage generator into a JournalArticle generator

        :param gen:
        :return:
        """
        for page in gen:
            if isinstance(page, JournalArticlePage):
                yield page
            else:
                yield JournalArticlePage(pywikibot.getSite(), page.title())

    def JournalGenerator(self,gen):
        """
        Converts a generic ItemPage generator into a JournalGenerator
        :param gen:
        :return:
        """
        for page in gen:
            if isinstance(page, JournalPage):
                yield page
            else:
                yield JournalPage(pywikibot.getSite(), page.title())

    def AuthorGenerator(self,gen):
        """
        Converts a generic ItemPage generator into an AuthorGenerator
        :param gen:
        :return:
        """
        for page in gen:
            if isinstance(page, AuthorPage):
                yield page
            else:
                yield AuthorPage(pywikibot.getSite(), page.title())

    def findJournalArticlesMissingOntologicalData(self):
        """
        Returns a Journal Article Generator containing all those items
        which have a PMCID but are missing either source-type OR item type
        claims
        :return:
        """
        querystring = """prefix lbt: <http://librarybase.wmflabs.org/prop/direct/>
						prefix lb: <http://librarybase.wmflabs.org/entity/>

						SELECT DISTINCT ?s WHERE {
						?s lbt:P17 ?r .
						MINUS { ?s lbt:P19 ?o .
						?s lbt:P3 ?l .
						}
						}"""
        self.rawquery(querystring)
        textlist = [line['s']['value'][38:] for line in self.results['results']['bindings']]
        return self.JournalArticleGenerator(PagesFromTitlesGenerator(textlist))

    def findArticleByPMCID(self, id):
        querystring = """
		PREFIX wdt: <http://librarybase.wmflabs.org/prop/direct/>
		SELECT ?s WHERE {
		?s wdt:P17 "%s" .
 		}""" % id
        self.rawquery(querystring)

    def findJournalByISSN(self, issn):
        """
        Returns a Journal generator that contains all those items that are of source-type journal
        and have the ISSN property set to the ISSN parameter.
        This should really only be one since each ISSN is only assigned to one Journal.
        :param issn:
        :return:
        """
        querystring = u"""prefix lbt: <http://librarybase.wmflabs.org/prop/direct/>
						prefix lb: <http://librarybase.wmflabs.org/entity/>

						SELECT DISTINCT ?s WHERE {{
						?s lbt:P3 lb:Q12 .
						?s lbt:P14 '{}'
						}}""".format(issn)
        self.rawquery(querystring)
        textlist = [line['s']['value'][38:] for line in self.results['results']['bindings']]
        return self.JournalGenerator(PagesFromTitlesGenerator(textlist))

    def predictISSNOfJournalsFromISSNOfArticle(self):
        """
        Return a list of journal Items and ISSNs by
        assuming that the ISSN which has wrongly been placed on an item which is published in that journal
        :return:
        """
        querystring = u"""prefix lbt: <http://librarybase.wmflabs.org/prop/direct/>
						prefix lb: <http://librarybase.wmflabs.org/entity/>

						SELECT ?journal ?issn WHERE {
						?s lbt:P4 ?journal .
						?s lbt:P14 ?issn
						}"""
        self.rawquery(querystring)
        return [[line['journal']['value'][39:],line['issn']['value']] for line in self.results['results']['bindings']]

    def findJournalArticleswithISSNThatPointToJournalWithoutISSN(self):
        """
        Return list of Journal Articles that point to a journal and the  journal item has no ISSN claim
        However the journal article item (wrongly) does.
        :return:
        """
        querystring = u"""prefix lbt: <http://librarybase.wmflabs.org/prop/direct/>
						prefix lb: <http://librarybase.wmflabs.org/entity/>

						SELECT DISTINCT ?s WHERE {{
						?s lbt:P4 ?journal .
						?s lbt:P14 ?issn .
                        OPTIONAL {?journal lbt:P14 ?issn2}
                          FILTER(!bound(?issn2))
						}}"""
        self.rawquery(querystring)
        textlist = [line['s']['value'][38:] for line in self.results['results']['bindings']]
        return self.JournalArticleGenerator(PagesFromTitlesGenerator(textlist))


class LibraryBasePage(pywikibot.ItemPage):
    def __init__(self, site, title=None, ns=None):
        pywikibot.ItemPage.__init__(self, site, title, ns)

    def getClaims(self, property):
        """Get all the claims of a given property from an item"""
        if not hasattr(self, 'claims'):
            self.get()
        if self.claims:
            if property in self.claims:
                return self.claims[property]
        return []

    def getClaimTargets(self, property):
        """
        Gets the targets of the claims for a given property of the current LibraryBase page
        :param property:
        :return:
        """
        claims=self.getClaims(property)
        return [claim.getTarget() for claim in claims]


    def makeSimpleClaim(self, property, target, reference='EPMC'):
        """
        Add a simple claim to an item by just giving it a property and a target
        Also adds a default reference for the claim.
        TODO: Break out the add reference bit to another method and make more sensible defaults
        :param property:
        :param target:
        :param reference:
        :return:
        """
        if not hasattr(self, 'claims'):
            self.get()
        claim = pywikibot.Claim(self.site, property)
        claim.setTarget(target)
        claimShouldBeMade=True
        if claim.getTarget() in self.getClaimTargets(property):
            #print('Claim shouldn\'t be made: it is already present on article {}'.format(self.getID()))
            claimShouldBeMade=False
        if claimShouldBeMade:
            #print('adding claim to {}: {} targetting {}'.format(self.getID(), claim.getID(), claim.getTarget()))
            self.addClaim(claim)
            if reference == 'EPMC':
                #print('with reference to EPMC')
                fromEPMCClaim = pywikibot.Claim(self.site, 'P20')
                fromEPMCClaim.setTarget(pywikibot.ItemPage(self.site, title='Q335'))
                claim.addSource(fromEPMCClaim)

    def addDelayedClaim(self, property, target, reference='EPMC'):
        """
        Add a delayed claim claim to an item by just giving it a property and a target
        Also adds a default reference for the claim.
        :param property:
        :param target:
        :param reference:
        :return:
        """
        if not hasattr(self, 'claims'):
            self.get()
        claim = pywikibot.Claim(self.site, property)
        claim.setTarget(target)
        claimShouldBeMade=True
        if claim.getTarget() in self.getClaimTargets(property):
            #Claim shouldn't be made: it is already present on article
            claimShouldBeMade=False
        if claimShouldBeMade:
            #print('adding claim to {}: {} targetting {}'.format(self.getID(), claim.getID(), claim.getTarget()))
            claim.id=claim.getID()
            if reference == 'EPMC':
                #print('with reference to EPMC')
                fromEPMCClaim = pywikibot.Claim(self.site, 'P20')
                fromEPMCClaim.setTarget(pywikibot.ItemPage(self.site, title='Q335'))
                sources = defaultdict(list)
                sources[fromEPMCClaim.getID()].append(fromEPMCClaim)
                claim.sources.append(sources)
            #handle self.claims not existing
            if not self.claims:
                self.claims = defaultdict(list)
            if not property in self.claims:
                self.claims[property]=[]
            #actually incrfease claims
            self.claims[property].append(claim)


    def getItemType(self):
        """
        Get type of item from a dict of 'vanity names for items'.
        TODO: This should now use get claim targets.
        :return:
        """
        self.get()
        if self.claims:
            if 'P19' in self.claims:
                return { 'Q264' : 'source',
                         'Q265' : 'person',
                         'Q262' : 'meta',
                         'Q263' : 'source-type',
                         'Q266' : 'organisation'
                }.get(self.claims['P19'][0].getTarget().id,'unknown') # unknown means target is not in list above
            else:
                return 'unspecified' #this means no P19 (item type) statement

class AuthorPage(LibraryBasePage):
    def setName(self, name):
        self.editLabels( {'en': {'language': 'en', 'value': name}} )

    def addOrcid(self, orcid):
        self.makeSimpleClaim('P18', orcid)

    def setItemType(self):
        self.makeSimpleClaim('P19', pywikibot.ItemPage(self.site, title='Q265'), reference=None) #type of item - source

class JournalArticlePage(LibraryBasePage):

    def setItemType(self):
        self.makeSimpleClaim('P19', pywikibot.ItemPage(self.site, title='Q264'), reference=None)
        self.makeSimpleClaim('P3', pywikibot.ItemPage(self.site, title='Q10'), reference=None) #type of source item - jounal item

    def setTitle(self, title):
        if len(title)>249:
            title=title[:249]
        self.editLabels( {'en': {'language': 'en', 'value': title}} )
    #self.makeSimpleClaim('P2', title)
    #Type of source = journal article

    def addAuthor(self, author):
        """
        Test whether or not the metadata from the provider has an orcid for this author
        If so we see if we already have an item for it. If we have an item we make the claim; if not we make it and
        make the claim. Otherwise we just make an item and claim it without an Orcid being involved.
        :param author:
        :return:
        """
        authorPage=AuthorPage(self.site)
        if author in self.metadata['orcids']:
            existingauthor = self.authorAlreadyExists(self.metadata['orcids'][author])
            if existingauthor == False :
                authorPage.setName(author)
                authorPage.addOrcid(self.metadata['orcids'][author])
                authorPage.setItemType()
            else:
                authorPage=AuthorPage(self.site, existingauthor)
        else:
            authorPage.setName(author)
            authorPage.setItemType()
        #print("adding author:" + author)
        self.addDelayedClaim('P2', authorPage)


    def setAuthors(self, authors):
        for author in authors:
            if author:
                self.addAuthor(author)

    def setDate(self, rawdate):
        splitdate = rawdate.split('-')
        date=pywikibot.WbTime(year=int(splitdate[0]), month=int(splitdate[1]), day=int(splitdate[2]), site=self.site)
        self.makeSimpleClaim('P5', date)
    #self.makeSimpleClaim('P5', rawdate)

    def setVolume(self, volume):
        if volume:
            self.addDelayedClaim('P9', volume)

    def setIssue(self, issue):
        if issue:
            self.addDelayedClaim('P10', issue)

    def setPages(self, pages):
        if pages:
            self.addDelayedClaim('P11', pages)

    def setDOI(self, doi):
        if doi:
            self.addDelayedClaim('P13', doi)

    def setISSN(self, issn):
        if issn:
            self.makeSimpleClaim('P14', issn)

    def getISSN(self):
        if not hasattr(self, 'claims'):
            self.get()
        if self.claims:
            if 'P14' in self.claims:
                return self.claims['P14'][0].getTarget()


    def setPMID(self, pmid):
        if pmid:
            self.addDelayedClaim('P15', pmid)

    def setPMCID(self, pmcid):
        self.makeSimpleClaim('P17', pmcid)

    def setArticles(self, pmcid):
        citefile = queryCiteFile.CiteFile()
        articles = citefile.findPagesIDAppears(pmcid)
        for idx, article in enumerate(articles):
            #print(idx)
            self.addArticle(article)

    def addArticle(self, article):
        self.addDelayedClaim('P8', article)

    def setJournal(self, journal, issn=None):
        newJournalItemNeeded = True
        if issn:
            searcher=LibraryBaseSearch()
            journals=searcher.findJournalByISSN(issn)
            try:
                journalpage = next(journals)
                newJournalItemNeeded = False
            except StopIteration: pass
        if newJournalItemNeeded:
            journalpage = JournalPage(self.site)
            journalpage.editLabels( {'en': {'language': 'en', 'value': journal}} )
            journalpage.setItemType()
        self.makeSimpleClaim('P4', journalpage)

    def setMetaData(self, metadata):
        self.metadata = metadata
        self.setTitle(metadata['title'])
        self.setItemType()
        self.setPMCID(metadata['pmcid'])
        self.setDate(metadata['date'])
        self.setVolume(metadata['volume'])
        self.setIssue(metadata['issue'])
        self.setPages(metadata['pages'])
        self.setJournal(metadata['journal'],metadata['issn'])
        self.setDOI(metadata['doi'])
        #self.setISSN(metadata['issn'])
        self.setPMID(metadata['pmid'])
        self.setAuthors(metadata['authors'])
        self.setArticles(metadata['pmcid'])
        self.editEntity()


    def articleAlreadyExists(self, id):
        sparql = SPARQLWrapper("{}bigdata/namespace/lb/sparql".format(sparqlepointurl))
        querystring = """
		PREFIX wdt: <http://librarybase.wmflabs.org/prop/direct/>
		SELECT ?s WHERE {
		?s wdt:P17 "%s" .
 		}""" % id
        sparql.setQuery(querystring)
        sparql.setReturnFormat(JSON)
        attempts = 0
        while True:
            try:
                results = sparql.query().convert()
                break
            except (urllib.error.URLError, urllib.error.HTTPError) as neterror:
                attempts += 1
                time.sleep(3)
                continue
        else:
            print('attempts' + attempts)
            raise urllib.error.URLError
        if len(results["results"]["bindings"]) >= 1:
            return True
        else:
            return False

    def authorAlreadyExists(self, orcid):
        sparql = SPARQLWrapper("{}bigdata/namespace/lb/sparql".format(sparqlepointurl))
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

    def authorAlreadyExists(self, orcid):
        sparql = SPARQLWrapper("{}bigdata/namespace/lb/sparql".format(sparqlepointurl))
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

class JournalPage(LibraryBasePage):
    def setItemType(self):
        self.makeSimpleClaim('P19', pywikibot.ItemPage(self.site, title='Q264'))
        self.makeSimpleClaim('P3', pywikibot.ItemPage(self.site, title='Q12'), reference=None)

    def setISSN(self, issn):
        if issn:
            self.makeSimpleClaim('P14', issn)





if __name__ == '__main__':
    site = pywikibot.Site("librarybase", "librarybase")
    #repo = site.data_repositry()
    item = JournalArticlePage(site, 'Q261')

    pmcid = 'PMC3315379'

    pmcidobj = getPMCID(pmcid)
    pmcidobj.getBBasicMetadata()
    metadata = pmcidobj.metadata

    #print(item.articleAlreadyExists(metadata['pmcid']))


    #print(item.authorAlreadyExists('0000-0002-1298-7653'))

    if not item.articleAlreadyExists(metadata['pmcid']):
        print('Setting metadata for: ' + metadata['pmcid'])
        item.setMetaData(metadata)
    else:
        print("{} already exists".format(metadata['pmcid']))
