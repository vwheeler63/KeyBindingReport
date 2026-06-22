debugging = False
if debugging:
    print(f'{__name__}  >>> module execution....')

from . import debug          # noqa: E402
from . import rst_utils      # noqa: E402
from . import output_view    # noqa: E402
from . import ascii_table    # noqa: E402

__all__ = [
    'debug',
    'rst_utils',
    'output_view',
    'ascii_table',
]

if debugging:
    print(f'{__name__}  <<<')
