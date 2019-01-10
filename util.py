#!/usr/bin/env python3
'''
util.py
sentivent-webannoparser
10/10/18
Copyright (c) Gilles Jacobs. All rights reserved.  
'''
from collections import abc, defaultdict

def dict_zip(*dicts, fillvalue=None):
    all_keys = {k for d in dicts for k in d.keys()}
    return {k: [d.get(k, fillvalue) for d in dicts] for k in all_keys}

def list_duplicates(seq):
    tally = defaultdict(list)
    for i, item in enumerate(seq):
        tally[item].append(i)
    return ((key,locs) for key,locs in tally.items()
                            if len(locs)>1)

def flatten(l):
    return [item for sublist in l for item in sublist]

def count_avg(iterable_obj, attr, return_counts=False):
    try:
        if not isinstance(iterable_obj, abc.Iterable): raise TypeError
        cnt = 0
        for x in iterable_obj:
            attrib_val = getattr(x, attr)
            if attrib_val: # only add to count if attribute value is not None and empty list
                cnt += len(attrib_val)
        avg = cnt / float(len(iterable_obj))
        if return_counts:
            return avg, cnt
        else:
            return avg
    except TypeError as te:
        print(f"{iterable_obj} is not an iterable. {str(te)}")
