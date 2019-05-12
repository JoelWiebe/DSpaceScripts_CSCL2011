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

#UPDATE VALUES

#filename of volume pdfs
volumeonefilename = 'ICLS 2014 Volume 1 (PDF)-wCover.pdf'
volumetwofilename = 'ICLS 2014 Volume 2 (PDF)-wCover.pdf'
volumethreefilename = 'ICLS 2014 Volume 3 (PDF)-wCover.pdf'

#volume names
volumeonename = 'Volume 1'
volumetwoname = 'Volume 2'
volumethreename = 'Volume 3'

#list of paper types and their starting pages
papertypeandstart = [("Papers", 21),("Report and Reflection Papers", 935),("Symposia",1177),("Poster",1479),("Workshops",1675),("Research-Practice Partnership Workshop for Doctoral and Early Career Researchers",1712),("Early Career Workshop",1728),("Doctoral Consortium",1747)]

#first page of first paper in the volume
volumeonestart = 23
volumetwostart = 625
volumethreestart = 1179

#pdf page number minus written page number
volumeonepageoffset = 40
volumetwopageoffset = -582
volumethreepageoffset = -1136

#first page of last paper of last volume
startoflastpaper = 1763

#page after last page of last paper of last volume
endofdoc = 1764 

splitPDFs = True
printfullmetadata = True
createimportfiles = True

#the registrant created suffix used prior to the id; conference + year (e.g. cscl2014)
doisuffix = "icls2014"

#conference year
conferenceyear = 2014

#list of editors for citation; get this from the proceedings citation recommendation
editors = "Polman, J. L., Kyza, E. A., O'Neill, D. K., Tabak, I., Penuel, W. R., Jurow, A. S., O'Connor, K., Lee, T., and D'Amico, L."

#publisher location used for citation
conferencelocation = "Boulder, CO"

#date that the conference took place in the format yyyy-mm
issued = "2014-06"

#title of conference with conference acronym and year
conferencetitle = "Learning and Becoming in Practice: The International Conference of the Learning Sciences (ICLS) 2014"

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
      <dcvalue element="identifier" qualifier="citation" language="en_US">$authorscit&#x20;($conferenceyear).&#x20;$title.&#x20;In&#x20;$editors&#x20;(Eds.),&#x20;$conferencetitle,&#x20;$volume&#x20;(pp.&#x20;$pages).&#x20;$conferencelocation:&#x20;International&#x20;Society&#x20;of&#x20;the&#x20;Learning&#x20;Sciences.</dcvalue>
      <dcvalue element="identifier" qualifier="uri">https://doi.dx.org&#x2F;10.22318&#x2F;$doisuffix.$id</dcvalue>
      <dcvalue element="description" qualifier="abstract" language="en_US">$abstract</dcvalue>
      <dcvalue element="language" qualifier="iso" language="en_US">en</dcvalue>
      <dcvalue element="publisher" qualifier="none" language="en_US">$conferencelocation:&#x20;International&#x20;Society&#x20;of&#x20;the&#x20;Learning&#x20;Sciences</dcvalue>
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
    if int(page) >= volumeonestart and int(page) < volumetwostart:
        volume = volumeonename
    elif int(page) >= volumetwostart and int(page) < volumethreestart:
        volume = volumetwoname
    elif int(page) >= volumethreestart and int(page) < endofdoc:
        volume = volumethreename
    else:
        raise ValueError("Page number is outside of the provided range", int(page), volumeonestart, endofdoc)

    papertype = None
    for currpapertype, currpaperstart in papertypeandstart:
        if int(page) >= currpaperstart:
            papertype = currpapertype

    if papertype == None:
        raise valueError ("No paper type was assigned", int(page), title, authors) 

    cs.append([int(page),title,authors, volume, papertype])

metadatafile = open("rawmetadata.txt","w+")
metadatafile.write(str(cs))
print("Created rawmetadata.txt")
metadatafile.close()

if printfullmetadata:
    metadatafile = open("fullmetadata.txt","w+")
for idx, c in enumerate(cs):
    startpage = c[0]
    if startpage == startoflastpaper:
        endpage = endofdoc
    else:
        endpage = cs[idx+1][0]

        #Update endpage if there is a section header between papers
        for currpapertype, currpaperstart in papertypeandstart:
            if startpage < currpaperstart and currpaperstart < endpage:
                endpage = currpaperstart

    if splitPDFs:
        print("Splitting PDF: page " + str(startpage) + " - " + str(endpage-1) + " from " + str(c[3]))
        if c[3] == 'Volume 1':
            fin = subprocess.run(['/bin/bash', './split.sh', volumeonefilename, str(startpage+volumeonepageoffset), str(endpage+volumeonepageoffset-1),'pdfs/' + str(startpage) + '-' + str(endpage-1) + '.pdf'])
     
        if c[3] == 'Volume 2':
            fin = subprocess.run(['/bin/bash', './split.sh', volumetwofilename, str(startpage+volumetwopageoffset), str(endpage+volumetwopageoffset-1),'pdfs/' + str(startpage) + '-' + str(endpage-1) + '.pdf'])
           
        if c[3] == 'Volume 3':
             fin = subprocess.run(['/bin/bash', './split.sh', volumethreefilename, str(startpage+volumethreepageoffset), str(endpage+volumethreepageoffset-1),'pdfs/' + str(startpage) + '-' + str(endpage-1) + '.pdf'])

        fin = subprocess.run(['pdftotext', '-simple', 'pdfs/'+ str(startpage)+'-'+ str(endpage-1)+'.pdf'])

    if printfullmetadata:

        ff = open('pdfs/'+ str(startpage)+"-"+ str(endpage-1)+'.txt', 'rb').read().decode('utf8', 'ignore').strip().replace('\n','ZZZZ')

        match = re.match(r".*Abstract[:.](.+?)ZZZZZZZZ", ff, re.MULTILINE)

        if match:
            abstract = escape(' '.join(match.groups(1)[0].replace('ZZZZ', ' ').split()))
        else:
            abstract = ''

        names = c[2].split(',')
        authorscit = makeAuthorsCit(names)
        authors = makeAuthors(names)
        id = str(startpage)+'-'+str(endpage-1)
        full = item.substitute(authors=authors, authorscit=authorscit, title=escape(c[1]), datetime=genDatetime(),id=str(startpage), abstract=escape(abstract), volume=escape(c[3]), type=escape(c[4]), pages=str(startpage)+'-'+str(endpage-1), doisuffix=doisuffix, conferenceyear=conferenceyear, editors=editors, conferencelocation=conferencelocation, issued=issued, conferencetitle=conferencetitle)
    
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
