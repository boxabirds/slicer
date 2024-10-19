import argparse
from pathlib import Path
import sys
import json
import wave
from typing import List
from midiutil import MIDIFile
import os 


#Useful constants copied from http://www.synthfont.com/SFSPEC21.PDF
MONO_SAMPLE_TYPE = 1

class Generator:
    def __init__(self, operator: int, amount: int):
        self.operator = operator # TODO this should be an enum of all possible valid operators
        self.amount = amount

class Zone:
    # A zone is a high level representation of SF bags, generators and modulators. 
    # We have implemented only a specific scenario we care about for now,
    # where a bag has a sample id and a key range. 
    def __init__(self, sample_path: Path, root_key: int, lower_key: int, upper_key: int):
        self.sample = Sample(sample_path)
        self.sample.original_pitch = root_key
        self.root_key = root_key
        self.lower_key = lower_key
        self.upper_key = upper_key
        self.generators = []

    def add_generator(self, generator: Generator):
        self.generators.append(generator)

class Instrument:
    def __init__(self, name: str):
        self.name = name
        self.zones: List[Zone] = []

    def add_zone(self, zone: Zone):
        self.zones.append(zone)

class Preset:
    def __init__(self, name: str, preset: int, bank: int):
        self.name = name
        self.preset = preset
        self.bank = bank
        self.instruments: List[Instrument] = []

    def add_instrument(self, instrument: Instrument):
        self.instruments.append(instrument)

class Info:
    def __init__(self, name: str, author: str, product: str, copyright: str, comments: str):
        self.name = name
        self.author = author
        self.product = product
        self.copyright = copyright
        self.comments = comments

    def to_json(self):
        return {
            "id": "LIST",
            "form_type": "INFO",
            "contents": {
                "ifil": {"version": "2.01"},
                "isng": {"target_sound_engine": "All"},
                "INAM": {"bank_name": self.product},
                "IENG": {"author": self.author},
                "IPRD": {"product": self.product},
                "ICOP": {"copyright": self.copyright},
                "ICMT": {"comments": self.comments},
                "ISFT": {"tools": self.product}
            }
        }

class SoundFont:
    def __init__(self, name: str, author: str, product: str, copyright: str, comments: str):
        self.info = Info(name=name, author=author, product=product, copyright=copyright, comments=comments)
        self.presets: List[Preset] = []

    def create_default_preset_and_instrument(self):
        default_preset = Preset(name=self.info.name, preset=0, bank=0)
        self.presets.append(default_preset)
        
        default_instrument = Instrument(name=self.info.name)
        default_preset.add_instrument(default_instrument)

    def add_zone_to_default_instrument(self, zone: Zone):
        if self.presets and self.presets[0].instruments:
            self.presets[0].instruments[0].add_zone(zone)
        else:
            raise ValueError("Default preset and instrument have not been created yet.")

    def save(self, directory: Path) -> Path:
        sf2_json = {
            "id": "RIFF",
            "form_type": "sfbk",
            "contents": [
                self.info.to_json(),
                self.create_sdta(),
                self.create_pdta()
            ]
        }
        
        # make the path be relative to the directory
        sf2_json_path = directory / f"{self.info.name}.sf2.json"
        with open(sf2_json_path, "w") as f:
            json.dump(sf2_json, f, indent=2)
        return sf2_json_path

    def create_sdta(self):
        return {
            "id": "LIST",
            "form_type": "sdta",
            "contents": {
                "smpl": {
                    "data": "".join(sample.get_hex_data() for preset in self.presets 
                                    for instrument in preset.instruments 
                                    for zone in instrument.zones 
                                    for sample in [zone.sample])
                }
            }
        }

    def create_pdta(self):
        return {
            "id": "LIST",
            "form_type": "pdta",
            "contents": {
                "phdr": self.create_phdr(),
                "pbag": self.create_pbag(),
                "pmod": self.create_pmod(),
                "pgen": self.create_pgen(),
                "inst": self.create_inst(),
                "ibag": self.create_ibag(),
                "imod": self.create_imod(),
                "igen": self.create_igen(),
                "shdr": self.create_shdr()
            }
        }

    def create_phdr(self):
        entries = []
        for i, preset in enumerate(self.presets):
            entries.append({
                "name": preset.name,
                "preset": preset.preset,
                "bank": preset.bank,
                "bag_index": i,
                "library": 0,
                "genre": 0,
                "morphology": 0
            })
        # Add EOP terminator
        entries.append({
            "name": "EOP",
            "preset": 0,
            "bank": 0,
            "bag_index": len(self.presets),
            "library": 0,
            "genre": 0,
            "morphology": 0
        })
        return {"entries": entries}

    def create_pbag(self):
        entries = []
        gen_index = 0
        for preset in self.presets:
            entries.append({
                "generator_index": gen_index,
                "modulator_index": 0
            })
            gen_index += 1  # One generator per preset
        # Add terminator
        entries.append({
            "generator_index": gen_index,
            "modulator_index": 0
        })
        return {"entries": entries}

    def create_pmod(self):
        return {"entries": [{
            "source": 0,
            "destination": 0,
            "amount": 0,
            "amount_source": 0,
            "transform": 0
        }]}

    def create_pgen(self):
        entries = []
        for i, preset in enumerate(self.presets):
            entries.append({
                "operator": 41,  # Instrument
                "amount": i
            })
        # Add terminator
        entries.append({
            "operator": 0,
            "amount": 0
        })
        return {"entries": entries}

    def create_inst(self):
        entries = []
        bag_index = 0
        for preset in self.presets:
            for instrument in preset.instruments:
                entries.append({
                    "name": instrument.name,
                    "bag_index": bag_index
                })
                bag_index += len(instrument.zones)
        # Add EOI terminator
        entries.append({
            "name": "EOI",
            "bag_index": bag_index
        })
        return {"entries": entries}

    def create_ibag(self):
        entries = []
        gen_index = 0
        for preset in self.presets:
            for instrument in preset.instruments:
                for _ in instrument.zones:
                    entries.append({
                        "generator_index": gen_index,
                        "modulator_index": 0
                    })
                    gen_index += 2  # Each zone has two generators: sample id and note range
        # Add terminator
        entries.append({
            "generator_index": gen_index,
            "modulator_index": 0
        })
        return {"entries": entries}

    def create_imod(self):
        return {"entries": [{
            "source": 0,
            "destination": 0,
            "amount": 0,
            "amount_source": 0,
            "transform": 0
        }]}

    def create_igen(self):
        entries = []
        sample_index = 0
        for preset in self.presets:
            for instrument in preset.instruments:
                for zone in instrument.zones:
                    # Sample ID
                    entries.append({
                        "operator": 53,  # Sample ID
                        "amount": sample_index
                    })
                    # Note range
                    entries.append({
                        "operator": 43,  # Note range
                        "amount": [zone.lower_key, zone.upper_key]
                    })
                    sample_index += 1
        # Add igen terminator
        entries.append({
            "operator": 0,
            "amount": 0
        })
        return {"entries": entries}

    def create_shdr(self):
        entries = []
        start_offset = 0
        for preset in self.presets:
            for instrument in preset.instruments:
                for zone in instrument.zones:
                    sample = zone.sample
                    end_offset = start_offset + sample.sample_length
                    entries.append(sample.create_shdr(start_offset, end_offset))
                    start_offset = end_offset + 1 # Update start_offset for the next sample
        # Add EOS terminator
        entries.append(Sample.create_terminator())
        return {"entries": entries}

class Sample:
    def __init__(self, wav_path: Path):
        with wave.open(str(wav_path), 'rb') as wav_file:
            self.name = wav_path.stem
            self.sample_rate = wav_file.getframerate()
            self.sample_length = wav_file.getnframes()
            self.original_pitch = 60  # Default to middle C
            num_channels = wav_file.getnchannels()
            if num_channels == 2:
                raise ValueError("Stereo samples are not supported yet")
            self.data = wav_file.readframes(self.sample_length)

    def get_hex_data(self):
        return self.data.hex()
    
    def create_shdr(self, start: int, end: int):
        return {
            "name": self.name,
            "start": start,
            "end": end,
            "loop_start": 0, 
            "loop_end": 0,
            "sample_rate": self.sample_rate,
            "original_pitch": self.original_pitch, 
            "pitch_correction": 0,
            "sample_link": 0,
            "sample_type": 1  # Mono sample
        }


    @staticmethod
    def create_terminator():
        return {
            "name": "EOS",
            "start": 0,
            "end": 0,
            "loop_start": 0,
            "loop_end": 0,
            "sample_rate": 0,
            "original_pitch": 0,
            "pitch_correction": 0,
            "sample_link": 0,
            "sample_type": 0
        }

import math

def create_demo_midi_file(sf: SoundFont, start_note: int):
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

    # Create original MIDI file
    for i, sample in enumerate(samples):
        pitch = min(start_note + i, 127)  # Ensure pitch is within MIDI range (0-127)
        
        # Calculate duration in quarter notes
        duration_seconds = sample.sample_length / sample.sample_rate
        duration_quarter_notes = duration_seconds / (60 / tempo)
        
        print(f"Adding note {pitch} with duration {duration_quarter_notes} quarter notes at time {time} at volume {volume}")
        midi.addNote(track, channel, pitch, time, duration_quarter_notes, volume)
        time += duration_quarter_notes

    with open(f"{sf.info.name}.mid", "wb") as midi_file:
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

    with open(f"{sf.info.name}-quantized.mid", "wb") as midi_file:
        midi_quantized.writeFile(midi_file)

    print(f"MIDI files saved to {sf.info.name}.mid and {sf.info.name}-quantized.mid")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a SoundFont from WAV samples, one per note")
    parser.add_argument("--samples-dir", required=True, help="Directory containing WAV samples")
    parser.add_argument("--name", type=str, help="Name of the SoundFont (will be name of product, Preset and Instrument too)")
    parser.add_argument("--author", type=str, default="WordPlay")
    parser.add_argument("--copyright", type=str, default="2024 WordPlay")
    parser.add_argument("--comments", type=str, default="Created by WordPlay")
    parser.add_argument("--start-note", type=int, default=60, help="MIDI note number for the first sample")
    args = parser.parse_args()

    samples_dir = Path(args.samples_dir)
    if not samples_dir.is_dir():
        print(f"Error: {samples_dir} is not a valid directory", file=sys.stderr)
        sys.exit(1)

    max_samples = 127
    start_note = args.start_note
    end_note = min(start_note + max_samples - 1, 127)  # Ensure end note doesn't exceed MIDI range

    samples = sorted(samples_dir.glob("*.wav"))
    if not samples:
        print(f"Error: No WAV files found in {samples_dir}", file=sys.stderr)
        sys.exit(1)

    # we can only have as many samples as the number of notes on a keyboard
    selected_samples = samples[:min(len(samples), end_note - start_note + 1)]

    if len(samples) > len(selected_samples):
        excluded_samples = samples[len(selected_samples):]
        print(f"Warning: Number of samples ({len(samples)}) exceeds the maximum allowed ({len(selected_samples)}).")
        print("The following samples were not included:")
        for sample in excluded_samples:
            print(f"- {sample}")

    print(f"Found {len(samples)} WAV files in {samples_dir}")

    # Use the directory name if --name is not provided
    name = args.name if args.name else samples_dir.name

    sf = SoundFont(
        name=name, 
        author=args.author, 
        product=name, 
        copyright=args.copyright, 
        comments=args.comments
    )
    sf.create_default_preset_and_instrument()

    current_note = args.start_note
    for sample_path in samples:
        # for our specific situation we only have one note per sample
        zone = Zone(sample_path, root_key=current_note, lower_key=current_note, upper_key=current_note)
        sf.add_zone_to_default_instrument(zone)
        current_note += 1

    sf.save(samples_dir)
    print(f"JSON equivlant of an sf2 file saved to {sf.info.name}.sf2.json")

    create_demo_midi_file(sf, args.start_note)
    print(f"MIDI file saved to {sf.info.name}.mid")

def create_sf2_json_file(samples_dir: Path, start_note: int = 60) -> Path:
    sf = SoundFont(
        name="AudioSlicer",
        author="WordPlay",
        product="AudioSlicer",
        copyright="2024 WordPlay",
        comments="Created by WordPlay"
    )
    sf.create_default_preset_and_instrument()

    samples = sorted(samples_dir.glob("*.wav"), key=lambda x: os.path.getmtime(x))
    for i, sample_path in enumerate(samples):
        zone = Zone(sample_path, root_key=start_note + i, lower_key=start_note + i, upper_key=start_note + i)
        sf.add_zone_to_default_instrument(zone)

    return sf.save(samples_dir)
