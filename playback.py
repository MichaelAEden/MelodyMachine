import time

import mido
import pygame

pygame.init()


def play_pygame(path: str):
    pygame.mixer.music.load(path)
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        pygame.time.wait(1000)


def play_mido(path: str):
    with mido.open_output(autoreset=True) as port:
        mid = mido.MidiFile(path)

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

