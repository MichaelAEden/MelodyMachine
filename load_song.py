import logging
import time
from collections import defaultdict

import mido
import numpy as np


_MEASURES_PER_SONG = 16
_TICKS_PER_MEASURE = 96
_TICKS_PER_SONG = _TICKS_PER_MEASURE * _MEASURES_PER_SONG
_NOTE_SCALE = 96

_NOTE_VOLUME_PERCENTILE_THRESHOLD = 75  # Only allow notes with volume in top percentile.
_DEFAULT_CHANNEL_VOLUME = 127

_TICKS_PER_SECOND = 60

_CHANNEL_PERCUSSION = 9  # 10 by MIDI standard but Mido uses 0-indexing.
_CONTROL_VOLUME = 7


def get_note_volume(velocity: int, channel_volume: int) -> float:
    return (velocity / 127) * (channel_volume / 127)


def get_volume_threshold(mid: mido.MidiFile) -> float:
    note_volumes = []
    channel_volumes = defaultdict(lambda: _DEFAULT_CHANNEL_VOLUME)
    for track in mid.tracks:
        for msg in track:
            if hasattr(msg, 'channel') and msg.channel == _CHANNEL_PERCUSSION:
                continue

            if msg.type == 'control_change' and msg.control == _CONTROL_VOLUME:
                channel_volumes[msg.channel] = msg.value

            if msg.type == 'note_on':
                note_volume = get_note_volume(msg.velocity, channel_volumes[msg.channel])
                note_volumes.append(note_volume)

    return np.percentile(note_volumes, _NOTE_VOLUME_PERCENTILE_THRESHOLD)


def to_numpy(path: str):
    mid = mido.MidiFile(path)

    # Adapted from MidiFile.__iter__
    if mid.type == 2:
        raise TypeError('Cannot merge tracks in type 2 (asynchronous) file.')

    playback_ticks = 0
    beats_per_measure = None
    channel_volumes = {}
    data = np.zeros((_NOTE_SCALE, _TICKS_PER_SONG))

    volume_threshold = get_volume_threshold(mid)

    for msg in mido.merge_tracks(mid.tracks):
        # Only consider time signature, but ignore tempo.
        if msg.type == 'time_signature' and beats_per_measure is None:
            beats_per_measure = msg.numerator
            continue

        if msg.time > 0:
            playback_ticks += msg.time

        if hasattr(msg, 'channel') and msg.channel == _CHANNEL_PERCUSSION:
            continue

        if msg.type == 'control_change' and msg.control == _CONTROL_VOLUME:
            channel_volumes[msg.channel] = msg.value

        if msg.type == 'note_on':
            if msg.channel not in channel_volumes:
                logging.warning(f'Unknown volume for channel: {msg.channel}, defaulting to {_DEFAULT_CHANNEL_VOLUME}.')
                channel_volumes[msg.channel] = _DEFAULT_CHANNEL_VOLUME

            note_volume = get_note_volume(msg.velocity, channel_volumes[msg.channel])
            if note_volume < volume_threshold:
                continue

            if beats_per_measure is None:
                logging.warning('Unknown time signature, defaulting to 4/4.')
                beats_per_measure = 4

            ticks_per_measure = mid.ticks_per_beat * beats_per_measure
            time_index = int(playback_ticks * _TICKS_PER_MEASURE / ticks_per_measure)
            if time_index >= _TICKS_PER_SONG:
                break

            note_index = msg.note
            if note_index >= _NOTE_SCALE:
                logging.warning(f'Ignoring note: {note_index} >= {_NOTE_SCALE}.')
                continue

            data[note_index, time_index] = 1

    return data


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

            msg = mido.Message('note_on', note=note_index)
            port.send(msg)

