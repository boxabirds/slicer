from fasthtml.common import *
import requests
import os
import tempfile

app, rt = fast_app()

@rt('/')
def home():
    return Div(
        H1("Audio Slicer", cls="text-center text-4xl mt-10"),
        P("Instantly create midi instruments from spoken word recordings", cls="text-center text-lg mt-2"),
        Div(
            Div(
                P("Upload or drag and drop your audio file here", cls="text-center text-gray-500"),
                Input(type="file", accept="audio/*", cls="block mx-auto mt-4", hx_post="/process", hx_target="#output"),
                Button("Convert", cls="bg-blue-500 text-white p-2 rounded mt-4"),
                cls="border-2 border-dashed border-gray-300 p-6 mt-6"
            ),
            cls="flex flex-col items-center"
        ),
        Div(id="output", cls="mt-4"),
        cls="container mx-auto"
    )

@rt('/process', methods=['POST'])
def process():
    # Assume the file is uploaded and accessible as 'audio_file'
    audio_file = request.files['audio_file']
    audio_path = save_temp_file(audio_file)

    # Call WhisperX API
    response = call_whisperx_api(audio_path)

    # Process the response
    if response.status_code == 200:
        data = response.json()
        segments = data['output']['segments']
        temp_dir = create_word_files(segments)
        return Div(
            P(f"Files created in temporary directory: {temp_dir}", cls="text-center text-lg mt-4"),
            cls="flex flex-col items-center"
        )
    else:
        return Div(
            P("Error processing audio file.", cls="text-center text-lg mt-4 text-red-500"),
            cls="flex flex-col items-center"
        )

def save_temp_file(file):
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, file.filename)
    file.save(file_path)
    return file_path

def call_whisperx_api(audio_path):
    url = "https://api.replicate.com/v1/predictions"
    headers = {
        "Authorization": "Token YOUR_API_TOKEN",
        "Content-Type": "application/json"
    }
    data = {
        "version": "77505c700514deed62ab3891c0011e307f905ee527458afc15de7d9e2a3034e8",
        "input": {
            "audio_file": audio_path,
            "batch_size": 64,
            "vad_onset": 0.5,
            "vad_offset": 0.363,
            "diarization": False,
            "temperature": 0,
            "align_output": False
        }
    }
    return requests.post(url, headers=headers, json=data)

def create_word_files(segments):
    temp_dir = tempfile.mkdtemp()
    for segment in segments:
        words = segment['text'].split()
        for i, word in enumerate(words):
            word_file_path = os.path.join(temp_dir, f"word_{i}.wav")
            # Here you would convert the word to a wav file
            # This is a placeholder for the actual conversion logic
            with open(word_file_path, 'w') as f:
                f.write(f"Audio data for {word}")
    return temp_dir

serve()
