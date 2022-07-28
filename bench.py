import os
import timeit

import mido
import numpy as np


def bench_midi_loading() -> float:
    """Compute average time to load MIDI file."""
    rng = np.random.default_rng(seed=1845)
    filepaths = [
        os.path.join(root, filename)
        for root, _, filenames in os.walk('res')
        for filename in filenames
    ]

    def load_midi_file():
        filepath = filepaths[rng.integers(0, len(filepaths))]
        mido.MidiFile(filepath)

    return timeit.timeit(load_midi_file, number=10)


if __name__ == '__main__':
    print(bench_midi_loading())
