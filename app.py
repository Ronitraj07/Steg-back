from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import cv2
import numpy as np
from PIL import Image
from cryptography.fernet import Fernet
import io # Required for in-memory file handling

app = Flask(__name__)

# --- CONFIGURATION ---

# Allow requests from your specific GitHub Pages URL
# The '*' is a fallback, but it's better to be specific.
CORS(app, origins=["https://ronitraj07.github.io", "http://localhost:3000"])

# Set a file size limit (e.g., 50MB)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# --- ENCRYPTION SETUP ---

# IMPORTANT: Get the secret key from an environment variable.
# You must set this in your Vercel project settings.
key_str = os.environ.get('FERNET_KEY')
if not key_str:
    # This is a fallback for local development, but it's not secure for production.
    # A real key should be generated once and set in your environment.
    print("WARNING: FERNET_KEY environment variable not set. Using a temporary key.")
    key_str = Fernet.generate_key().decode('utf-8')

KEY = key_str.encode('utf-8')
cipher = Fernet(KEY)


# --- IMAGE STEGANOGRAPHY ---

@app.route('/encode/image', methods=['POST'])
def encode_image():
    if 'file' not in request.files or 'message' not in request.form:
        return jsonify({"error": "Invalid request: Missing file or message"}), 400

    file = request.files['file']
    message = request.form['message']

    try:
        # Read image directly into memory
        image = Image.open(io.BytesIO(file.read()))
        encoded = image.copy()
        width, height = image.size

        # Add a delimiter to know where the message ends
        binary_message = ''.join(format(ord(char), '08b') for char in message) + '1111111111111110'

        if len(binary_message) > width * height * 3:
            return jsonify({"error": "Message is too long for this image"}), 400

        data_index = 0
        for y in range(height):
            for x in range(width):
                if data_index < len(binary_message):
                    pixel = list(image.getpixel((x, y)))
                    for n in range(3): # R, G, B channels
                        if data_index < len(binary_message):
                            # Modify the least significant bit
                            pixel[n] = pixel[n] & ~1 | int(binary_message[data_index])
                            data_index += 1
                    encoded.putpixel((x, y), tuple(pixel))
                else:
                    break
            if data_index >= len(binary_message):
                break
        
        # Save the encoded image to an in-memory buffer
        byte_io = io.BytesIO()
        encoded.save(byte_io, 'PNG')
        byte_io.seek(0) # Rewind the buffer to the beginning

        return send_file(byte_io, mimetype='image/png', as_attachment=True, download_name='encoded_image.png')

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route('/decode/image', methods=['POST'])
def decode_image():
    if 'file' not in request.files:
        return jsonify({"error": "Invalid request: No file provided"}), 400

    file = request.files['file']

    try:
        image = Image.open(io.BytesIO(file.read()))
        binary_message = ""
        width, height = image.size

        for y in range(height):
            for x in range(width):
                pixel = image.getpixel((x, y))
                for n in range(3):
                    binary_message += str(pixel[n] & 1)
        
        delimiter = '1111111111111110'
        if delimiter in binary_message:
            message_bits = binary_message.split(delimiter)[0]
            decoded_message = ''.join(chr(int(message_bits[i:i+8], 2)) for i in range(0, len(message_bits), 8))
            return jsonify({"message": decoded_message})
        else:
            return jsonify({"error": "No hidden message found"}), 400

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


# --- VIDEO STEGANOGRAPHY (SIMPLIFIED FOR SERVERLESS) ---
# NOTE: Real video processing is very memory-intensive and may hit serverless limits.
# This example is simplified and may not work for large files or complex operations.

@app.route("/encode/video", methods=["POST"])
def encode_video():
    # This is a placeholder. Real video encoding is too complex for a simple example.
    # It would require libraries like moviepy and careful memory management.
    return jsonify({"error": "Video encoding is not implemented in this version due to serverless constraints."}), 501

@app.route('/decode/video', methods=['POST'])
def decode_video():
    # As with encoding, this is a placeholder.
    return jsonify({"error": "Video decoding is not implemented in this version due to serverless constraints."}), 501


# --- CIPHERTEXT ENCRYPTION/DECRYPTION ---

@app.route('/encrypt/text', methods=['POST'])
def encrypt_text():
    data = request.json.get('text')
    if not data:
        return jsonify({"error": "No text provided"}), 400
    encrypted = cipher.encrypt(data.encode())
    return jsonify({"encrypted": encrypted.decode()})


@app.route('/decrypt/text', methods=['POST'])
def decrypt_text():
    encrypted_data = request.json.get('encrypted')
    if not encrypted_data:
        return jsonify({"error": "No encrypted text provided"}), 400
    try:
        decrypted = cipher.decrypt(encrypted_data.encode())
        return jsonify({"decrypted": decrypted.decode()})
    except Exception:
        return jsonify({"error": "Decryption failed. The text may be invalid or the key may have changed."}), 400


# A simple root route to confirm the server is running
@app.route('/')
def index():
    return "Steganography Backend is running!"

# This part is not needed for Vercel, but good for local testing
if __name__ == "__main__":
    app.run(debug=True, port=5000)
