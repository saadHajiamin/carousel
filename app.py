import os
import io
import json
import requests
import zipfile
from flask import Flask, request, jsonify
from PIL import Image, ImageDraw, ImageFont
import cairo

app = Flask(__name__)

# Setup paths
BASE_DIR = "output"
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
os.makedirs(FONTS_DIR, exist_ok=True)

# Font URLs from GitHub
FONTS = {
    "amiri": {
        "url": "https://github.com/alif-type/amiri/releases/download/0.122/amiri-0.122.zip",
        "file": "Amiri-Regular.ttf"
    },
    "garamond": {
        "url": "https://github.com/georgd/EB-Garamond/releases/download/v0.016/EBGaramond-0.016.zip",
        "file": "EBGaramond-Bold.ttf"
    },
    "lora": {
        "url": "https://github.com/cyrealtype/Lora/releases/download/v4.202/Lora-Cyrillic.zip",
        "file": "Lora-Medium.ttf"
    }
}

# Download and extract fonts
def download_fonts():
    for name, info in FONTS.items():
        zip_path = os.path.join(FONTS_DIR, f"{name}.zip")
        font_path = os.path.join(FONTS_DIR, info["file"])
        if not os.path.exists(font_path):
            r = requests.get(info["url"])
            with open(zip_path, "wb") as f:
                f.write(r.content)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(FONTS_DIR)

# Create vertical gradient bg using cairo
def create_gradient_image(width=1080, height=1350):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)
    gradient = cairo.LinearGradient(0, 0, 0, height)
    gradient.add_color_stop_rgb(0, 0, 0, 0)
    gradient.add_color_stop_rgb(1, 0.1, 0.1, 0.1)
    ctx.rectangle(0, 0, width, height)
    ctx.set_source(gradient)
    ctx.fill()
    output = io.BytesIO()
    surface.write_to_png(output)
    output.seek(0)
    return Image.open(output)

# Draw centered text
def draw_text_centered(img, text, font_path, font_size=60):
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, font_size)
    lines = text.split("\n")
    line_heights = [draw.textsize(line, font=font)[1] for line in lines]
    total_height = sum(line_heights) + (10 * (len(lines)-1))
    current_y = (img.height - total_height) // 2
    for line, lh in zip(lines, line_heights):
        text_width, _ = draw.textsize(line, font=font)
        x = (img.width - text_width) // 2
        draw.text((x, current_y), line, font=font, fill="white")
        current_y += lh + 10
    return img

# Send to webhook
def send_to_webhook(image_path, number):
    url = "https://hook.eu2.make.com/zvi2nvx42ia5aqouj0o4t0kxtznw6qga"
    with open(image_path, "rb") as f:
        files = {"file": (f"post{number}.png", f, "image/png")}
        response = requests.post(url, files=files)
    print(f"Sent post{number}.png to webhook. Status: {response.status_code}")

# Main route
@app.route("/generate", methods=["POST"])
def generate_images():
    try:
        data = request.get_json()
        slides = data.get("slides", [])
        if not slides:
            return jsonify({"error": "No slides provided"}), 400

        download_fonts()

        for slide in slides:
            number = slide.get("slide_number", 0)
            slide_type = slide.get("slide_type", "").lower()
            text = slide.get("text", f"Slide {number}")

            img = create_gradient_image()

            if slide_type == "title":
                font_path = os.path.join(FONTS_DIR, FONTS["garamond"]["file"])
                font_size = 72
            elif slide_type == "quote":
                font_path = os.path.join(FONTS_DIR, FONTS["amiri"]["file"])
                font_size = 48
            else:
                font_path = os.path.join(FONTS_DIR, FONTS["lora"]["file"])
                font_size = 60

            img = draw_text_centered(img, text, font_path, font_size)
            save_path = os.path.join(BASE_DIR, f"post{number}.png")
            img.save(save_path)
            send_to_webhook(save_path, number)

        return jsonify({"message": f"{len(slides)} posts generated."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
