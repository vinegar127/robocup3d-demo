"""Pinned public runtime identifiers and explicitly selected field profiles."""
from pathlib import Path
PUBLIC_KINDS = ('apollo', 'bahia', 'my3d', 'aspen', 'retricato', 'jenny', 'freeloap', 'gru2')
PYTHON_FIELDS = {'bahia': 'fifa', 'aspen': 'fifa', 'jenny': 'custom', 'freeloap': '7v7'}
GRU_KINDS = ('retricato', 'gru2')


def native_assets(root, kind, runtime):
    """Use each native opponent's own assets after an out-of-tree Linux build."""
    if kind not in ('apollo', 'my3d'):
        raise ValueError('Unknown native opponent')
    bundled = Path(runtime)/'assets'
    if bundled.is_dir():
        return bundled
    source = Path(root)/('third_party/my3d/runtime/apollo/assets' if kind == 'my3d'
                         else 'third_party/apollo/assets')
    if not source.is_dir():
        raise FileNotFoundError(f'Missing {kind} assets: {source}')
    return source


def configuration(kind):
    if kind == 'jenny':
        return 'upstream --field custom (55 x 36 m), original tactics, models and 1-7 formation'
    if kind == 'freeloap':
        return 'upstream --field 7v7 (55 x 36 m), original tactics, models and 1-7 formation'
    if kind == 'bahia':
        return 'upstream default fifa (105 x 68 m internal geometry)'
    return 'upstream default'
