import time

import mido
import numpy as np

from load_song import NOTE_MIN, TICKS_PER_MEASURE

_SECONDS_PER_MEASURE = 5 / 3
_TICKS_PER_SECOND = TICKS_PER_MEASURE / _SECONDS_PER_MEASURE


def play_midi(mid: mido.MidiFile):
    """Custom implementation of mido.MidiFile.play() which resolves timing issues."""
    with mido.open_output(autoreset=True) as port:
        # TODO: submit PR to fix MidiFile.play().
        start_time = None
        input_time = 0.0

        for msg in mid:
            if start_time is None:
                start_time = time.time()

            input_time += msg.time

            playback_time = time.time() - start_time
            duration_to_next_event = input_time - playback_time

            if duration_to_next_event > 0.0:
                time.sleep(duration_to_next_event)

            if not isinstance(msg, mido.MetaMessage):
                port.send(msg)


def play_numpy(data: np.ndarray):
    # TODO: send Note Off messages.
    with mido.open_output(autoreset=True) as port:
        msg = mido.Message('program_change', program=0)
        port.send(msg)

        notes = np.transpose(np.nonzero(data.T))
        start_time = time.time()

        for time_index, note_index in notes:
            playback_time = time.time() - start_time
            sleep_time = (time_index / _TICKS_PER_SECOND) - playback_time

            if sleep_time > 0:
                time.sleep(sleep_time)

            msg = mido.Message('note_on', note=note_index + NOTE_MIN)
            port.send(msg)
