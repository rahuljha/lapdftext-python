#!/usr/bin/python

import re
from subprocess import Popen, PIPE

class TextUtils:
    dictwords = {}
    dictlines = open("/usr/share/dict/words", "r")
    for word in dictlines:
        word = word.strip()
        dictwords[word] = 1

    @classmethod
    def remove_hyphens(cls, text):
        for hword,lword,rword in re.findall("((\w+)\s*-\s*(\w+))", text):
            joined_word = lword+rword

            if joined_word.lower() in cls.dictwords:
                text = text.replace(hword, joined_word)
            elif (not lword in cls.dictwords) and (not rword in cls.dictwords):
                text = text.replace(hword, joined_word)
    
        return text

    @classmethod
    def fix_wide_letters(cls, text):
        for charstring in re.findall("((?:.\ )(?:.|$){5,})", text):
            charstring = charstring.replace(" ", "")
            cands = cls.segment_word(charstring)
            if len(cands) == 0:
                return text

            candProbs = {}
            for cand in cands:
                candProbs[cand] = float(cls.get_lm_prob(cand).strip())

            bestcand = max(candProbs.iterkeys(), key=(lambda s: candProbs[s]))
            return bestcand

    @classmethod
    def get_lm_prob(cls, text):
        blm_cmd = "java -ea -mx1000m -server -cp /data0/tools/berkeleylm-1.1.2/src/ edu.berkeley.nlp.lm.io.ComputeLogProbabilityOfTextStream /data0/tools/berkeleylm-1.1.2/examples/google.binary"
        args1 = ["echo", '"%s"' % text]
        args2 = blm_cmd.split(" ")
        p1 = Popen(args1, stdout=PIPE)
        p2 = Popen(args2, stdin=p1.stdout, stdout=PIPE)
        return p2.communicate()[0]

    @classmethod
    def segment_word(cls, text):
        cands = []
        for i in range(len(text)):
            cur_word = text[:(i+1)] 
            # this is because range starts from 0 to (len-1), but the index in substring works with 1-index (i.e. "test"[:2] = "te")
            if(cur_word.lower() in cls.dictwords or cur_word.isdigit()):
                if(len(cur_word) == 1 and cur_word.isalpha() and cur_word != "a"): 
                    # all the single alphabets are there in the dict, we should ignore all these except "a"
                    continue
                rest_str = text[(i+1):]
                if rest_str == "":
                    return [cur_word] if len(cands) == 0 else cands + [cur_word]
                rest_words = cls.segment_word(rest_str)
                for cand in rest_words:
                    cands.append(cur_word+" "+cand)

        if len(cands) == 0:
            cands = [""] # if no set of characters in this string form any known words
    
        cands = [i for i in cands if len(i.replace(" ", "")) > 0.9 * len(text)] # we don't want candidates that are too short
        return cands


if __name__ == "__main__":
    print TextUtils.remove_hyphens("For ex- ample, the results indicate that it might be more suitable to use a declarative phrase when resum- ing to a domain where the system is asking the user for information, for example when adding songs to a play list at the mp3-player cf. the in- terview domain ")

    print "Best cand: "+TextUtils.fix_wide_letters("D u s t a n d e a r f r i e n d s")
    print "Best cand: "+TextUtils.fix_wide_letters("1 I n t r o d u c t i o n")
    print "Best cand: "+TextUtils.fix_wide_letters("U N S U P E R V I S E D W O R D S E N S E D I S A M B I G U A T I O N R I V A L I N G S U P E R V I S E D M E T H O D S")
    print "Best cand: "+TextUtils.fix_wide_letters("D a v i d Y a r o w s k y D e p a r t m e n t of C o m p u t e r and I n f o r m a t i o n Science University of P e n n s y l v a n i a P h i l a d e l p h i a , PA 19104, USA")

    
