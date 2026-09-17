"""Offline Chinese line breaking; never rewrite the transcript's characters."""
from functools import lru_cache
import logging

@lru_cache(maxsize=1)
def tokenizer():
    import jieba
    jieba.setLogLevel(logging.WARNING)
    return jieba.Tokenizer()

def chinese_lines(text, width=16):
    if not text:return []
    tokens=[]
    # Keep words, Latin identifiers and numbers intact where they fit a line.
    for token in tokenizer().cut(text,HMM=False):
        tokens.extend(token[i:i+width] for i in range(0,len(token),width))
    closing=set('，。！？；：、）》】」』”’,.!?;:%％')
    opening=set('（《【「『“‘(')
    n=len(tokens)
    # Dynamic programming avoids greedy one-character final lines. Punctuation
    # boundaries are preferred, but length and word integrity remain primary.
    best=[None]*(n+1);best[n]=(0,[])
    for i in range(n-1,-1,-1):
        chunk='';options=[]
        for j in range(i,n):
            chunk+=tokens[j]
            if len(chunk)>width:break
            if best[j+1] is None:continue
            boundary=0
            if j+1<n and tokens[j+1][0] in closing:boundary+=500
            if chunk[-1] in opening:boundary+=500
            if chunk[-1] in '，。！？；：、,.!?;:':boundary-=15
            cost=(width-len(chunk))**2+boundary+best[j+1][0]
            if len(chunk.strip())<3 and n>1:cost+=100
            options.append((cost,[chunk]+best[j+1][1]))
        if options:best[i]=min(options,key=lambda entry:entry[0])
    return best[0][1] if best[0] else [text]
