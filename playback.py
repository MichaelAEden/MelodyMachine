import time

import mido


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
