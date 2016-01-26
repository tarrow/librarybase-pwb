import queryCiteFile
import librarybase
import pywikibot
from epmclib.getPMCID import getPMCID
from epmclib.exceptions import IDNotResolvedException
import queue
import threading

def worker():
    while True:
        idx, citation = q.get()
        print(citation)
        if citation is None:
            break
        print('trying to add {} number {}'.format(citation[5], idx))
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
        q.task_done()

q=queue.Queue()
threads = []
for i in range(3):
    t = threading.Thread(target=worker)
    t.start()
    threads.append(t)

citefile = queryCiteFile.CiteFile()
citations = citefile.findRowsWithIDType('pmc')
for citation in enumerate(citations):
    q.put(citation)

q.join()

for i in range(3):
    q.put(None)
for t in threads:
    t.join()
