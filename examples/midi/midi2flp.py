import music21
import OpenFL.FLP as F

def midi2flp(midifilename,
             quarternote_s=0.25,
             skip_leading_rests=True):
    """
    Given a midi file, return a list of FLP.Packets objects, one for each track.
    """
    mf = music21.midi.MidiFile()
    mf.open(midifilename)
    mf.read()
    soundstream = music21.midi.translate.midiFileToStream(mf)
    tracks = []
    for track in soundstream.elements:
        x=[x for x in track.flat.elements if isinstance(x, (music21.note.Note, music21.note.Rest))]
        pitchtime = []
        for thing in x:
            if isinstance(thing, music21.note.Rest):
                pitchtime.append((0, float(thing.duration.quarterLength)))
            else:
                pitchtime.append((thing.pitch.frequency, float(thing.duration.quarterLength)))
        packets = F.Packets([F.ZCurrent(80),])

        for i, (Hz, time) in enumerate(pitchtime):
            time *= quarternote_s
            if Hz == 0:
                if i != 0 and skip_leading_rests: # Don't start with a rest.
                    packets.append(F.Dwell(s=time))
            else:
                ufreq = Hz*8
                packets += [F.ZFeedRate(ufreq),
                            F.ZMove(-int(ufreq*0.5*float(time))), F.WaitForMovesToComplete(), 
                            F.ZMove(int(ufreq*0.5*float(time))), F.WaitForMovesToComplete()]
        tracks.append(packets)
    return tracks
