import struct
import json
from pathlib import Path
import argparse

def pack_chunk(id, data):
    return id.encode() + struct.pack('<I', len(data)) + data

def pack_subchunk(id, data):
    # Ensure word alignment
    if len(data) % 2 != 0:
        data += b'\0'
    return id.encode() + struct.pack('<I', len(data)) + data

def create_sf2_from_json(json_path, output_path):
    print(f"Reading JSON file: {json_path}")
    with open(json_path, 'r') as f:
        sf2_data = json.load(f)
    
    print("JSON file loaded successfully")
    print(f"SF2 version: {sf2_data['id']} {sf2_data['form_type']}")
    
    warnings = []

    # Pack INFO chunk
    print("Processing INFO chunk...")
    info_chunk = b''
    for chunk in sf2_data['contents']:
        if chunk['id'] == 'LIST' and chunk['form_type'] == 'INFO':
            for subchunk in ['ifil', 'isng', 'INAM', 'IENG', 'IPRD', 'ICOP', 'ICMT', 'ISFT']:
                if subchunk in chunk['contents']:
                    info = chunk['contents'][subchunk]
                    if subchunk == 'ifil':
                        if isinstance(info['version'], str):
                            major, minor = map(int, info['version'].split('.'))
                        else:
                            major, minor = info['version']['major'], info['version']['minor']
                        data = struct.pack('<HH', major, minor)
                        print(f"  {subchunk}: Version {major}.{minor}")
                    else:
                        value = list(info.values())[0]
                        data = value.encode().ljust(len(value) + 1, b'\0')
                        if len(value) > 256:
                            warnings.append(f"INFO.{subchunk} truncated to 256 bytes")
                        print(f"  {subchunk}: {value[:50]}... (truncated if longer than 50 chars)")
                    info_chunk += pack_subchunk(subchunk, data)
                else:
                    print(f"  {subchunk}: Not found in JSON")
            break
    info_list = pack_chunk('LIST', b'INFO' + info_chunk)
    print(f"INFO chunk size: {len(info_chunk)} bytes")

    # Pack sdta chunk
    print("Processing sdta chunk...")
    sdta_chunk = b''
    for chunk in sf2_data['contents']:
        if chunk['id'] == 'LIST' and chunk['form_type'] == 'sdta':
            if 'smpl' in chunk['contents']:
                sample_data = bytes.fromhex(chunk['contents']['smpl']['data'])
                sdta_chunk += pack_subchunk('smpl', sample_data)
                print(f"  smpl: {len(sample_data)} bytes of sample data")
            else:
                print("  smpl: No sample data found")
            break
    sdta_list = pack_chunk('LIST', b'sdta' + sdta_chunk)
    print(f"sdta chunk size: {len(sdta_chunk)} bytes")

    # Pack pdta chunk
    print("Processing pdta chunk...")
    pdta_chunk = b''
    for chunk in sf2_data['contents']:
        if chunk['id'] == 'LIST' and chunk['form_type'] == 'pdta':
            for subchunk in ['phdr', 'pbag', 'pmod', 'pgen', 'inst', 'ibag', 'imod', 'igen', 'shdr']:
                if subchunk in chunk['contents']:
                    entries = chunk['contents'][subchunk]['entries']
                    packed_entries = b''
                    print(f"  {subchunk}: {len(entries)} entries")
                    for entry in entries:
                        if subchunk in ['pgen', 'igen']:
                            operator = entry['operator']
                            amount = entry['amount']
                            if operator == 43:  # rangesType
                                if isinstance(amount, list) and len(amount) == 2:
                                    low_byte, high_byte = amount
                                    amount = (high_byte << 8) | low_byte
                                else:
                                    print(f"Warning: Invalid amount format for operator 43 in {subchunk}. Using 0.")
                                    amount = 0
                            packed_entries += struct.pack('<HH', operator, amount)
                        elif subchunk == 'phdr':
                            name = entry['name'].encode().ljust(20, b'\0')[:20]
                            packed_entries += struct.pack('<20sHHHIII', 
                                name, 
                                entry['preset'], entry['bank'], entry['bag_index'],
                                entry['library'], entry['genre'], entry['morphology'])
                        elif subchunk == 'pbag':
                            packed_entries += struct.pack('<HH', 
                                entry['generator_index'], entry['modulator_index'])
                        elif subchunk == 'pmod':
                            packed_entries += struct.pack('<BBHBHxxx', 
                                entry['source'], entry['destination'], entry['amount'],
                                entry['amount_source'], entry['transform'])
                        elif subchunk == 'inst':
                            name = entry['name'].encode().ljust(20, b'\0')[:20]
                            packed_entries += struct.pack('<20sH', 
                                name, entry['bag_index'])
                        elif subchunk == 'ibag':
                            packed_entries += struct.pack('<HH', 
                                entry['generator_index'], entry['modulator_index'])
                        elif subchunk == 'imod':
                            packed_entries += struct.pack('<HHhHH', 
                                entry['source'], entry['destination'], entry['amount'],
                                entry['amount_source'], entry['transform'])
                        elif subchunk == 'igen':
                            packed_entries += struct.pack('<HH', 
                                entry['operator'], entry['amount'])
                        elif subchunk == 'shdr':
                            name = entry['name'].encode().ljust(20, b'\0')[:20]
                            packed_entries += struct.pack('<20sIIIIIBbHH', 
                                name, entry['start'], entry['end'],
                                entry['loop_start'], entry['loop_end'], entry['sample_rate'],
                                entry['original_pitch'], entry['pitch_correction'], entry['sample_link'],
                                entry['sample_type'])
                    pdta_chunk += pack_subchunk(subchunk, packed_entries)
                else:
                    print(f"  {subchunk}: Not found in JSON")
            break
    pdta_list = pack_chunk('LIST', b'pdta' + pdta_chunk)
    print(f"pdta chunk size: {len(pdta_chunk)} bytes")

    # Combine all chunks
    riff_data = info_list + sdta_list + pdta_list

    # Update RIFF header with correct size and form type
    riff_header = b'RIFF' + struct.pack('<I', len(riff_data) + 4) + b'sfbk'

    # Write the final sf2 file
    print(f"Writing SF2 file: {output_path}")
    with open(output_path, 'wb') as f:
        f.write(riff_header + riff_data)

    print(f"\nSF2 file created successfully: {output_path}")
    print(f"Total file size: {len(riff_header + riff_data)} bytes")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert JSON to SF2 file")
    parser.add_argument("input_json", type=str, help="Input JSON file")
    parser.add_argument("--output", type=str, help="Output SF2 file name (default: <input stem>.json.sf2)")
    
    args = parser.parse_args()
    
    input_path = Path(args.input_json)
    output_path = Path(args.output) if args.output else input_path.with_suffix('.json.sf2')
    
    try:
        create_sf2_from_json(str(input_path), str(output_path))
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
