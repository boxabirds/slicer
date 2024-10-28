from midiutil import MIDIFile
from soundfonts import SoundFont
import math
from pathlib import Path

def create_demo_midi_files(sf: SoundFont, start_note: int, sf2_path: Path):
    midi = MIDIFile(1)  # Create a MIDIFile with 1 track
    track = 0
    time = 0
    tempo = 120  # Default tempo in BPM
    midi.addTrackName(track, time, sf.info.name)
    midi.addTempo(track, time, tempo)

    channel = 0
    volume = 100

    samples = []
    for preset in sf.presets:
        for instrument in preset.instruments:
            for zone in instrument.zones:
                samples.append(zone.sample)

    # Get the directory of the SF2 file using pathlib
    output_dir = Path(sf2_path).parent
    
    # Create original MIDI file
    for i, sample in enumerate(samples):
        pitch = min(start_note + i, 127)  # Ensure pitch is within MIDI range (0-127)
        
        # Calculate duration in quarter notes
        duration_seconds = sample.sample_length / sample.sample_rate
        duration_quarter_notes = duration_seconds / (60 / tempo)
        
        print(f"Adding note {pitch} with duration {duration_quarter_notes} quarter notes at time {time} at volume {volume}")
        midi.addNote(track, channel, pitch, time, duration_quarter_notes, volume)
        time += duration_quarter_notes

    midi_path = output_dir / f"{sf.info.name}.mid"
    with midi_path.open("wb") as midi_file:
        midi.writeFile(midi_file)

    # Create quantized MIDI file
    midi_quantized = MIDIFile(1)
    midi_quantized.addTrackName(track, 0, sf.info.name + " (Quantized)")
    midi_quantized.addTempo(track, 0, tempo)

    time = 0
    for i, sample in enumerate(samples):
        pitch = min(start_note + i, 127)
        
        duration_seconds = sample.sample_length / sample.sample_rate
        duration_quarter_notes = duration_seconds / (60 / tempo)
        
        # Quantize start time to nearest eighth note
        quantized_start = math.ceil(time * 2) / 2
        
        # Adjust duration to avoid overlap
       # adjusted_duration = max(duration_quarter_notes - (quantized_start - time), 0.125)  # Minimum duration of 1/8 note
        
        #print(f"Adding quantized note {pitch} with duration {adjusted_duration} quarter notes at time {quantized_start} at volume {volume}")
        midi_quantized.addNote(track, channel, pitch, quantized_start, duration_quarter_notes, volume)
        
        time = quantized_start + duration_quarter_notes

    quantized_midi_path = output_dir / f"{sf.info.name}-quantized.mid"
    with quantized_midi_path.open("wb") as midi_file:
        midi_quantized.writeFile(midi_file)

    print(f"MIDI files saved to {midi_path} and {quantized_midi_path}")
