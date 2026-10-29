"""Lossless JSON scalar normalization for preserved development support reports."""
import math
import numpy as np

def plain(value):
    if isinstance(value,np.generic):
        item=value.item()
        if isinstance(item,np.generic):raise TypeError('Unsupported extended NumPy scalar')
        return plain(item)
    if value is None or type(value) in (str,bool,int):return value
    if type(value)is float:
        if not math.isfinite(value):raise ValueError('Nonfinite report scalar')
        return value
    if isinstance(value,dict):
        if any(type(k)is not str for k in value):raise ValueError('Report keys must be strings')
        return {k:plain(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [plain(v) for v in value]
    raise TypeError('Unsupported report value: '+type(value).__name__)
