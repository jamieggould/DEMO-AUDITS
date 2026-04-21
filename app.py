# FULL FINAL VERSION (CLEAN + READY)

import os
import io
import json
import time
import base64
import traceback
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, session
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "lawmens-audit-2024")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

CANVA_API_BASE = "https://api.canva.com/rest/v1"
CANVA_CLIENT_ID = os.environ.get("CANVA_CLIENT_ID")
CANVA_CLIENT_SECRET = os.environ.get("CANVA_CLIENT_SECRET")
CANVA_REDIRECT_URI = os.environ.get("CANVA_REDIRECT_URI")
CANVA_TEMPLATE_ID = os.environ.get("CANVA_BRAND_TEMPLATE_ID")

# -----------------------------
# BASIC ROUTES
# -----------------------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health")
def health():
    return "OK", 200

# -----------------------------
# OPENAI TEXT GENERATION
# -----------------------------

def openai_generate(prompt):
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt
    )

    return response.output_text.strip()

@app.route("/generate-ai-text", methods=["POST"])
def generate_ai_text():
    data = request.get_json()
    section = data.get("section")
    report = data.get("report_data", {})

    if section == "executive_summary":
        prompt = f"Write an executive summary for a demolition audit at {report.get('job_address')}."
    elif section == "conclusion":
        prompt = f"Write a conclusion for demolition audit with materials: {report.get('kwp_materials')}"
    elif section == "introduction":
        prompt = f"Write an introduction for a demolition audit at {report.get('job_address')}."
    else:
        return jsonify({"error": "Unknown section"}), 400

    text = openai_generate(prompt)
    return jsonify({"text": text})

# -----------------------------
# CANVA AUTH
# -----------------------------

@app.route("/canva/connect")
def canva_connect():
    params = {
        "client_id": CANVA_CLIENT_ID,
        "redirect_uri": CANVA_REDIRECT_URI,
        "response_type": "code",
        "scope": "asset:write design:content:write design:content:read brandtemplate:content:read",
    }
    return redirect(f"https://www.canva.com/api/oauth/authorize?{requests.compat.urlencode(params)}")

@app.route("/canva/callback")
def canva_callback():
    code = request.args.get("code")

    res = requests.post(f"{CANVA_API_BASE}/oauth/token", json={
        "grant_type": "authorization_code",
        "code": code,
        "client_id": CANVA_CLIENT_ID,
        "client_secret": CANVA_CLIENT_SECRET,
        "redirect_uri": CANVA_REDIRECT_URI,
    })

    data = res.json()
    session["canva_token"] = data.get("access_token")

    return redirect("/")

def get_canva_token():
    return session.get("canva_token")

# -----------------------------
# MAIN REPORT GENERATION
# -----------------------------

@app.route("/generate-canva-report", methods=["POST"])
def generate_canva_report():

    token = get_canva_token()
    if not token:
        return jsonify({"error": "Connect Canva first"}), 401

    data = request.form.to_dict(flat=False)
    files = request.files

    report = _process_form_data(data, files)

    # Generate AI text automatically
    report["executive_summary"] = openai_generate(
        f"Executive summary for demolition audit at {report['job_address']}"
    )

    report["conclusion_text"] = openai_generate(
        f"Conclusion for demolition audit with materials {report['kwp_materials']}"
    )

    # Upload images to Canva
    def upload_image(data_url):
        if not data_url:
            return ""

        header, b64 = data_url.split(",", 1)
        binary = base64.b64decode(b64)

        res = requests.post(
            f"{CANVA_API_BASE}/assets",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("image.png", binary)}
        )
        return res.json().get("asset", {}).get("id")

    report["building_photo_asset"] = upload_image(report.get("building_photo"))
    report["chart_asset"] = upload_image(report.get("waste_diversion_chart"))

    # Build Canva payload
    payload = {
        "PROJECT_ADDRESS": {"type": "text", "text": report["job_address"]},
        "CLIENT_NAME": {"type": "text", "text": report["client_name"]},
        "EXECUTIVE_SUMMARY": {"type": "text", "text": report["executive_summary"]},
        "CONCLUSION_TEXT": {"type": "text", "text": report["conclusion_text"]},
        "BUILDING_PHOTO": {"type": "image", "asset_id": report["building_photo_asset"]},
        "WASTE_DIVERSION_CHART": {"type": "image", "asset_id": report["chart_asset"]},
    }

    # Create Canva design
    res = requests.post(
        f"{CANVA_API_BASE}/autofills",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            "brand_template_id": CANVA_TEMPLATE_ID,
            "data": payload
        }
    )

    job = res.json()
    job_id = job["job"]["id"]

    # Wait for completion
    for _ in range(30):
        time.sleep(2)
        check = requests.get(
            f"{CANVA_API_BASE}/autofills/{job_id}",
            headers={"Authorization": f"Bearer {token}"}
        ).json()

        if check["job"]["status"] == "success":
            design_id = check["design"]["id"]
            break

    return jsonify({
        "success": True,
        "design_id": design_id
    })

# -----------------------------
# FORM PROCESSING (UNCHANGED)
# -----------------------------

def _first(data, key, default=''):
    vals = data.get(key, [])
    return vals[0] if vals else default

def _encode_upload(file_storage):
    if not file_storage:
        return ""
    raw = file_storage.read()
    return f"data:image/png;base64,{base64.b64encode(raw).decode()}"

def _process_form_data(data, files):
    return {
        "job_address": _first(data, "job_address"),
        "client_name": _first(data, "client_name"),
        "building_photo": _encode_upload(files.get("building_photo")),
        "waste_diversion_chart": "",
        "kwp_materials": data.get("material_name", [])
    }

# -----------------------------

if __name__ == "__main__":
    app.run(debug=True)
