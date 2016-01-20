"""
Find all journal items that have a suggested ISSN because it appears
in an item about and article which appears in the journal.

Find all of these suggested ISSNs and add them to the lowest
Qid journal item.

Then find all journal article items (that have an ISSN) that 'appear' in a journal
item with no ISSN. Lookup the ISSN and if it exists alter the calim so it points
to the right (low Qid) Journal item.

Then merge the higher Qid journal item with the lower one.
"""

import librarybase
import pywikibot

site = pywikibot.Site("librarybase", "librarybase")
searcher = librarybase.LibraryBaseSearch()
journaldict = searcher.predictISSNOfJournalsFromISSNOfArticle()
issndict=dict()
for line in journaldict:
    #print(line[0])
    issndict.setdefault(line[1], []).append(line[0])
print(issndict)
issnlist=[]
for issn, idlist in issndict.items():
    issnlist.append([issn, min(idlist)])

# for line in issnlist:
#     journalitem=librarybase.JournalPage(site, 'Q{}'.format(line[1]))
#     journalitem.setISSN(line[0])
#     journalitem.setItemType()

journalarticles = searcher.findJournalArticleswithISSNThatPointToJournalWithoutISSN()
for journalarticle in journalarticles:
    issn=journalarticle.getISSN()
    #print(issn)
    journal=searcher.findJournalByISSN(issn)
    targetjournal = next(journal)
    if(targetjournal):
        defunctPages=[defunctjournal for defunctjournal in journalarticle.getClaimTargets('P4')]
        #print(defunctPages)
        #journalarticle.removeClaims(journalarticle.getClaims('P4'))
        journalarticle.makeSimpleClaim('P4', targetjournal)
        #print(journalarticle.getClaims('P4'))
        for defunctPage in defunctPages:
            possibleBadClaims=journalarticle.getClaims('P4')
            badClaims = []
            for claim in possibleBadClaims:
                if claim.getTarget()==defunctPage:
                    badClaims.append(claim)
            journalarticle.removeClaims(badClaims)
            defunctPage.mergeInto(targetjournal)


