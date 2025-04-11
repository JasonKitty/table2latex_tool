# MIT License
# Copyright (c) 2025 JasonKitty (shibo.zhou1@gmail.com, shibo.zhou@zhejianglab.org)
# This file is part of the Table2LaTeX Tool project.
# See the LICENSE file in the repository root for full license text.

from flask import Flask, render_template, request, jsonify
from model import image_to_latex
from PIL import Image

import os
import uuid
import shutil
import subprocess
import numpy as np
from PIL import Image
from flask import request, jsonify, send_from_directory
from pdf2image import convert_from_path
import cv2

def compile_latex(latex_code, output_dir):
    linesep = '\n'
    usepackages = [
        '\\usepackage{graphicx}\n\\usepackage{amsmath, amssymb, mathtools, booktabs, multirow, array, bm, pifont, xcolor, makecell}',
        # '\\usepackage{pifont}\n\\usepackage{bbding}',
#         r"""\makeatletter
# \newcommand{\thickhline}{%
#   \noalign {\ifnum 0=`}\fi \hrule height 2pt
#   \futurelet \reserved@a \@xhline
# }
# \makeatother"""
    ]
    full_code = fr"""
\documentclass[UTF8]{{ctexart}}
{linesep.join(usepackages)}
\pagestyle{{empty}}
\begin{{document}}
\resizebox*{{0.5\columnwidth}}{{!}}{{
{latex_code}
}}
\end{{document}}
""".strip()

    tex_path = os.path.join(output_dir, "temp.tex")
    with open(tex_path, "w") as f:
        f.write(full_code)
    print(full_code)
    result = subprocess.run(
        ["xelatex", "-interaction=nonstopmode", "-output-directory", output_dir, tex_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30
    )

    return os.path.join(output_dir, "temp.pdf")


def crop_pdf(pdf_path):
    def crop_table(img):
        data = np.array(img.convert("L")).astype(np.uint8)
        max_val = data.max()
        min_val = data.min()
        if max_val == min_val:
            return img
        data = (data - min_val) / (max_val - min_val) * 255
        gray = 255 * (data < 200).astype(np.uint8)

        coords = cv2.findNonZero(gray)
        a, b, w, h = cv2.boundingRect(coords)
        return img.crop((a - 10, b - 10, a + w + 10, b + h + 10))

    pages = convert_from_path(pdf_path, 300)
    page = pages[-1].convert("RGB")
    cropped = crop_table(page)
    output_path = f"/tmp/{uuid.uuid4()}.png"
    cropped.save(output_path)
    return output_path


app = Flask(__name__, static_folder="static", template_folder="templates")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    file = request.files['image']
    image = Image.open(file.stream).convert("RGB")
    
    latex = image_to_latex(image)

    return jsonify({'latex': latex})

@app.route("/render", methods=["POST"])
def render_latex():
    data = request.get_json()
    latex_code = data.get("latex", "")
    if not latex_code:
        return jsonify({"error": "No LaTeX code provided"}), 400

    tmp_dir = f"/tmp/latex_render_{uuid.uuid4()}"
    os.makedirs(tmp_dir, exist_ok=True)

    pdf_path = compile_latex(latex_code, tmp_dir)
    print('pdf', pdf_path)
    if not pdf_path or not os.path.exists(pdf_path):
        return jsonify({"error": "Failed to compile LaTeX"}), 500

    try:
        img_path = crop_pdf(pdf_path)
        final_name = f"{uuid.uuid4()}.png"
        final_path = os.path.join("static/render", final_name)
        os.makedirs(os.path.dirname(final_path), exist_ok=True)
        shutil.move(img_path, final_path)

        return jsonify({"image_url": f"/static/render/{final_name}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8396, debug=False)
