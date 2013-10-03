#!/usr/bin/python

from __future__ import division
from collections import Counter
from sets import Set

import os
import sys
import re
from subprocess import call
from lxml import etree

from lapdfExceptions import *
from text_utils import TextUtils

## Defining Enums ##

def enum(**enums):
    return type('Enum', (), enums)

# Enum to specify the location of a chunk in one of the six blocks
# defined on the page:

# |------------+-------------|
# | TopLeft    | TopRight    |
# |------------+-------------|
# | MiddleLeft | MiddleRight |
# |------------+-------------|
# | BottomLeft | BottomRight |
# |------------+-------------|

PageLoc = enum(TopLeft = 1, TopRight = 2, MiddleLeft = 3, MiddleRight = 4, BottomLeft = 5, BottomRight = 6)

#Enum to specifiy font styles
FontStyle = enum(Regular = 1, Italics = 2, Bold = 3)

## Done Defining Enums ##

class Word:
    def __init__(self, text, attrs):
        self.text = text
        self.attrs = attrs

    def __repr__(self):
        return self.text

    def get_attr(self, attr):
        if attr in self.attrs:
            return self.attrs[attr]
        else:
            return None
    
class Chunk:
    def __init__(self, pageNum, w, h, pageBlocks):
        self.pageNum = pageNum
        self.width = w
        self.height = h
        self.pageBlocks = pageBlocks
        self.words = []
        self.mfAttrs = {}
        
    def add_word(self, word):
        self.words.append(word)

    def get_mf_attr(self, attr):
        """returns the most frequent value of attr in this chunk"""
        if attr in self.mfAttrs:
            return self.mfAttrs[attr]
        else:
            # compute
            counts = Counter([w.get_attr(attr) for w in self.words])
            mfAttr = max(counts.iterkeys(), key=(lambda w: counts[w]))
            self.mfAttrs[attr] = mfAttr
            return mfAttr

    def __repr__(self):
        size = self.get_mf_attr("font-size")
        style = self.get_mf_attr("font-style")
        
        return " ".join([i.text for i in self.words]) + " (size:"+str(size)+",style:"+str(style)+",blocks: "+";".join([str(i) for i in self.pageBlocks])+")"
            

class LapdfText:

    def __init__(self, blockfilepath):
        """constructor to initialize an instance from the blocks XML produced by the blockify 
        utility of lapdftext"""

        self.numPages = 0
        self.mostFreqFontSize = None
        self.allFontSizes = None
        self.chunks = []

        if not os.path.exists(blockfilepath):
            raise FileNotFoundError("Blockify file not found: "+blockfilepath) 
        infile = open(blockfilepath, "r")
        tree = etree.parse(infile)
        root = tree.getroot()

        curPage = 0
        curPageOrigin = ()
        curPageTop = ()
        curChunk = None
        for element in root.iter("Page", "Chunk", "Word"):
            if element.tag == "Page":
                self.numPages += 1
                curPage = element.get("pageNumber")
                curPageOrigin = (int(element.get("x1")), int(element.get("y1")))
                curPageTop = (int(element.get("x2")), int(element.get("y2")))

            elif element.tag == "Chunk":
                # a new chunk element has started, create a new chunk
                curChunk = self.create_chunk(element, curPage, curPageOrigin, curPageTop)
                self.chunks.append(curChunk)

            elif element.tag == "Word":         
                curChunk.add_word(self.create_word(element))

    def get_mfs(self):
        """Returns the most frequent font size in this article"""

        if not self.mostFreqFontSize:
            font_sizes = []
            for c in self.chunks:
                for w in c.words:
                    font_sizes.extend([w.get_attr("font-size")])

            counts = Counter(font_sizes)
            self.mostFreqFontSize = int(max(counts.iterkeys(), key=(lambda w: counts[w])))
            self.allFontSizes = sorted([int(i) for i in counts.keys() if i])
        return self.mostFreqFontSize

    def get_font_sizes(self):
        if not self.allFontSizes:
            self.get_mfs()

        return self.allFontSizes
                

    def create_chunk(self, element, curPage, curPageOrigin, curPageTop):
        blockOrigin = (int(element.get("x1")), int(element.get("y1")))
        blockTop = (int(element.get("x2")), int(element.get("y2")))
        return Chunk(curPage, 
                     int(element.get("x2"))-int(element.get("x1")), # width
                     int(element.get("y2"))-int(element.get("y1")), # height
                     self.get_blocks(blockOrigin, blockTop, curPageOrigin, curPageTop))

    def create_word(self, element):
        styleStr = element.get("style")
        styleMap = {}

        try:
            for pair in styleStr.split(";"):
                (name, val) = pair.split(":")
                if name == "font-size":
                    val = val.replace("pt", "")
                    styleMap[name] = int(val)
                if name == "font-style":
                    if(re.search("italic", val, re.IGNORECASE)):
                        styleMap[name] = FontStyle.Italics
                    elif(re.search("bold", val, re.IGNORECASE)):
                        styleMap[name] = FontStyle.Bold
                    else:
                        styleMap[name] = FontStyle.Regular

            # if font-style is not explicity present, it is sometimes implicit in the font name
            if("font-style" not in styleMap):
                fontName = element.get("font")
                if(re.search("bold", fontName, re.IGNORECASE) or re.search("medi", fontName, re.IGNORECASE)):
                    styleMap["font-style"] = FontStyle.Bold
                elif(re.search("ital", fontName, re.IGNORECASE)):
                    styleMap["font-style"] = FontStyle.Italics
        except:
            styleMap = {}

        return Word(element.text.encode('ascii', 'ignore'), styleMap)
        
    @classmethod
    def from_pdffile(cls, pdffilepath):
        """constructor to initialize an instance from a PDF file"""

        outdirpath = "/tmp"
        if not os.path.exists(pdffilepath):
            raise FileNotFoundError("PDF file not found: "+pdffilepath)

        call(["blockify", pdffilepath, outdirpath])
        pdffilename = os.path.basename(pdffilepath)
        outfilename = pdffilename.replace(".pdf", "_spatial.xml")
        outfilepath = outdirpath+"/"+outfilename
        if not os.path.exists(outfilepath):
            raise FileNotFoundError("Blockify output file not found: "+outfilepath)

        return cls(outfilepath)
        
    def get_blocks(self, blockOrigin, blockTop, pageOrigin, pageTop):

        blocks = Set([])

        pageHeight = pageTop[1] - pageOrigin[1]
        pageWidth = pageTop[0] - pageOrigin[0]

        # these are the points to be checked
        points = (blockOrigin, (blockOrigin[0], blockTop[1]), blockTop, (blockTop[0], blockOrigin[1]))
        
        # these are the ranges they can be in
        yranges = {0: (pageOrigin[1], pageOrigin[1]+pageHeight/3), 
                   1: (pageOrigin[1]+pageHeight/3, pageOrigin[1]+pageHeight*2/3),
                   2: (pageOrigin[1]+pageHeight*2/3, pageOrigin[1]+pageHeight)};
        xranges = {0: (pageOrigin[0], pageOrigin[0]+pageWidth/2),
                   1: (pageOrigin[0]+pageWidth/2, pageTop[0])}

        # simple hash to quicken the mapping

        blockHash = {"00": PageLoc.TopLeft, "01": PageLoc.MiddleLeft, "02": PageLoc.BottomLeft,
                     "10": PageLoc.TopRight, "11": PageLoc.MiddleRight, "12": PageLoc.BottomRight}

        for p in points:
            blockx = blocky = 0 # the valid values are (0,0), (0,1), (0,2), (1,0), (1,1), (1,2)
            for bx, xr in xranges.iteritems():
                if p[0] >= xr[0] and p[0] < xr[1]:
                    blockx = bx
                    break

            for by, yr in yranges.iteritems():
                if p[1] >= yr[0] and p[1] < yr[1]:
                    blocky = by
                    break

            blocks.add(blockHash[str(bx)+str(by)])

        return blocks

if(__name__ == "__main__"):
    if(len(sys.argv) < 2):
        print "Usage: lapdftext.py <file_loc> <file_type: pdf|xml>"
        sys.exit(1)

    f_loc = sys.argv[1]
    f_type = sys.argv[2]

    if f_type == "pdf":
        lpt = LapdfText.from_pdffile(f_loc)
    elif f_type == "xml":
        lpt = LapdfText(f_loc)
    else:
        print "Unknown file type: "+f_type
        sys.exit(1)

    print "MF font size: "+str(lpt.get_mfs())
    print "All sizes: "+";".join([str(s) for s in lpt.get_font_sizes()])
    for c in lpt.chunks:
        print c

