import replicate
import os
import tempfile
from pydub import AudioSegment
from fasthtml.common import Div, H1, P, Form, Input, Button, serve, fast_app

# Initialize FastHTML app
app, rt = fast_app()

# Define the home route
@rt('/')
def home():
    return Div(
        H1("Audio Slicer", cls="text-center text-4xl mt-10"),
        P("Create midi instruments from spoken word recordings", cls="text-center text-lg mt-2"),
        Div(
            Form(
                P("Upload or drag and drop your audio file here", cls="text-center text-gray-500"),
                Input(type="file", name="audio_file", accept="audio/*"),
                Button("Convert", type="submit", cls="bg-blue-500 text-white p-2 rounded mt-4"),
                enctype="multipart/form-data",
                action="/process",
                method="post",
                cls="border-2 border-dashed border-gray-300 p-6 mt-6"
            ),
            cls="flex flex-col items-center"
        ),
        Div(id="output", cls="mt-4"),
        cls="container mx-auto"
    )

# Route for processing uploaded audio file
@rt('/process', methods=['POST'])
async def process(request):
    form = await request.form()

    # Check if the audio_file is present
    if 'audio_file' not in form:
        return Div(P("No audio file uploaded.", cls="text-red-500"))

    audio_file = form['audio_file']
    audio_path = save_temp_file(audio_file)

    # Open the audio file as a binary stream and send to WhisperX via Replicate
    with open(audio_path, "rb") as f:
        response = call_whisperx_api(f)

    # Process the response and create word-level audio files
    if response and 'segments' in response:
        segments = response['segments']
        temp_dir = slice_word_audio(segments, audio_path)
        return Div(
            P(f"Files created in temporary directory: {temp_dir}", cls="text-center text-lg mt-4"),
            cls="flex flex-col items-center"
        )
    else:
        return Div(
            P("Error processing audio file or no segments found.", cls="text-center text-lg mt-4 text-red-500"),
            cls="flex flex-col items-center"
        )

# Helper function to save uploaded file in a temporary directory
def save_temp_file(file):
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, file.filename)
    with open(file_path, 'wb') as f:
        f.write(file.file.read())
    return file_path

# Helper function to call WhisperX via Replicate using the binary file
def call_whisperx_api(file):

    # the replicate system requires an API token -- this is really just documenting what is being expected
    replicate_api_token = os.getenv('REPLICATE_API_TOKEN')
    if not replicate_api_token:
        raise EnvironmentError("REPLICATE_API_TOKEN environment variable not set")

    model_version = "victor-upmeet/whisperx:84d2ad2d6194fe98a17d2b60bef1c7f910c46b2f6fd38996ca457afd9c8abfcb"
    prediction = replicate.run(
        model_version,
        input={
            "audio_file": file,  # Pass the file directly
            "batch_size": 64,
            "vad_onset": 0.5,
            "vad_offset": 0.363,
            "diarization": False,
            "temperature": 0,
            "align_output": True  # Enable word-level timestamps
        }
    )
    return prediction

# Function to slice audio by words using Pydub
def slice_word_audio(segments, audio_path):
    audio = AudioSegment.from_file(audio_path)
    temp_dir = tempfile.mkdtemp()

    for segment in segments:
        word_timestamps = segment.get('words', [])
        for i, word_info in enumerate(word_timestamps):
            word = word_info['word'].strip()
            start_time = word_info['start']  # in seconds
            end_time = word_info['end']      # in seconds

            # Calculate start and end in milliseconds
            start_ms = int(start_time * 1000)
            end_ms = int(end_time * 1000)

            # Extract the word's audio segment
            word_audio = audio[start_ms:end_ms]

            # Make word filenames safe
            safe_word = ''.join(c for c in word if c.isalnum() or c in (' ', '_')).replace(' ', '_')

            # Save the word as a WAV file
            word_file_path = os.path.join(temp_dir, f"{i+1:04d}_{safe_word}_{start_time:.2f}_{end_time:.2f}.wav")
            word_audio.export(word_file_path, format="wav")

    return temp_dir

# Start the FastHTML app
serve()
