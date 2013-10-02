#!/usr/bin/python

import re

class TextUtils:
    def __init__(self):
        self.dict = {}
        dictwords = open("/usr/share/dict/words", "r")
        for word in dictwords:
            word = word.strip()
            self.dict[word] = 1
    
    def remove_hyphens(self, text):
        for hword,lword,rword in re.findall("((\w+)\s*-\s*(\w+))", text):
            joined_word = lword+rword

            if joined_word.lower() in self.dict:
                text = text.replace(hword, joined_word)
            elif (not lword in self.dict) and (not rword in self.dict):
                text = text.replace(hword, joined_word)
    
        return text


if __name__ == "__main__":
    tu = TextUtils()
    print tu.remove_hyphens("For ex- ample, the results indicate that it might be more suitable to use a declarative phrase when resum- ing to a domain where the system is asking the user for information, for example when adding songs to a play list at the mp3-player cf. the in- terview domain ")
