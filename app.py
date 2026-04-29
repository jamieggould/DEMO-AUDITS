"""
Lawmens Pre-Demolition Audit Generator — Flask backend
Template: Savills-3.pptx
"""
import os
import io
import traceback
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv
from pptx import Presentation
from pptx.util import Inches
from pptx.chart.data import ChartData
from pptx.enum.chart import XL_CHART_TYPE

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "lawmens-audit-2024")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
PPTX_TEMPLATE_PATH = os.environ.get("PPTX_TEMPLATE_PATH", "Savills-3.pptx")

# ─────────────────────────────────────────────────────────────
# BASIC ROUTES
# ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health")
def health():
    return "OK", 200

# ─────────────────────────────────────────────────────────────
# OPENAI TEXT GENERATION
# ─────────────────────────────────────────────────────────────

def openai_generate(prompt):
    """Generate text via OpenAI. Returns empty string on any failure."""
    if not OPENAI_API_KEY:
        return ""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception:
        traceback.print_exc()
        return ""

@app.route("/generate-ai-text", methods=["POST"])
def generate_ai_text():
    data = request.get_json()
    section = data.get("section")
    report = data.get("report_data", {})

    if section == "executive_summary":
        prompt = (
            f"Write a professional executive summary for a pre-refurbishment/demolition audit "
            f"at {report.get('job_address', 'the site')} for client {report.get('client_name', '')}. "
            f"Keep it to 3-4 concise paragraphs."
        )
    elif section == "conclusion":
        mats = report.get('kwp_materials', [])
        mat_text = ', '.join(m['name'] for m in mats if m.get('name')) if mats else 'various materials'
        prompt = (
            f"Write a professional conclusion and recommendations section for a pre-demolition audit. "
            f"Key waste products identified: {mat_text}. Keep it to 2-3 paragraphs."
        )
    elif section == "introduction":
        prompt = (
            f"Write a professional introduction for a pre-refurbishment/demolition audit "
            f"at {report.get('job_address', 'the site')}. Keep it to 2 paragraphs."
        )
    else:
        return jsonify({"error": "Unknown section"}), 400

    text = openai_generate(prompt)
    if not text:
        return jsonify({"error": "AI generation failed. Check OPENAI_API_KEY is set in your environment."}), 500
    return jsonify({"text": text})

# ─────────────────────────────────────────────────────────────
# EXCEL CALCULATOR PARSER
# ─────────────────────────────────────────────────────────────

# Sheet1 summary layout: material pairs every 6 rows
CALC_MATERIAL_MAP = [
    (20, 'Carpet',            'Timber'),
    (26, 'Plasterboard',      'Glass'),
    (32, 'Metal',             'Hardcore'),
    (38, 'Insulation',        'Fibre Ceiling Tiles'),
    (44, 'Plastic',           'Vinyl'),
    (50, 'Rubber',            'Fabric'),
    (56, 'Fluorescent Tubes', 'Oil / Hydraulic Fluid'),
]

EWC_CODES = {
    'Carpet':               '20 03 01',
    'Timber':               '17 02 01',
    'Plasterboard':         '17 08 02',
    'Glass':                '17 02 02',
    'Metal':                '17 04 05',
    'Hardcore':             '17 01 01',
    'Insulation':           '17 06 04',
    'Fibre Ceiling Tiles':  '17 06 05',
    'Plastic':              '17 02 03',
    'Vinyl':                '20 01 39',
    'Rubber':               '16 01 03',
    'Fabric':               '20 01 10',
    'Fluorescent Tubes':    '20 01 21',
    'Oil / Hydraulic Fluid':'13 01 10',
}

def parse_calculator_excel(file_bytes):
    """
    Read the Pre Demo Audit Calculator Excel (Sheet1 summary tab).
    Returns list of material dicts and totals.
    """
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(file_bytes), data_only=True)
    ws = wb['Sheet1']
    rows = list(ws.iter_rows(values_only=True))

    materials = []
    for base_row, left_name, right_name in CALC_MATERIAL_MAP:
        val_row = rows[base_row + 2]
        pct_row = rows[base_row + 4]

        left = {
            'name':       left_name,
            'weight_kg':  float(val_row[3] or 0),
            'volume_m3':  float(val_row[5] or 0),
            'weight_pct': round(float(pct_row[3] or 0) * 100, 1),
            'ewc':        EWC_CODES.get(left_name, ''),
        }
        right = {
            'name':       right_name,
            'weight_kg':  float(val_row[9]  or 0),
            'volume_m3':  float(val_row[11] or 0),
            'weight_pct': round(float(pct_row[9] or 0) * 100, 1),
            'ewc':        EWC_CODES.get(right_name, ''),
        }
        materials.append(left)
        materials.append(right)

    total_row = rows[66]
    total_weight_t  = float(total_row[2] or 0)
    total_volume_m3 = float(total_row[8] or 0)

    for m in materials:
        m['weight_t'] = round(m['weight_kg'] / 1000, 3)

    return {
        'materials':       materials,
        'total_weight_t':  round(total_weight_t, 3),
        'total_volume_m3': round(total_volume_m3, 3),
    }

@app.route("/parse-calculator", methods=["POST"])
def parse_calculator():
    f = request.files.get("calculator_file")
    if not f:
        return jsonify({"error": "No file uploaded"}), 400
    try:
        result = parse_calculator_excel(f.read())
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ─────────────────────────────────────────────────────────────
# PPTX — TEXT REPLACEMENT
# ─────────────────────────────────────────────────────────────

def _replace_in_paragraph(para, replacements):
    """
    Merge all runs → single string → replace placeholders → write back.
    Handles cases where PPTX splits {{PLACEHOLDER}} text across multiple runs.
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
    if shape.has_table:
        for row in shape.table.rows:
            for cell in row.cells:
                _replace_in_text_frame(cell.text_frame, replacements)
    if shape.shape_type == 6:  # GROUP
        for s in shape.shapes:
            _replace_in_shape(s, replacements)

# ─────────────────────────────────────────────────────────────
# PPTX — IMAGE REPLACEMENT
# Finds text boxes containing {{KEY}}, replaces with uploaded image
# ─────────────────────────────────────────────────────────────

def _replace_image_placeholders(prs, image_data):
    """
    image_data = { 'PLACEHOLDER_KEY': <bytes> }
    Finds shapes whose text contains {{PLACEHOLDER_KEY}},
    removes the shape, inserts the image at the same position/size.
    """
    for slide in prs.slides:
        to_remove = []
        to_add = []
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            text = shape.text_frame.text.strip()
            for key, img_bytes in image_data.items():
                if f'{{{{{key}}}}}' in text and img_bytes:
                    to_remove.append(shape)
                    to_add.append((shape.left, shape.top, shape.width, shape.height, img_bytes))
                    break
        for shape in to_remove:
            shape._element.getparent().remove(shape._element)
        for left, top, width, height, img_bytes in to_add:
            slide.shapes.add_picture(io.BytesIO(img_bytes), left, top, width, height)

# ─────────────────────────────────────────────────────────────
# PPTX — KWP PIE CHART REPLACEMENT
# ─────────────────────────────────────────────────────────────

def _add_kwp_pie_chart(slide, left, top, width, height, mats, value_key):
    """
    Add a PIE chart to the slide using material names and the specified value column.
    value_key: 'weight_pct', 'weight_t', or 'volume_m3'
    """
    cd = ChartData()
    cd.categories = [m.get('name', '') for m in mats]
    cd.add_series('', [float(m.get(value_key) or 0) for m in mats])
    slide.shapes.add_chart(XL_CHART_TYPE.PIE, left, top, width, height, cd)

def _replace_kwp_chart_placeholders(prs, kwp_materials):
    """
    Replace {{KWP_OF_TOTAL_WEIGHT}}, {{KWP_BY_VOL}}, {{KWP_BY_TON}}
    with native editable PIE charts.
    kwp_materials: list of dicts with name, weight_pct, weight_t, volume_m3
    """
    if not kwp_materials:
        return

    mats = [m for m in kwp_materials if m.get('name')]
    if not mats:
        return

    # Map placeholder → (value_key_in_mat_dict)
    CHART_MAP = {
        'KWP_OF_TOTAL_WEIGHT': 'weight_pct',
        'KWP_BY_VOL':          'volume_m3',
        'KWP_BY_TON':          'weight_t',
    }

    for slide in prs.slides:
        to_remove = []
        to_add = []
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            text = shape.text_frame.text.strip()
            for key, val_col in CHART_MAP.items():
                if f'{{{{{key}}}}}' in text:
                    to_remove.append(shape)
                    to_add.append((shape.left, shape.top, shape.width, shape.height, val_col))
                    break
        for shape in to_remove:
            shape._element.getparent().remove(shape._element)
        for left, top, width, height, val_col in to_add:
            _add_kwp_pie_chart(slide, left, top, width, height, mats, val_col)

# ─────────────────────────────────────────────────────────────
# PPTX — FILL TEMPLATE
# ─────────────────────────────────────────────────────────────

def fill_pptx_template(replacements, image_data=None, kwp_materials=None):
    """Load Savills-3.pptx, replace all placeholders, return BytesIO."""
    prs = Presentation(PPTX_TEMPLATE_PATH)

    # 1. Text replacements
    for slide in prs.slides:
        for shape in slide.shapes:
            _replace_in_shape(shape, replacements)

    # 2. Image replacements
    if image_data:
        _replace_image_placeholders(prs, image_data)

    # 3. KWP pie charts
    if kwp_materials:
        _replace_kwp_chart_placeholders(prs, kwp_materials)

    output = io.BytesIO()
    prs.save(output)
    output.seek(0)
    return output

# ─────────────────────────────────────────────────────────────
# BUILD REPLACEMENTS MAP
# ─────────────────────────────────────────────────────────────

def _first(data, key, default=''):
    """Get first value from flat=False form data dict."""
    vals = data.get(key, [])
    if isinstance(vals, list):
        return vals[0] if vals else default
    return vals if vals else default

def build_replacements(data, report):
    """Map all {{PLACEHOLDER}} keys to form values."""

    def g(key, default=''):
        return _first(data, key, default)

    r = {}

    # ── Slide 1: Cover ────────────────────────────────────────
    r['PROJECT_ADDRESS']  = report.get('job_address', g('job_address'))
    r['CLIENT_NAME']      = report.get('client_name', g('client_name'))
    r['DATE_OF_REPORT']   = g('date_of_report', datetime.now().strftime('%d %B %Y'))
    r['REPORT_NUMBER']    = g('report_number')

    # ── Slide 2: Report Team ──────────────────────────────────
    r['PREPARED_BY']       = g('prepared_by')
    r['PREPARED_BY_ROLE']  = g('prepared_by_role')
    r['PREPARED_DATE']     = g('prepared_date')
    r['AUTHORISED_BY']     = g('authorised_by')
    r['AUTHORISED_BY_ROLE']= g('authorised_by_role')
    r['AUTHORISED_DATE']   = g('authorised_date')

    # ── Slide 4 / 29: KWP summary ────────────────────────────
    r['KEY_WASTE_PRODUCTS'] = g('key_waste_products')
    r['PROJECT_WEIGHT']     = g('project_weight')
    r['LANDFILL_TARGET_PERCENT']  = g('landfill_target_percent', '95')
    r['RECYCLE_TARGET_PERCENT']   = g('recycle_target_percent', '80')
    r['OVERALL_REUSE_PERCENT']    = g('overall_reuse_percent')
    r['BENCHMARK_FOR_RESOURCE_EFFICIENCY'] = g('benchmark_resource_efficiency')

    # ── Narrative text ────────────────────────────────────────
    r['INFORMATION_PROVIDED']         = g('information_provided')
    r['CIRCULAR_ECONOMY_COMMITMENTS'] = g('circular_economy_commitments')

    # ── Materials 1-20 (Reuse section, slides 38-44) ──────────
    for i in range(1, 21):
        n = str(i)
        r[f'MATERIAL_{n}']             = g(f'material_{n}')
        r[f'MATERIAL_{n}_DESCRIPTION'] = g(f'material_{n}_description')
        r[f'MATERIAL_{n}_POTENTIAL']   = g(f'material_{n}_potential')
        r[f'MATERIAL_{n}_RISKS']       = g(f'material_{n}_risks')

    return r

# ─────────────────────────────────────────────────────────────
# IMAGE DATA COLLECTION
# ─────────────────────────────────────────────────────────────

def _read_upload(file_storage):
    """Return raw bytes from an uploaded file, or None if missing."""
    if not file_storage or file_storage.filename == '':
        return None
    return file_storage.read()

def _collect_image_data(files):
    """
    Collect all uploaded images keyed by their PPTX placeholder name.
    Template image placeholders:
      {{PREP_PHOTO}}     → prepared_by_photo
      {{AUTH_PHOTO}}     → authorised_by_photo
      {{BUILDING_PHOTO}} → building_photo
      {{SPEC_1}}-{{SPEC_7}} → spec_photo_1 … spec_photo_7
    """
    images = {}

    for field, key in [
        ('prepared_by_photo',   'PREP_PHOTO'),
        ('authorised_by_photo', 'AUTH_PHOTO'),
        ('building_photo',      'BUILDING_PHOTO'),
    ]:
        img = _read_upload(files.get(field))
        if img:
            images[key] = img

    for i in range(1, 8):
        img = _read_upload(files.get(f'spec_photo_{i}'))
        if img:
            images[f'SPEC_{i}'] = img

    return images

# ─────────────────────────────────────────────────────────────
# KWP MATERIALS FROM FORM
# ─────────────────────────────────────────────────────────────

def _build_kwp_materials(data):
    """
    Build the KWP materials list from parallel form arrays.
    Returns list of dicts with name, weight_t, weight_pct, volume_m3.
    """
    names    = data.get('material_name', [])
    weights  = data.get('weight_tonnes', [])
    volumes  = data.get('volume_m3', [])
    pcts     = data.get('pct_weight', [])

    materials = []
    total_wt = sum(float(w or 0) for w in weights)

    for i, name in enumerate(names):
        if not name:
            continue
        wt = float(weights[i]) if i < len(weights) and weights[i] else 0
        vol = float(volumes[i]) if i < len(volumes) and volumes[i] else 0
        pct = float(pcts[i]) if i < len(pcts) and pcts[i] else (round(wt / total_wt * 100, 1) if total_wt else 0)
        materials.append({
            'name':       name,
            'weight_t':   round(wt, 3),
            'weight_pct': round(pct, 1),
            'volume_m3':  round(vol, 3),
        })
    return materials

# ─────────────────────────────────────────────────────────────
# FORM PROCESSING
# ─────────────────────────────────────────────────────────────

def _process_form_data(data):
    return {
        'job_address': _first(data, 'job_address'),
        'client_name': _first(data, 'client_name'),
    }

# ─────────────────────────────────────────────────────────────
# MAIN REPORT GENERATION ROUTE
# ─────────────────────────────────────────────────────────────

@app.route("/generate-canva-report", methods=["POST"])
def generate_canva_report():
    data  = request.form.to_dict(flat=False)
    files = request.files
    report = _process_form_data(data)

    # Build replacements
    replacements = build_replacements(data, report)

    # Collect images
    image_data = _collect_image_data(files)

    # Build KWP materials for pie charts
    kwp_materials = _build_kwp_materials(data)

    # Auto-fill key_waste_products text if not manually provided
    if not replacements.get('KEY_WASTE_PRODUCTS') and kwp_materials:
        replacements['KEY_WASTE_PRODUCTS'] = ', '.join(m['name'] for m in kwp_materials)

    # Fill the template
    try:
        output = fill_pptx_template(replacements, image_data, kwp_materials)
    except FileNotFoundError:
        return jsonify({"error": (
            f"Template '{PPTX_TEMPLATE_PATH}' not found on server. "
            "Make sure Savills-3.pptx is committed to your repository root."
        )}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Failed to generate report: {str(e)}"}), 500

    addr = report.get('job_address', 'report').replace(' ', '_')[:40]
    filename = f"Audit_{addr}.pptx"
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        as_attachment=True,
        download_name=filename
    )

# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)
