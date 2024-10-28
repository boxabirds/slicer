import os
import tempfile
from pydub import AudioSegment

def slice_audio_by_words(audio_path, words):
    """
    Slices the given audio file into segments based on word timings and saves each segment as a WAV file.
    Files are saved with numeric prefixes (e.g., '0001_word.wav') to maintain sequence order.

    :param audio_path: Path to the original audio file.
    :param words: A list of dictionaries, each containing 'word', 'start', and 'end' keys.
    :return: A list of dictionaries, each containing the word, its start and end times, and the file path of the saved audio segment.

    The function processes each word in the list, extracts the corresponding audio segment, and saves it as a WAV file.
    The return value is a list of dictionaries with the following structure:

    Example:
    [
        {
            'word': 'Hello',
            'start': 0.5,
            'end': 0.8,
            'file_path': '/path/to/temp_dir/0001_Hello.wav'
        },
        {
            'word': 'world',
            'start': 0.9,
            'end': 1.2,
            'file_path': '/path/to/temp_dir/0002_world.wav'
        }
    ]
    """
    audio = AudioSegment.from_file(audio_path)
    temp_dir = tempfile.mkdtemp()

    for i, word_info in enumerate(words, 1):
        word = word_info['word']
        start_time = word_info['start']  # in seconds
        end_time = word_info['end']      # in seconds

        # Calculate start and end in milliseconds
        start_ms = int(start_time * 1000)
        end_ms = int(end_time * 1000)

        # Extract the word's audio segment
        word_audio = audio[start_ms:end_ms]

        # Make word filenames safe
        safe_word = ''.join(c for c in word if c.isalnum() or c in (' ', '_')).replace(' ', '_')
        
        # Create filename with zero-padded index prefix (4 digits)
        filename = f"{i:04d}_{safe_word}.wav"
        #filename = f"{safe_word}.wav"
        # Save the word as a WAV file
        word_file_path = os.path.join(temp_dir, filename)
        word_audio.export(word_file_path, format="wav")

        # Add the file path to the word info
        word_info['file_path'] = word_file_path

    return words
