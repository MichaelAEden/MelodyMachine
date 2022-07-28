import os
from typing import List


def get_midi_filepaths() -> List[str]:
    """Return list of filepaths of MIDI files."""
    return [
        os.path.join(root, filename)
        for root, _, filenames in os.walk('res')
        for filename in filenames
    ]

