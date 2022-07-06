import logging
import time

import mido
import numpy as np


_MEASURES_PER_SONG = 16
_TICKS_PER_MEASURE = 96
_TICKS_PER_SONG = _TICKS_PER_MEASURE * _MEASURES_PER_SONG
_NOTE_SCALE = 96

_TICKS_PER_SECOND = 60

_CHANNEL_PERCUSSION = 9  # 10 by MIDI standard but Mido uses 0-indexing.


def to_numpy(path: str):
    mid = mido.MidiFile(path)

    # Adapted from MidiFile.__iter__
    if mid.type == 2:
        raise TypeError('Cannot merge tracks in type 2 (asynchronous) file.')

    playback_ticks = 0
    beats_per_measure = None
    time_signature_received = False
    data = np.zeros((_NOTE_SCALE, _TICKS_PER_SONG))

    for msg in mido.merge_tracks(mid.tracks):
        # Only consider time signature, but ignore tempo.
        if msg.type == 'time_signature':
            if time_signature_received:
                logging.warning('Multiple Time Signature messages received.')
            elif beats_per_measure is None:
                beats_per_measure = msg.numerator
            time_signature_received = True
            continue

        if msg.time > 0:
            playback_ticks += msg.time

        if hasattr(msg, 'channel') and msg.channel == _CHANNEL_PERCUSSION:
            continue

        if msg.type == 'note_on':
            if beats_per_measure is None:
                logging.warning('Unknown time signature, defaulting to 4/4 time.')
                beats_per_measure = 4

            ticks_per_measure = mid.ticks_per_beat * beats_per_measure
            time_index = int(playback_ticks * _TICKS_PER_MEASURE / ticks_per_measure)
            if time_index >= _TICKS_PER_SONG:
                break

            note_index = msg.note
            if note_index >= _NOTE_SCALE:
                logging.warning('Ignoring note outside accepted range.')
                continue

            data[note_index, time_index] = 1

    return data


def play_numpy(data: np.ndarray):
    # TODO: send Note Off messages.
    with mido.open_output(autoreset=True) as port:
        notes = np.transpose(np.nonzero(data.T))
        start_time = time.time()

        for time_index, note_index in notes:
            playback_time = time.time() - start_time
            sleep_time = (time_index / _TICKS_PER_SECOND) - playback_time
            if sleep_time > 0:
                time.sleep(sleep_time)

            msg = mido.Message('note_on', note=note_index)
            port.send(msg)

