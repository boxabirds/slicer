import os
import tempfile
from pathlib import Path
from shutil import copyfile
from fasthtml.common import *
from staticfiles import store_static_file  # Import the staticfiles module
from transcribe import transcribe_audio  # Import the transcribe module
from slice import slice_audio_by_words  # Import the slice module
from soundfonts import create_sf2_json_file, create_sf2_from_json
from mididemos import create_demo_midi_files

# Initialize FastHTML app with Bootstrap CSS
app, rt = fast_app(hdrs=(
    Link(rel="stylesheet", href="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css"),
))

# Define the home route
@rt('/')
def home():
    return Div(
        H1("Audio Slicer", cls="text-center text-4xl mt-10"),
        Div(
            Div(
                # State 1: Logo, form for file upload
                Div(
                    Img(src="/static/audioslicer.png", cls="mb-4 w-32"),
                    P("Upload or drag and drop your audio file here", cls="text-center text-gray-500"),
                    Form(
                        # Add start note input before file input
                        Div(
                            Label("Start Note (0-127):", for_="start_note", cls="block mb-2"),
                            Input(
                                type="number",
                                id="start_note",
                                name="start_note",
                                min="0",
                                max="127", 
                                value="60",
                                cls="w-20 text-center mb-4"
                            ),
                            cls="mb-4"
                        ),
                        Input(type="file", name="audio_file", accept="audio/*", id="audio-input"),
                        Button("Upload", type="submit", cls="btn btn-primary mt-4"),  # Bootstrap button
                        enctype="multipart/form-data",
                        hx_post="/process",  # Sends request to /process route
                        hx_target="#state-panel",  # Updates the state-panel div
                        hx_swap="innerHTML",  # Swap inner content for new state
                        cls="flex flex-col items-center"
                    ),
                    cls="state-1 text-center"
                ),
                id="state-panel",  # Container for the dynamic states
                cls="flex justify-center"
            ),
            cls="flex flex-col items-center"
        ),
        cls="container mx-auto flex flex-col items-center justify-center"  # Horizontally center everything
    )

# Route for processing uploaded audio file (State 2: Processing)
@rt('/process', methods=['POST'])
async def process(request):
    form = await request.form()

    # Check if the audio_file is present
    if 'audio_file' not in form:
        return Div(P("No audio file uploaded.", cls="text-red-500"))

    audio_file = form['audio_file']
    audio_path = save_temp_file(audio_file)
    start_note = int(form.get('start_note', 60))  # Get start_note from form, default to 60

    # Display the processing state (State 2)
    return Div(
        Div(
            Div(cls="progress-bar progress-bar-striped progress-bar-animated", role="progressbar", style="width: 100%;"),
            cls="progress"
        ),
        P("Processing...", cls="text-center mt-4"),
        hx_trigger="load",  # Auto-trigger to start processing
        hx_post="/convert",  # Continue to the actual conversion step
        hx_target="#state-panel",  # Swap content again to show completion after processing
        hx_swap="innerHTML",  # Swap inner content with state-3
        hx_vals={"audio_path": audio_path, "start_note": start_note},  # Pass both values
        cls="state-2 text-center"
    )

# Route for conversion and final display (State 3: Completed)
@rt('/convert', methods=['POST'])
async def convert(request):
    form = await request.form()

    # Get the file path passed from the /process route
    audio_path = form['audio_path']
    start_note = int(form.get('start_note', 60))

    # Transcribe and process audio
    words = transcribe_audio(audio_path)
    words_with_paths = slice_audio_by_words(audio_path, words)

    # Create the SoundFont .sf2 file
    temp_dir = Path(words_with_paths[0]['file_path']).parent

    print(f"Creating SoundFont from wav files in '{temp_dir}'")
    sf, sf2_json_path = create_sf2_json_file(temp_dir,  start_note)
    sf2_path = temp_dir / f"{sf2_json_path.stem}.sf2"
    create_sf2_from_json(sf2_json_path, sf2_path)

    # create a set of wild and wonderful midi demos using the samples
    create_demo_midi_files(sf, start_note, sf2_path)

    # Store the .sf2 file using the staticfiles module
    stored_file_path = store_static_file(sf2_path)

    # Display the final state (State 3: Completion with download)
    return Div(
        P(f"Conversion complete. File is in {sf2_path.resolve()}", cls="text-center text-lg mt-4"),
        A("Download", href=f"/{stored_file_path}", download=sf2_path.name, cls="btn btn-success mt-4"),  # Dynamic download URL
        cls="state-3 text-center"
    )

# Route to serve static files from the output folder
@rt('/output/{file_path:path}')
def output_file(file_path: str):
    full_path = Path(f"output/{file_path}")
    
    if full_path.exists() and full_path.is_file():
        return FileResponse(full_path)
    else:
        return Div(P("File not found", cls="text-danger"))

# Helper function to save uploaded file in a temporary directory
def save_temp_file(file):
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, file.filename)
    with open(file_path, 'wb') as f:
        f.write(file.file.read())
    return file_path

# Start the FastHTML app
serve()
