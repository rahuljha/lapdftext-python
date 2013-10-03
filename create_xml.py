#!/usr/bin/python

import re
import sys
from lapdftext import LapdfText, FontStyle
from lxml import etree
from text_utils import TextUtils


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

text_font_size = lpt.get_mfs()
all_sizes = lpt.get_font_sizes()
heading_size = all_sizes[all_sizes.index(text_font_size)+1]

paper = etree.Element("paper")

curSection = None
mainBodyStarted = False

for c in lpt.chunks:
    chunk_font_size = c.get_mf_attr("font-size")
    chunk_font_style = c.get_mf_attr("font-style")
    chunkText = " ".join([i.text for i in c.words])
    chunkText = TextUtils.fix_wide_letters(TextUtils.remove_hyphens(chunkText))
    
#        print " ".join([i.text for i in c.words])
    if chunk_font_size >= text_font_size and chunk_font_size <= heading_size and chunk_font_style == FontStyle.Bold:
        if not mainBodyStarted and re.match("abstract", chunkText, flags = re.IGNORECASE):
            mainBodyStarted = True
        if not mainBodyStarted: continue
        curSection = etree.SubElement(paper, "section")

        m = re.match("^((?:\d\.)*\d)\s+(.*)$", chunkText)
        if m:
            curSection.attrib["number"] = m.group(1)
            chunkText = m.group(2)

        curSection.attrib["name"] = chunkText
        curSection.text = ""
#        print "Heading: "+" ".join([i.text for i in c.words])
    elif chunk_font_size == text_font_size:
        if curSection is not None:
            curSection.text += chunkText
    elif (chunk_font_size < text_font_size and curSection is not None 
          and re.match("references", curSection.attrib["name"], flags = re.IGNORECASE)):
        curSection.text += chunkText
    else:
        pass

print etree.tostring(paper)
