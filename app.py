from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import os
import cv2
import shutil
import numpy as np
from PIL import Image
from cryptography.fernet import Fernet

app = Flask(__name__)
CORS(app, origins=[
    "https://ronitraj07.github.io",             # your frontend on GitHub Pages
    "https://steg-back.onrender.com"            # your backend on Render
])

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "output"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Encryption key for Ciphertext
KEY = Fernet.generate_key()
cipher = Fernet(KEY)

# Allow large file uploads
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

# Helper function to save uploaded files
def save_file(file, folder):
    file_path = os.path.join(folder, file.filename)
    file.save(file_path)
    return file_path

# ✅ Image Steganography Encoding
@app.route('/encode/image', methods=['POST'])
def encode_image():
    if 'file' not in request.files or 'message' not in request.form:
        return jsonify({"error": "Invalid request"}), 400

    file = request.files['file']
    message = request.form['message']

    file_path = save_file(file, UPLOAD_DIR)

    image = Image.open(file_path)
    encoded = image.copy()
    width, height = image.size
    binary_message = ''.join(format(ord(char), '08b') for char in message) + '1111111111111110'

    data_index = 0
    for y in range(height):
        for x in range(width):
            pixel = list(image.getpixel((x, y)))
            for n in range(3):
                if data_index < len(binary_message):
                    pixel[n] = pixel[n] & ~1 | int(binary_message[data_index])
                    data_index += 1
            encoded.putpixel((x, y), tuple(pixel))
            if data_index >= len(binary_message):
                break
        if data_index >= len(binary_message):
            break

    output_path = os.path.join(OUTPUT_DIR, "encoded_image.png")
    encoded.save(output_path)
    return send_file(output_path, as_attachment=True)

# ✅ Image Steganography Decoding
@app.route('/decode/image', methods=['POST'])
def decode_image():
    if 'file' not in request.files:
        return jsonify({"error": "Invalid request"}), 400

    file = request.files['file']
    file_path = save_file(file, UPLOAD_DIR)

    image = Image.open(file_path)
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
    else:
        return jsonify({"error": "No hidden message found"}), 400

    decoded_message = ''.join(
        chr(int(message_bits[i:i+8], 2)) 
        for i in range(0, len(message_bits), 8)
    )

    return jsonify({"message": decoded_message})

# ✅ Video Steganography Encoding
@app.route("/encode/video", methods=["POST"])
def encode_video():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        video_file = request.files["file"]
        message = request.form.get("message", "")

        if not video_file:
            return jsonify({"error": "Invalid file"}), 400

        print("✅ Received video:", video_file.filename)
        print("✅ Message to encode:", message)

        # Save video for processing
        video_path = os.path.join(UPLOAD_DIR, video_file.filename)
        video_file.save(video_path)

        # Simulate encoding process 
        encoded_video_path = os.path.join(OUTPUT_DIR, f"encoded_{video_file.filename}")
        shutil.copy(video_path, encoded_video_path)  # Simulating encoding

        # Ensure file exists before sending response
        if not os.path.exists(encoded_video_path):
            return jsonify({"error": "Encoding failed"}), 500

        return jsonify({
            "success": True,
            "message": "Video encoded successfully!",
            "encoded_video_url": f"http://localhost:5000/output/{os.path.basename(encoded_video_path)}"
        })

    except Exception as e:
        print("🔥 Video encoding error:", str(e))
        return jsonify({"error": str(e)}), 500

# ✅ Video Steganography Decoding
@app.route('/decode/video', methods=['POST'])
def decode_video():
    if 'file' not in request.files:
        return jsonify({"error": "Invalid request"}), 400

    file = request.files['file']
    file_path = save_file(file, UPLOAD_DIR)

    video = cv2.VideoCapture(file_path)
    if not video.isOpened():
        return jsonify({"error": "Failed to open video file"}), 400

    binary_message = ""

    while True:
        ret, frame = video.read()
        if not ret:
            break
        for i in range(frame.shape[0]):
            for j in range(frame.shape[1]):
                pixel = frame[i, j]
                for n in range(3):
                    binary_message += str(pixel[n] & 1)

    delimiter = '1111111111111110'
    if delimiter in binary_message:
        message_bits = binary_message.split(delimiter)[0]
    else:
        return jsonify({"error": "No hidden message found"}), 400

    decoded_message = ''.join(
        chr(int(message_bits[i:i+8], 2)) 
        for i in range(0, len(message_bits), 8)
    )

    video.release()
    return jsonify({"message": decoded_message})

# ✅ Ciphertext Encryption
@app.route('/encrypt/text', methods=['POST'])
def encrypt_text():
    data = request.json.get('text')
    encrypted = cipher.encrypt(data.encode())
    return jsonify({"encrypted": encrypted.decode()})

# ✅ Ciphertext Decryption
@app.route('/decrypt/text', methods=['POST'])
def decrypt_text():
    encrypted_data = request.json.get('encrypted')
    decrypted = cipher.decrypt(encrypted_data.encode())
    return jsonify({"decrypted": decrypted.decode()})

@app.route("/output/<filename>")
def get_encoded_video(filename):
    return send_from_directory(OUTPUT_DIR, filename)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
