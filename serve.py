import os
import tempfile
from fasthtml.common import *
from transcribe import transcribe_audio  # Import the transcribe module
from slice import slice_audio_by_words  # Import the slice module
from soundfonts import create_sf2_json_file
from pathlib import Path

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

    # Transcribe the audio file
    try:
        words = transcribe_audio(audio_path)
    except Exception as e:
        return Div(
            P(f"Error processing audio file: {str(e)}", cls="text-center text-lg mt-4 text-red-500"),
            cls="flex flex-col items-center"
        )

    # Slice the audio by words
    words_with_paths = slice_audio_by_words(audio_path, words)

    # Assuming words_with_paths already contains files in a temp directory
    temp_dir = Path(words_with_paths[0]['file_path']).parent
    sf2_json_path = create_sf2_json_file(temp_dir)

    # Display the results including the temporary directory where the word audio files are saved
    return Div(
        P(f"SoundFont JSON file created. Check the console for file path. File saved in {sf2_json_path.resolve()}", cls="text-center text-lg mt-4"),
        cls="flex flex-col items-center"
    )

# Helper function to save uploaded file in a temporary directory
def save_temp_file(file):
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, file.filename)
    with open(file_path, 'wb') as f:
        f.write(file.file.read())
    return file_path

# Start the FastHTML app
serve()
