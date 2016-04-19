import time

import music21
import OpenFL.Printer as P

def midi_live(midifilename, quarternote_s=0.5, skip_leading_rests=True):
    """ Given a MIDI file, play it live on the printer
    """
    p = P.Printer()
    if p.state() != P.State.MACHINE_READY_TO_PRINT:
        p.initialize()

    # Use a class as a local namespace to capture variables
    class Position:
        z = 0   # This is our current Z position in microsteps
        direction = -1  # This is the direction of travel (negative = down)

    # Local function that handles note direction and timing
    def play_note(freq, time_s):
        # Turn around if we're about to hit the top or bottom
        steps = freq * time_s
        if not (-80000 <= Position.z + Position.direction * steps <= 0):
            Position.direction *= -1

        # Send a blocking motor move
        p.move_z(Position.direction * freq * time_s, freq, 80)

        # Update the dead-reckoning Z position
        Position.z += Position.direction * steps

    mf = music21.midi.MidiFile()
    mf.open(midifilename)
    mf.read()
    soundstream = music21.midi.translate.midiFileToStream(mf)

    for track in soundstream.elements:
        for i in track.flat.elements:
            # Play a note on the printer (and clear the skip rests flag)
            if isinstance(i, music21.note.Note):
                play_note(i.pitch.frequency,
                          i.duration.quarterLength * quarternote_s)
                skip_leading_rests = False
            # Pause the correct amount of time for a rest
            elif isinstance(i, music21.note.Rest):
                if not skip_leading_rests:
                    time.sleep(i.duration.quarterLength * quarternote_s)
