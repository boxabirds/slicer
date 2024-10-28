import os
import replicate as rp
import json
def transcribe_audio(file_path):
    """
    Transcribes the given WAV file using WhisperX via Replicate and returns an array of words
    with their start and end times.

    :param file_path: Path to the WAV file to be transcribed.
    :return: List of dictionaries containing word, start time, and end time.
    
    Response Format:
    The function returns a list of dictionaries, where each dictionary represents a word
    and its associated timing information. Each dictionary contains the following keys:
    
    - 'word': The transcribed word as a string.
    - 'start': The start time of the word in seconds as a float.
    - 'end': The end time of the word in seconds as a float.
    
    Example:
    [
        {'word': 'Hello', 'start': 0.5, 'end': 0.8},
        {'word': 'world', 'start': 0.9, 'end': 1.2},
        {'word': 'this', 'start': 1.3, 'end': 1.5},
        {'word': 'is', 'start': 1.6, 'end': 1.7},
        {'word': 'GPT', 'start': 1.8, 'end': 2.0}
    ]
    """    # This isn't strictly necessary but it's a good way to document the API token
    replicate_api_token = os.getenv('REPLICATE_API_TOKEN')
    if not replicate_api_token:
        raise EnvironmentError("REPLICATE_API_TOKEN environment variable not set")

    # Open the audio file as a binary stream
    with open(file_path, "rb") as f:
        # from https://replicate.com/victor-upmeet/whisperx example code
        model_version = "victor-upmeet/whisperx:84d2ad2d6194fe98a17d2b60bef1c7f910c46b2f6fd38996ca457afd9c8abfcb"
        prediction = rp.run(
            model_version,
            input={
                "audio_file": f,  # Pass the file directly
                "batch_size": 64,
                "vad_onset": 0.5,
                "vad_offset": 0.363,
                "diarization": False,
                "temperature": 0,
                "align_output": True  # Enable word-level timestamps
            }
        )

    # Extract word segments
    if prediction and 'segments' in prediction:
        words = []
        for segment in prediction['segments']:
            for word_info in segment.get('words', []):
                if 'start' in word_info and 'end' in word_info:
                    words.append({
                        'word': word_info['word'].strip(),
                        'start': word_info['start'],
                        'end': word_info['end']
                    })
                else:
                    print(f"Skipping word {word_info['word']} due to missing start or end")
        print(json.dumps(words, indent=2))
        return words
    else:
        raise ValueError("Error processing audio file or no segments found.")

