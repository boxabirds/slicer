import os
import sys
import torch
import whisperx
import torchaudio

def main(input_file):
    # Ensure the input file exists
    if not os.path.isfile(input_file):
        print(f"Input file {input_file} does not exist.")
        return

    # Create output folder
    input_stem = os.path.splitext(os.path.basename(input_file))[0]
    output_dir = f"{input_stem}-words"
    os.makedirs(output_dir, exist_ok=True)

    # Load audio file
    waveform, sample_rate = torchaudio.load(input_file)

    # Determine the device to run the model on
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Set compute type
    compute_type = "float16" if device == "cuda" else "float32"

    # Load the Whisper model
    print("Loading Whisper model...")
    model = whisperx.load_model("medium", device, compute_type=compute_type)

    # Transcribe the audio
    print("Transcribing audio...")
    result = model.transcribe(input_file)

    # Load the alignment model and metadata
    print("Loading alignment model...")
    model_a, metadata = whisperx.load_align_model(
        language_code=result["language"], device=device
    )

    # Align the transcribed segments
    print("Aligning words...")
    result_aligned = whisperx.align(
        result["segments"], model_a, metadata, input_file, device
    )

    # Process each word segment
    print("Processing word segments...")
    for i, word_info in enumerate(result_aligned['word_segments']):
        print(word_info)
        word = word_info['word'].strip()
        start_time = word_info['start']  # in seconds
        end_time = word_info['end']      # in seconds

        # Convert time to sample indices
        start_sample = int(start_time * sample_rate)
        end_sample = int(end_time * sample_rate)

        # Ensure the indices are within the waveform's length
        start_sample = max(0, start_sample)
        end_sample = min(waveform.size(1), end_sample)

        # Extract audio segment for the word
        word_waveform = waveform[:, start_sample:end_sample]

        # Convert to mono if stereo
        if word_waveform.size(0) > 1:
            word_waveform = word_waveform.mean(dim=0, keepdim=True)

        # Ensure 16-bit PCM
        word_waveform = word_waveform.to(torch.float32)
        word_waveform = word_waveform * 32767
        word_waveform = word_waveform.clamp(-32768, 32767).to(torch.int16)

        # Format start and end times
        start_time_str = "{:.2f}".format(start_time)
        end_time_str = "{:.2f}".format(end_time)

        # Make the word safe for filenames
        safe_word = ''.join(c for c in word if c.isalnum() or c in (' ', '_')).rstrip()
        safe_word = safe_word.replace(' ', '_')

        # Construct the output filename
        output_filename = f"{i+1:04d}_{safe_word}_{start_time_str}_{end_time_str}.wav"
        output_filepath = os.path.join(output_dir, output_filename)

        # Save the audio segment as 16-bit linear mono WAV
        torchaudio.save(output_filepath, word_waveform, sample_rate, bits_per_sample=16, encoding='PCM_S')

    print(f"Word audio files have been saved to {output_dir}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <input_audio_file>")
    else:
        main(sys.argv[1])
