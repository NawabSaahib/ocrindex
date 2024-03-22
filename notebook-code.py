# CODE AFTER ADDING DOWNLOADING PART
from flask import send_file, make_response
from pyngrok import ngrok
from flask import Flask, render_template, request, redirect, url_for
from PIL import Image
import os
import re
import pytesseract
from flask import send_from_directory
import zipfile
import shutil

# Set Tesseract command path
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# Specify the project folder and template directory
images_folder = '/content/ocrindex/images'
template_folder = '/content/ocrindex'
port_no = 5000

# Flask Configuration
UPLOAD_FOLDER = images_folder
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}

app = Flask(__name__, template_folder=template_folder)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Set max upload size to 16MB

ngrok.set_auth_token("2ds0ymsPkJwByF4hssQzIVRsBUb_7QdXVC8XkL16yV3J6yxyf")
public_url = ngrok.connect(port_no).public_url

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def home():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    try:
        # Check if the post request has the file part
        if 'file' not in request.files:
            return "No file part in the request."

        uploaded_files = request.files.getlist('file')

        # Create the 'images' folder if it doesn't exist
        os.makedirs(images_folder, exist_ok=True)

        # Save uploaded files to the 'images' folder
        for uploaded_file in uploaded_files:
            if uploaded_file and allowed_file(uploaded_file.filename):
                file_path = os.path.join(images_folder, uploaded_file.filename)
                uploaded_file.save(file_path)

        keyword = "Sender's Reference"

        # Redirect to a new route that will execute the image processing code
        return redirect(url_for('execute_processing', keyword=keyword))

    except Exception as e:
        return f"Error processing files: {str(e)}"

# Add a new route to execute the image processing code
# ... (previous code)

def extract_reference_number(image_path, keyword):
    try:
        # Use Tesseract OCR to extract text from the image
        cmd = f'/usr/bin/tesseract "{image_path}" -'
        extracted_text = os.popen(cmd).read()

        # Print the extracted text for debugging
        print(f"Extracted Text from {image_path}:\n{extracted_text}")
 # Find the index of the keyword in the extracted text
        keyword_index = extracted_text.find(keyword)

        if keyword_index != -1:
            # Extract the text after the keyword
            text_after_keyword = extracted_text[keyword_index + len(keyword):].strip()

            # Split the text and take the first word as the reference number
            reference_number = text_after_keyword.split()[0]

            return reference_number
        else:
            print(f"Keyword '{keyword}' not found in the image.")
            return None
    except Exception as e:
        print(f"Error extracting reference number from {image_path}: {str(e)}")
        return None



@app.route('/execute_processing/<keyword>')
def execute_processing(keyword):
    try:
        files = [f for f in os.listdir(images_folder) if os.path.isfile(os.path.join(images_folder, f))]
        renamed_files = []  # Moved outside the loop

        for file_name in files:
            # Create the full path to the image file
            image_path = os.path.join(images_folder, file_name)

            # Extract the reference number from the current image
            reference_number = extract_reference_number(image_path, keyword)

            # Rename the file with the extracted reference number
            if reference_number is not None:
                new_file_name = f"{reference_number}.jpg"
                new_file_path = os.path.join(images_folder, new_file_name)

                try:
                    os.rename(image_path, new_file_path)
                    print(f"File {file_name} renamed successfully to: {new_file_path}")
                    renamed_files.append(new_file_path)
                except OSError as e:
                    print(f"Error renaming the file {file_name}: {str(e)}")
            else:
                print(f"File {file_name} not renamed due to missing reference number.")

        zip_filename = f'{images_folder}.zip'
        with zipfile.ZipFile(zip_filename, 'w') as zip_file:
            for file in renamed_files:
                zip_file.write(file, os.path.basename(file))

        download_button = f'<a href="/download" id="downloadButton">Download Renamed Files</a>'
        return f"Processing complete for folder: {images_folder} {download_button}"

    except Exception as e:
        return f"Error executing processing: {str(e)}"


import shutil
@app.route('/download')
def download():
    try:
        zip_filename = f'{images_folder}.zip'

        # Create a zip file with all renamed files
        renamed_files = [os.path.join(images_folder, f) for f in os.listdir(images_folder) if os.path.isfile(os.path.join(images_folder, f))]
        with zipfile.ZipFile(zip_filename, 'w') as zip_file:
            for file in renamed_files:
                zip_file.write(file, os.path.basename(file))

        # Delete all files in the 'images' folder
        for file in renamed_files:
            os.remove(file)

        # Create a response object and set headers to force browser download
        response = make_response(send_file(zip_filename, as_attachment=True))
        response.headers["Content-Disposition"] = f"attachment; filename={os.path.basename(zip_filename)}"
        return response

    except Exception as e:
        return f"Error downloading files: {str(e)}"


print(f"To access the Global link, please click {public_url}")
app.run(port=port_no)
