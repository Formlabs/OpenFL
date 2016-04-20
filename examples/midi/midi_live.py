#!/usr/bin/env python
import time

import music21
import sys
import os
sys.path.append(os.path.abspath('../OpenFL'))
from OpenFL import Printer as P

def midi_live(midifilename, 
              quarternote_s=0.5, 
              frequency_factor=1.0,
              skip_leading_rests=True):
    """ Given a MIDI file, play it live on the printer
    """
    p = P.Printer()
    if p.state() != P.State.MACHINE_READY_TO_PRINT:
        p.initialize()
    else:
        # We still want to ensure we start in a known state, with z at the limit:
        import OpenFL.FLP as FLP
        # Move z up by more than the z height at 15 mm/s.
        p.move_z(FLP.ZMove.usteps_up_per_mm * 200.0, 
                 feedrate=FLP.ZMove.usteps_up_per_mm * 15.0)

    # Use a class as a local namespace to capture variables
    p.move_z(FLP.ZMove.usteps_up_per_mm * -10.0, 
             feedrate=FLP.ZMove.usteps_up_per_mm * 15.0)
    class Position:
        zbounds_mm = (-10, -150)
        zbounds_ustep = (zbounds_mm[0] * FLP.ZMove.usteps_up_per_mm,
                         zbounds_mm[1] * FLP.ZMove.usteps_up_per_mm)
        # This is our current Z position in microsteps:
        z_ustep = FLP.ZMove.usteps_up_per_mm * -10.0
        direction = -1  # This is the direction of travel (negative = down)
        


    # Local function that handles note direction and timing
    def play_note(freq, time_s):
        # Turn around if we're about to hit the top or bottom
        steps = freq * time_s
        next_z_would_be = Position.z_ustep + Position.direction * freq * time_s
        if Position.direction < 0:
            if next_z_would_be < min(Position.zbounds_ustep):
                Position.direction = 1
        else:
            if next_z_would_be > max(Position.zbounds_ustep):
                Position.direction = -1

        # Send a blocking motor move
        p.move_z(Position.direction * freq * time_s, freq, 80)

        # Update the dead-reckoning Z position
        Position.z_ustep += Position.direction * steps

    mf = music21.midi.MidiFile()
    mf.open(midifilename)
    mf.read()
    soundstream = music21.midi.translate.midiFileToStream(mf)
    print len(soundstream.elements)
    for track in soundstream.elements:
        for i in track.flat.elements:
            # Play a note on the printer (and clear the skip rests flag)
            if isinstance(i, music21.note.Note):
                play_note(i.pitch.frequency * frequency_factor,
                          i.duration.quarterLength * quarternote_s)
                skip_leading_rests = False
            # Pause the correct amount of time for a rest
            elif isinstance(i, music21.note.Rest):
                if not skip_leading_rests:
                    time.sleep(i.duration.quarterLength * quarternote_s)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Play a midi file on your Form 1 or Form 1+.')
    parser.add_argument('midifile', type=str,
                        help='A midi file to play')
    parser.add_argument('--quarternote_s',
                        type=float,
                        default=0.5,
                        help='Duration for a quarternote.')
    parser.add_argument('--frequency_factor', type=float, default=1.0,
                        help='Scale frequency by this factor.')
    args = parser.parse_args()
    midi_live(args.midifile, 
              quarternote_s=args.quarternote_s, 
              frequency_factor=args.frequency_factor)
