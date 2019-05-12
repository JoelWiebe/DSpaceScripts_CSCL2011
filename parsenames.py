#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import getopt
import shutil
from nameparser import HumanName
from string import Template
import datetime
import os
import subprocess
from xml.sax.saxutils import escape
from itertools import zip_longest
import re

#constants
VOL_FILENAME_INDEX = 0 #filename of pdf
VOL_TITLE_INDEX = 1 #title for citation (including volume)
VOL_FIRST_PAGE_INDEX = 2 #first page of first paper in the volume
VOL_PAGE_OFFSET_INDEX = 3 #pdf page number minus written page number
VOL_LAST_PAPER_INDEX = 4 #first page of last paper of last volume
VOL_END_PAGE = 5 #page after last page of last paper of last volume

ENTRY_START_PAGE_INDEX = 0
ENTRY_TITLE_INDEX = 1
ENTRY_AUTHORS_INDEX = 2
ENTRY_VOL_NUM_INDEX = 3
ENTRY_PAPER_TYPE_INDEX = 4

#UPDATE VALUES
volumes = [['CSCL2011_Conference_Proceedings_Vol1.pdf','Connecting Computer-Supported Collaborative Learning to Policy and Practice: CSCL2011 Conference Proceedings. Volume I — Long Papers',1,36,558,566],['CSCL2011_Conference_Proceedings_Vol2.pdf','Connecting Computer-Supported Collaborative Learning to Policy and Practice: CSCL2011 Conference Proceedings. Volume II — Short Papers & Posters',566,-531,1006,1008],['CSCL2011_Conference_Proceedings_Vol3.pdf','Connecting Computer-Supported Collaborative Learning to Policy and Practice: CSCL2011 Conference Proceedings',1014,-973,1312,1314]]

#list of paper types and their starting pages
papertypeandstart = [("Long Papers", -1),("Short Papers", 565),("Posters",858),("Symposia",1008),("Interactive Events, Demonstrations and CSCL in Practice Showcases",1119),("Pre-Conference Events: Tutorials",1192),("Pre-Conference Events: Workshops",1198),("Doctoral Consortium",1206),("Early Career Workshops",1288),("Post-Conference Events",1290)] 

#the registrant created suffix used prior to the id; conference + year (e.g. cscl2014)
doisuffix = "cscl2011"

#conference year
conferenceyear = 2011

#list of editors for citation; get this from the proceedings citation recommendation
editors = "Spada, H., Stahl, G., Miyake, N., Law, N."

#publisher location used for citation
publisher = "International Society of the Learning Sciences"

#date that the conference took place in the format yyyy-mm
issued = "2011-06"

splitPDFs = True
printfullmetadata = True
createimportfiles = True

subj = Template(u'<dc:subject xml:lang="en">$subject</dc:subject>')
def subjects(sstr):
    s = sstr.split(',')
    return "\n".join([escape(subj.substitute(subject=x.strip())) for x in s])
def genDatetime():
    return datetime.datetime.now().isoformat()[0:19] + 'Z'

author = Template(u'<dcvalue element="contributor" qualifier="author">$author</dcvalue>')
def makeAuthors(authors):
    return "\n".join([author.substitute(author=y.last + ", " + (y.first + ' ' + y.middle).strip()) for y in [HumanName(x) for x in names]])

def makeAuthorCit(name):
    y = HumanName(name)
    if name == '' or y.first == '':
        return ''
    init = y.first[0] + '.'
    if y.middle != '':
        init = init + ' ' + y.middle[0] + '.'
    return y.last + ", " + init

def makeAuthorsCit(ys):
    if len(ys) == 1:
        return makeAuthorCit(ys[0])
    if len(ys) == 2:
        return escape(makeAuthorCit(ys[0]) + " & " + makeAuthorCit(ys[1]))
    start =  ", ".join([makeAuthorCit(y) for y in ys[:-1]]).strip()
    return escape(start + ", & " + makeAuthorCit(ys[-1:][0]))

item = Template(u"""<?xml version="1.0" encoding="utf-8" standalone="no"?>
    <dublin_core schema="dc">
    $authors
      <dcvalue element="date" qualifier="accessioned">$datetime</dcvalue>
      <dcvalue element="date" qualifier="available">$datetime</dcvalue>
      <dcvalue element="date" qualifier="issued">$issued</dcvalue>
      <dcvalue element="identifier" qualifier="citation" language="en_US">$authorscit&#x20;($conferenceyear).&#x20;$title.&#x20;In&#x20;$editors&#x20;(Eds.),&#x20;$volumetitle&#x20;(pp.&#x20;$pages).&#x20;$publisher.</dcvalue>
      <dcvalue element="identifier" qualifier="uri">https://doi.dx.org&#x2F;10.22318&#x2F;$doisuffix.$id</dcvalue>
      <dcvalue element="description" qualifier="abstract" language="en_US">$abstract</dcvalue>
      <dcvalue element="language" qualifier="iso" language="en_US">en</dcvalue>
      <dcvalue element="publisher" qualifier="none" language="en_US">$publisher</dcvalue>
      <dcvalue element="title" qualifier="none" language="en_US">$title</dcvalue>
      <dcvalue element="type" qualifier="none" language="en_US">$type</dcvalue>
    </dublin_core>
""")

argv = sys.argv[1:]

try:
    if len(argv) > 0:
        opts, args = getopt.getopt(argv, "h", ["ns","nf","ni"])

        for opt, arg in opts:
            if opt == '-h':
                print("parsenames.py [--ns] [--nf] [--ni]")
                sys.exit()
            elif opt == '--ns':
                print("No splitting of PDFs or converting to text")
                splitPDFs = False
            elif opt == '--nf':
                print("No full metadata file creation")
                printfullmetadata = False
            elif opt == '--ni':
                print("No import files creation")
                createimportfiles = False

except getopt.GetoptError:
    print("parsenames.py [--ns] [--nf] [--ni]")

f = open('newtoc', 'r').read().strip().split('\n')

g  =list(zip(*[iter(f)]*2))

cs = []
for group in g:
    line = group[0].replace("\r", "").strip()
    fline = re.match(r"(.+?) *\.+? *(\d+?)$", line)
    title = fline.groups(1)[0].strip()
    page = fline.groups(1)[1].strip()
    authors = group[1].replace("\r", "").strip()

    #Get the volume number for current TOC entry
    volumeindex = 0
    for currvolumeindex, currvolume in enumerate(volumes):
        if int(page) >= currvolume[VOL_FIRST_PAGE_INDEX] and int(page) < currvolume[VOL_END_PAGE]:
            volumeindex = currvolumeindex
    volumenumber = volumeindex+1
    
    papertype = None
    for currpapertype, currpaperstart in papertypeandstart:
        if int(page) >= currpaperstart:
            papertype = currpapertype

    if papertype == None:
        raise valueError ("No paper type was assigned", int(page), title, authors) 

    cs.append([int(page), title, authors, volumenumber, papertype])

metadatafile = open("rawmetadata.txt","w+")
metadatafile.write(str(cs))
print("Created rawmetadata.txt")
metadatafile.close()

if printfullmetadata:
    metadatafile = open("fullmetadata.txt","w+")
for idx, c in enumerate(cs):
    startpage = c[ENTRY_START_PAGE_INDEX]

    if startpage == volumes[c[ENTRY_VOL_NUM_INDEX]-1][VOL_LAST_PAPER_INDEX]:
        endpage = volumes[c[ENTRY_VOL_NUM_INDEX]-1][VOL_END_PAGE]
    else:
        endpage = cs[idx+1][ENTRY_START_PAGE_INDEX]

        #Update endpage if there is a section header between papers
        for currpapertype, currpaperstart in papertypeandstart:
            if startpage < currpaperstart and currpaperstart < endpage:
                endpage = currpaperstart

    if splitPDFs:
        pageoffset = volumes[c[ENTRY_VOL_NUM_INDEX]-1][VOL_PAGE_OFFSET_INDEX]
        print("Splitting PDF: page " + str(startpage) + " - " + str(endpage-1) + " from Volume " + str(c[ENTRY_VOL_NUM_INDEX]))
        fin = subprocess.run(['/bin/bash', './split.sh', volumes[c[ENTRY_VOL_NUM_INDEX]-1][VOL_FILENAME_INDEX], str(startpage+pageoffset), str(endpage+pageoffset-1),'pdfs/' + str(startpage) + '-' + str(endpage-1) + '.pdf']) 
        
        fin = subprocess.run(['pdftotext', '-simple', 'pdfs/'+ str(startpage)+'-'+ str(endpage-1)+'.pdf'])

    if printfullmetadata:

        ff = open('pdfs/'+ str(startpage)+"-"+ str(endpage-1)+'.txt', 'rb').read().decode('utf8', 'ignore').strip().replace('\n','ZZZZ')

        match = re.match(r".*Abstract[:.](.+?)ZZZZZZZZ", ff, re.MULTILINE)

        if match:
            abstract = escape(' '.join(match.groups(1)[0].replace('ZZZZ', ' ').split()))
        else:
            abstract = ''

        names = c[ENTRY_AUTHORS_INDEX].split(',')
        authorscit = makeAuthorsCit(names)
        authors = makeAuthors(names)
        id = str(startpage)+'-'+str(endpage-1)
        full = item.substitute(authors=authors, authorscit=authorscit, title=escape(c[ENTRY_TITLE_INDEX]), datetime=genDatetime(),id=str(startpage), abstract=escape(abstract), type=escape(c[ENTRY_PAPER_TYPE_INDEX]), pages=str(startpage)+'-'+str(endpage-1), doisuffix=doisuffix, conferenceyear=conferenceyear, editors=editors, publisher=publisher, issued=issued, volumetitle=volumes[c[ENTRY_VOL_NUM_INDEX]-1][VOL_TITLE_INDEX])
    if startpage == volumes[c[ENTRY_VOL_NUM_INDEX]-1][VOL_LAST_PAPER_INDEX]:
    
        metadatafile.write(str(full))

    if createimportfiles:
        dir = 'import/' + id
        try:
            os.mkdir(dir)
        except:
            pass
        xmlf = open(dir + '/dublin_core.xml', 'w')
        xmlf.write(full)
        open(dir + '/contents', 'w').write(id + '.pdf')
        shutil.copyfile('pdfs/'+ id + '.pdf', dir+'/'+id+'.pdf')

if createimportfiles:
    print("Created import files")

if printfullmetadata:
    print("Created fullmetadata.txt")
    metadatafile.close()
