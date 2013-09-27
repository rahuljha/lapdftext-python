#!/usr/bin/python

from __future__ import division
from collections import Counter

import os
import sys
import re
from subprocess import call
from lxml import etree

from lapdfExceptions import *

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
FontStyle = enum(Regular = 1, Italics = 1, Bold = 1)

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
    def __init__(self, pageNum, w, h, pageLoc):
        self.pageNum = pageNum
        self.width = w
        self.height = h
        self.pageLoc = pageLoc
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
            mfAttr = max(counts.iteritems(), key=(lambda w: counts[w]))[0]
            self.mfAttrs[attr] = mfAttr
            return mfAttr

    def __repr__(self):
        size = self.get_mf_attr("font-size")
        style = self.get_mf_attr("font-style")
        
        return " ".join([i.text for i in self.words]) + " ("+str(size)+","+str(style)+")"
            

class LapdfText:

    def __init__(self, blockfilepath):
        """constructor to initialize an instance from the blocks XML produced by the blockify 
        utility of lapdftext"""

        self.numPages = 0
        self.mostFreqFontSize = 0
        self.chunks = []

        if not os.path.exists(blockfilepath):
            raise FileNotFoundError("Blockify file not found: "+blockfilepath) 
        infile = open(blockfilepath, "r")
        tree = etree.parse(infile)
        root = tree.getroot()

        curPage = 0
        curPageWidth = 0
        curPageHeight = 0
        curChunk = None
        for element in root.iter("Page", "Chunk", "Word"):
            if element.tag == "Page":
                self.numPages += 1
                curPage = element.get("pageNumber")
                curPageWidth = int(element.get("x2")) - int(element.get("x1"))
                curPageHeight = int(element.get("y2")) - int(element.get("y1"))

            elif element.tag == "Chunk":
                width = int(element.get("x2")) - int(element.get("x1"))
                height = int(element.get("y2")) - int(element.get("y1"))
                self.chunks.append(curChunk)
                curChunk = Chunk(curPage, width, height, self.get_block(width, height, curPageWidth, curPageHeight))

            elif element.tag == "Word":
                styleStr = element.get("style")
                styleMap = {}

                try:
                    for pair in styleStr.split(";"):
                        (name, val) = pair.split(":")
                        if name == "font-size":
                            val = val.replace("pt", "")
                        styleMap[name] = val
                    # if font-style is not explicity present, it is sometimes implicit in the font name
                    if("font-style" not in styleMap):
                        fontName = element.get("font")
                        if(re.search("bold", fontName, re.IGNORECASE) or re.search("medi", fontName, re.IGNORECASE)):
                            styleMap["font-style"] = "Bold"
                        elif(re.search("ital", fontName, re.IGNORECASE)):
                            styleMap["font-style"] = "Bold"
                except:
                    styleMap = {}
                        
                curChunk.add_word(Word(element.text.encode('ascii', 'ignore'), styleMap))

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
        
    def get_block(self, w, h, w2, h2):
        return 1

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
    for c in lpt.chunks:
        print c
