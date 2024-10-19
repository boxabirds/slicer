# content of test_slice.py
import os
import json
import pytest
from pydub import AudioSegment
from slice import slice_audio_by_words

@pytest.fixture
def audio_test_cases():
    base_dir = "tests/data/slice/"
    test_cases = []
    for folder in os.listdir(base_dir):
        input_dir = os.path.join(base_dir, folder, "input")
        output_dir = os.path.join(base_dir, folder, "output")
        if os.path.isdir(input_dir) and os.path.isdir(output_dir):
            input_file = next((f for f in os.listdir(input_dir) if f.endswith('.wav')), None)
            output_json = os.path.join(output_dir, "output.json")
            if input_file and os.path.exists(output_json):
                test_cases.append((os.path.join(input_dir, input_file), output_json))
    return test_cases

def test_slice_audio_by_words(audio_test_cases):
    for input_path, expected_output_json in audio_test_cases:
        # Load the expected output JSON
        with open(expected_output_json, 'r') as f:
            expected_output = json.load(f)

        # Run the slicing function
        result = slice_audio_by_words(input_path, expected_output)

        # Compare the result with the expected output
        for segment, expected_segment in zip(result, expected_output):
            assert segment['word'] == expected_segment['word'], f"Word mismatch: {segment['word']} != {expected_segment['word']}"
            assert abs(segment['start'] - expected_segment['start']) < 0.01, f"Start time mismatch for word {segment['word']}"
            assert abs(segment['end'] - expected_segment['end']) < 0.01, f"End time mismatch for word {segment['word']}"
