"""Lightweight offline fallbacks used when NLTK (or its data) is unavailable.

They approximate NLTK's English stopword list, Porter stemmer and WordNet
(noun) lemmatizer closely enough for the pipeline to run anywhere. When NLTK
is installed, the real implementations are used automatically.
"""

FALLBACK_STOPWORDS = frozenset("""
i me my myself we our ours ourselves you you're you've you'll you'd your yours yourself
yourselves he him his himself she she's her hers herself it it's its itself they them their
theirs themselves what which who whom this that that'll these those am is are was were be
been being have has had having do does did doing a an the and but if or because as until
while of at by for with about against between into through during before after above below
to from up down in out on off over under again further then once here there when where why
how all any both each few more most other some such no nor not only own same so than too very
s t can will just don don't should should've now d ll m o re ve y ain aren aren't couldn
couldn't didn didn't doesn doesn't hadn hadn't hasn hasn't haven haven't isn isn't ma
mightn mightn't mustn mustn't needn needn't shan shan't shouldn shouldn't wasn wasn't
weren weren't won won't wouldn wouldn't
""".split())

_VOWELS = set("aeiou")


def _has_vowel(s):
    return any(c in _VOWELS for c in s) or "y" in s[1:]


class SimpleStemmer:
    """Small suffix-stripping stemmer (Porter-style, simplified)."""

    _STEP2 = (("ational", "ate"), ("tional", "tion"), ("ization", "ize"),
              ("izer", "ize"), ("fulness", "ful"), ("ousness", "ous"),
              ("iveness", "ive"), ("biliti", "ble"), ("alism", "al"),
              ("aliti", "al"), ("iviti", "ive"))
    _STEP3 = ("ement", "ment", "ness", "ful", "able", "ible", "ance", "ence",
              "ant", "ent", "ive", "ous", "ism", "ity", "ize", "ate", "al",
              "er", "ic", "ly")

    def stem(self, word):
        w = word.lower()
        if len(w) <= 3:
            return w
        # step 1a: plurals
        if w.endswith("sses"):
            w = w[:-2]
        elif w.endswith("ies"):
            w = w[:-2]
        elif w.endswith("ss"):
            pass
        elif w.endswith("s"):
            w = w[:-1]
        # step 1b: -ed / -ing
        if w.endswith("eed"):
            if len(w) > 4:
                w = w[:-1]
        else:
            for suf in ("ed", "ing"):
                if w.endswith(suf) and _has_vowel(w[:-len(suf)]):
                    w = w[:-len(suf)]
                    if w.endswith(("at", "bl", "iz")):
                        w += "e"
                    elif (len(w) > 2 and w[-1] == w[-2]
                          and w[-1] not in _VOWELS and w[-1] not in "lsz"):
                        w = w[:-1]
                    break
        # step 1c: y -> i
        if w.endswith("y") and len(w) > 2 and _has_vowel(w[:-1]):
            w = w[:-1] + "i"
        # step 2 / 3: derivational suffixes
        for suf, rep in self._STEP2:
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                w = w[:-len(suf)] + rep
                break
        for suf in self._STEP3:
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                w = w[:-len(suf)]
                break
        return w


class SimpleLemmatizer:
    """Rule-based noun lemmatizer (mimics WordNetLemmatizer's default pos='n')."""

    _IRREGULAR = {"men": "man", "women": "woman", "children": "child",
                  "feet": "foot", "teeth": "tooth", "mice": "mouse",
                  "geese": "goose"}

    def lemmatize(self, word, pos="n"):
        if word in self._IRREGULAR:
            return self._IRREGULAR[word]
        if len(word) <= 3:
            return word
        if word.endswith("ies") and len(word) > 4:
            return word[:-3] + "y"
        if word.endswith(("sses", "shes", "ches", "xes", "zes")):
            return word[:-2]
        if word.endswith("s") and not word.endswith(("ss", "us", "is")):
            return word[:-1]
        return word
