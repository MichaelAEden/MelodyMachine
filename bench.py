import asyncio
import cProfile
import io
import time
import timeit
from pstats import SortKey
from typing import Callable, List

import mido
import numpy as np

import utils


def load_midi_files(number: int) -> List[mido.MidiFile]:
    rng = np.random.default_rng(seed=1845)
    filepaths = utils.get_midi_filepaths()

    midi_files = []
    while len(midi_files) < number:
        filepath = filepaths[rng.integers(0, len(filepaths))]
        try:
            mid = mido.MidiFile(filepath)
            midi_files.append(mid)
        except Exception as e:
            print(f'Error reading MIDI file: {e}')

    return midi_files


def load_midi_file_fn() -> Callable:
    """Return function which loads a random MIDI file."""
    rng = np.random.default_rng(seed=1845)
    filepaths = utils.get_midi_filepaths()

    def load_midi_file():
        try:
            mido.MidiFile(filepaths[rng.integers(0, len(filepaths))])
        except Exception as e:
            print(f'Error reading MIDI file: {e}')

    return load_midi_file


def load_midi_file_fn_async():
    rng = np.random.default_rng(seed=1845)
    filepaths = utils.get_midi_filepaths()

    async def load_midi_file():
        try:
            mido.MidiFile(filepaths[rng.integers(0, len(filepaths))])
        except Exception as e:
            print(f'Error reading MIDI file: {e}')

    return load_midi_file


def merge_tracks_fn(number: int) -> Callable:
    """Return function which calls merge_tracks for a random MIDI file."""
    midi_files = load_midi_files(number)

    def merge_tracks():
        mid = midi_files[-1]
        mido.merge_tracks(mid.tracks)
        midi_files.pop()

    return merge_tracks


def custom_merge_tracks_fn(number: int) -> Callable:
    """Return function which calls the custom implementation of merge_tracks for a random MIDI file."""
    midi_files = load_midi_files(number)

    def merge_tracks():
        mid = midi_files[-1]
        utils.merge_tracks(mid)
        midi_files.pop()

    return merge_tracks


def bench(fn: Callable, number: int, repeat: int):
    """Time the given function."""
    times = timeit.repeat(fn, repeat=repeat, number=number)
    print(f'Average time:       {np.mean(times) / number}')
    print(f'Best average time:  {np.min(times) / number}')
    print(f'Worst average time: {np.max(times) / number}')


def bench_async(fn, number: int):
    """Time the given async function."""
    async def run():
        await asyncio.gather(*[fn() for _ in range(number)])

    start = time.perf_counter()
    asyncio.run(run())
    elapsed = time.perf_counter() - start

    print(f'Total time:   {elapsed}')
    print(f'Average time: {elapsed / number}')


def profile(fn, number: int):
    """Profile the given function."""
    global_env = {'fn': fn, 'number': number}
    cProfile.runctx(
        '[fn() for _ in range(number)]',
        globals=global_env,
        locals=global_env,
        sort=SortKey.CUMULATIVE
    )
