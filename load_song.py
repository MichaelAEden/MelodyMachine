import logging

import mido
import numpy as np
from tqdm import tqdm

import utils

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


def to_pianoroll(mid: mido.MidiFile) -> np.ndarray:
    # Adapted from MidiFile.__iter__
    if mid.type == 2:
        raise TypeError('Cannot merge tracks in type 2 (asynchronous) file.')

    playback_ticks = 0
    beats_per_measure = None
    channel_volumes = {}

    # Dimensions are pitch, time, and channel respectively.
    pianoroll = np.zeros((NOTE_RANGE, TICKS_PER_SONG, 16))

    for msg in utils.merge_tracks(mid):
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

            note_volume = (msg.velocity / 127) * (channel_volumes[msg.channel] / 127)
            pianoroll[note_index - NOTE_MIN, time_index, msg.channel] = note_volume

    # Flatten by summing note volumes over channels.
    pianoroll = np.sum(pianoroll, axis=2)

    # Round up loudest notes to 1, round down all other notes to 0.
    pianoroll[pianoroll == 0] = np.nan
    volume_threshold = np.nanpercentile(pianoroll, NOTE_VOLUME_PERCENTILE_THRESHOLD)
    pianoroll = (pianoroll >= volume_threshold).astype(np.int32)

    return pianoroll


def prepare_training_data() -> np.ndarray:
    # TODO: use sparse matrices instead?
    filepaths = utils.get_midi_filepaths()

    data = []
    for filepath in tqdm(filepaths):
        try:
            mid = mido.MidiFile(filepath)
            data.append(to_pianoroll(mid))
        except Exception as e:
            logging.error(f'Error occurred converting: {filepath}, {e}')

    data = np.dstack(data)
    return data


