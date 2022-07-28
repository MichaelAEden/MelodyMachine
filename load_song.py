import logging
from collections import defaultdict

import mido
import numpy as np


MEASURES_PER_SONG = 16
TICKS_PER_MEASURE = 48
TICKS_PER_SONG = TICKS_PER_MEASURE * MEASURES_PER_SONG
NOTE_MIN = 20  # Inclusive
NOTE_MAX = 96  # Not inclusive
NOTE_RANGE = NOTE_MAX - NOTE_MIN

NOTE_VOLUME_PERCENTILE_THRESHOLD = 75  # Only allow notes with volume in top percentile.
DEFAULT_CHANNEL_VOLUME = 127

CHANNEL_PERCUSSION = 9  # 10 by MIDI standard but Mido uses 0-indexing.
CONTROL_VOLUME = 7


def get_note_volume(velocity: int, channel_volume: int) -> float:
    return (velocity / 127) * (channel_volume / 127)


def get_volume_threshold(mid: mido.MidiFile) -> float:
    note_volumes = []
    channel_volumes = defaultdict(lambda: DEFAULT_CHANNEL_VOLUME)
    for track in mid.tracks:
        for msg in track:
            if hasattr(msg, 'channel') and msg.channel == CHANNEL_PERCUSSION:
                continue

            if msg.type == 'control_change' and msg.control == CONTROL_VOLUME:
                channel_volumes[msg.channel] = msg.value

            if msg.type == 'note_on':
                note_volume = get_note_volume(msg.velocity, channel_volumes[msg.channel])
                note_volumes.append(note_volume)

    return np.percentile(note_volumes, NOTE_VOLUME_PERCENTILE_THRESHOLD)


def to_numpy(mid: mido.MidiFile):
    # Adapted from MidiFile.__iter__
    if mid.type == 2:
        raise TypeError('Cannot merge tracks in type 2 (asynchronous) file.')

    playback_ticks = 0
    beats_per_measure = None
    channel_volumes = {}
    data = np.zeros((NOTE_RANGE, TICKS_PER_SONG))

    volume_threshold = get_volume_threshold(mid)

    for msg in mido.merge_tracks(mid.tracks):
        # Only consider time signature, but ignore tempo.
        if msg.type == 'time_signature' and beats_per_measure is None:
            beats_per_measure = msg.numerator
            continue

        if msg.time > 0:
            playback_ticks += msg.time

        if hasattr(msg, 'channel') and msg.channel == CHANNEL_PERCUSSION:
            continue

        if msg.type == 'control_change' and msg.control == CONTROL_VOLUME:
            channel_volumes[msg.channel] = msg.value

        if msg.type == 'note_on':
            if msg.channel not in channel_volumes:
                logging.warning(f'Unknown volume for channel: {msg.channel}, defaulting to {DEFAULT_CHANNEL_VOLUME}.')
                channel_volumes[msg.channel] = DEFAULT_CHANNEL_VOLUME

            note_volume = get_note_volume(msg.velocity, channel_volumes[msg.channel])
            if note_volume < volume_threshold:
                continue

            if beats_per_measure is None:
                logging.warning('Unknown time signature, defaulting to 4/4.')
                beats_per_measure = 4

            ticks_per_measure = mid.ticks_per_beat * beats_per_measure
            time_index = int(playback_ticks * TICKS_PER_MEASURE / ticks_per_measure)
            if time_index >= TICKS_PER_SONG:
                break

            note_index = msg.note
            if note_index < NOTE_MIN:
                logging.warning(f'Ignoring note in lower range: {note_index} < {NOTE_MIN}.')
                continue

            if note_index >= NOTE_MAX:
                logging.warning(f'Ignoring note in upper range: {note_index} >= {NOTE_MAX}.')
                continue

            data[note_index - NOTE_MIN, time_index] = 1

    return data






