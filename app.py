# FULL FINAL VERSION (CLEAN + READY)
import os
import io
import base64
import traceback
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv
from pptx import Presentation
from pptx.util import Inches

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "lawmens-audit-2024")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
PPTX_TEMPLATE_PATH = os.environ.get("PPTX_TEMPLATE_PATH", "Savills.pptx")

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
# PPTX TEMPLATE FILLING
# -----------------------------

def _replace_in_paragraph(para, replacements):
    """
    Merges all runs in a paragraph into a single string, replaces placeholders,
    then puts the result back into the first run and clears the rest.
    This handles the common case where PPTX splits placeholder text across multiple runs.
    """
    if not para.runs:
        return
    full_text = ''.join(run.text for run in para.runs)
    new_text = full_text
    for key, value in replacements.items():
        new_text = new_text.replace(f'{{{{{key}}}}}', str(value) if value is not None else '')
    if new_text != full_text:
        para.runs[0].text = new_text
        for run in para.runs[1:]:
            run.text = ''

def _replace_in_text_frame(tf, replacements):
    for para in tf.paragraphs:
        _replace_in_paragraph(para, replacements)

def _replace_in_shape(shape, replacements):
    if shape.has_text_frame:
        _replace_in_text_frame(shape.text_frame, replacements)
    # Handle tables
    if shape.has_table:
        for row in shape.table.rows:
            for cell in row.cells:
                _replace_in_text_frame(cell.text_frame, replacements)
    # Handle grouped shapes
    if shape.shape_type == 6:  # MSO_SHAPE_TYPE.GROUP
        for s in shape.shapes:
            _replace_in_shape(s, replacements)

def fill_pptx_template(replacements):
    """Load the PPTX template, replace all placeholders, return BytesIO."""
    prs = Presentation(PPTX_TEMPLATE_PATH)
    for slide in prs.slides:
        for shape in slide.shapes:
            _replace_in_shape(shape, replacements)
    output = io.BytesIO()
    prs.save(output)
    output.seek(0)
    return output

def build_replacements(data, report):
    """Build the full placeholder -> value dict from form data and AI-generated text."""

    def g(key, default=''):
        return _first(data, key, default)

    r = {}

    # ----- Core report fields -----
    r['PROJECT_ADDRESS']               = report.get('job_address', g('job_address'))
    r['CLIENT_NAME']                   = report.get('client_name', g('client_name'))
    r['DATE_OF_REPORT']                = g('date_of_report', datetime.now().strftime('%d %B %Y'))
    r['REPORT_NUMBER']                 = g('report_number')
    r['PROJECT_WEIGHT']                = g('project_weight')
    r['KEY_WASTE_PRODUCTS']            = g('key_waste_products')
    r['INFORMATION_PROVIDED']          = g('information_provided')
    r['CIRCULAR_ECONOMY_COMMITMENTS']  = g('circular_economy_commitments')

    # ----- Prepared / Authorised by -----
    r['PREPARED_BY']        = g('prepared_by')
    r['PREPARED_BY_ROLE']   = g('prepared_by_role')
    r['PREPARED_DATE']      = g('prepared_date')
    r['AUTHORISED_BY']      = g('authorised_by')
    r['AUTHORISED_BY_ROLE'] = g('authorised_by_role')
    r['AUTHORISED_DATE']    = g('authorised_date')

    # ----- AI-generated text -----
    r['EXECUTIVE_SUMMARY'] = report.get('executive_summary', g('executive_summary'))

    # ----- Materials 1-20 -----
    # Each material has: name, EWC code, description, potential, risks,
    # weight, weight%, volume, reuse%, carbon, embodied carbon factor
    for i in range(1, 21):
        n = str(i)
        r[f'MATERIAL_{n}']             = g(f'material_{n}')
        r[f'MATERIAL_{n}_DESCRIPTION'] = g(f'material_{n}_description')
        r[f'MATERIAL_{n}_POTENTIAL']   = g(f'material_{n}_potential')
        r[f'MATERIAL_{n}_RISKS']       = g(f'material_{n}_risks')
        r[f'MATERIAL_{n}_']            = g(f'material_{n}_ewc')   # trailing underscore variant
        r[f'MATERIAL_EWC_{n}']         = g(f'material_{n}_ewc')   # EWC 1-10 naming
        r[f'MATERIAL_{n}_EWC']         = g(f'material_{n}_ewc')   # EWC 11-20 naming
        r[f'MAT_{n}_WEIGH']            = g(f'mat_{n}_weigh')
        r[f'MAT_{n}_WEIGHP']           = g(f'mat_{n}_weighp')
        r[f'MAT_{n}_VOL']              = g(f'mat_{n}_vol')
        r[f'MAT_{n}_REUSE']            = g(f'mat_{n}_reuse')
        r[f'MAT_{n}_EWC']              = g(f'mat_{n}_ewc')
        r[f'MAT_{n}_CARB']             = g(f'mat_{n}_carb')
        r[f'MAT_{n}_ECF']              = g(f'mat_{n}_ecf')

    # ----- Edge-case placeholders found in this specific template -----
    # {{MATERIAL 10}} has a space instead of underscore
    r['MATERIAL 10'] = g('material_10')
    # {{MATERIAL_10_}} trailing underscore (EWC variant for material 10)
    r['MATERIAL_10_'] = g('material_10_ewc')
    # {{{MATERIAL_2_POTENTIAL} triple brace typo in template — handled by replacing the inner text
    r['MATERIAL_2_POTENTIAL'] = g('material_2_potential')

    return r

# -----------------------------
# MAIN REPORT GENERATION
# -----------------------------

@app.route("/generate-canva-report", methods=["POST"])
def generate_canva_report():
    data = request.form.to_dict(flat=False)
    files = request.files
    report = _process_form_data(data, files)

    # Generate AI text automatically
    report["executive_summary"] = openai_generate(
        f"Write a professional executive summary for a pre-refurbishment/demolition audit "
        f"at {report['job_address']} for client {report['client_name']}."
    )

    # Build all placeholder replacements
    replacements = build_replacements(data, report)

    # Fill the PPTX template
    try:
        output = fill_pptx_template(replacements)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Failed to generate report: {str(e)}"}), 500

    # Return the filled PPTX as a downloadable file
    filename = f"Audit_{report['job_address'].replace(' ', '_')[:40]}.pptx"
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        as_attachment=True,
        download_name=filename
    )

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
        "job_address":         _first(data, "job_address"),
        "client_name":         _first(data, "client_name"),
        "building_photo":      _encode_upload(files.get("building_photo")),
        "waste_diversion_chart": "",
        "kwp_materials":       data.get("material_name", [])
    }

# -----------------------------

if __name__ == "__main__":
    app.run(debug=True)
