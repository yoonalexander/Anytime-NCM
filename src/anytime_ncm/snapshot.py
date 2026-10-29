"""Read the packaged, aggregate-only research snapshot without ML dependencies."""
from importlib.resources import files
import json
from . import __version__

def load_snapshot():
    value=json.loads(files('anytime_ncm').joinpath('snapshot.json').read_text(encoding='utf-8'))
    if value['schema_version']!=1 or value['snapshot_version']!=__version__:
        raise ValueError('Installed research snapshot/version mismatch')
    return value
