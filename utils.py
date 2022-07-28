import os
from typing import List

import mido


def get_midi_filepaths() -> List[str]:
    """Return list of filepaths of MIDI files."""
    return [
        os.path.join(root, filename)
        for root, _, filenames in os.walk('res')
        for filename in filenames
    ]


def merge_tracks(mid: mido.MidiFile) -> mido.MidiTrack:
    """
    More efficient implementation of merge_tracks as compared to mido.
    See mido.merge_tracks() for more information.
    """
    messages_abs_time = []
    for track in mid.tracks:
        elapsed = 0
        for msg in track:
            elapsed += msg.time
            messages_abs_time.append((msg, elapsed))

    messages_abs_time.sort(key=lambda msg: msg[1])

    messages_rel_time = []
    elapsed = 0
    for msg, abs_time in messages_abs_time:
        delta = abs_time - elapsed

        # Calling __setattr__ on the copied instance is much faster than passing the attribute to copy.
        msg = msg.copy()
        msg.time = delta

        messages_rel_time.append(msg)
        elapsed = abs_time

    return mido.MidiTrack(mido.midifiles.tracks.fix_end_of_track(messages_rel_time))
