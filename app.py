"""
Lawmens Pre-Demolition Audit Generator — Flask backend
Template: Savills-6.pptx
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

OPENAI_API_KEY    = os.environ.get("OPENAI_API_KEY")
PPTX_TEMPLATE_PATH = os.environ.get("PPTX_TEMPLATE_PATH", "Savills-6.pptx")

# ─────────────────────────────────────────────────────────────
# DEFAULT TEXT FOR EACH MATERIAL TYPE
# Used to pre-fill descriptions / recommendations / risks
# when the user hasn't entered them manually.
# ─────────────────────────────────────────────────────────────
MATERIAL_DEFAULTS = {
    'Carpet': {
        'description':  'Carpet tiles and broadloom carpet removed during strip-out operations. Condition varies by area of use and age.',
        'waste_rec':    'Carpet tiles in good condition to be salvaged and offered for reuse via material exchange platforms. Worn or contaminated carpet to be segregated for textile recycling.',
        'risks':        'Adhesive residue on backing may limit reuse options. Market demand for second-hand carpet tiles is condition-dependent. Some older carpets may contain harmful fibres.',
        'potential':    'Medium',
        'ewc':          '20 03 01',
    },
    'Timber': {
        'description':  'Structural and non-structural timber elements including studwork, boarding, door frames, and secondary steelwork.',
        'waste_rec':    'Good-quality structural timber to be carefully dismantled and offered for reuse or sold through salvage merchants. Painted or contaminated timber to be segregated for biomass energy recovery.',
        'risks':        'Older timber may carry lead-based paint. Fixings and nails require removal before reuse. Moisture damage may reduce structural reuse potential.',
        'potential':    'High',
        'ewc':          '17 02 01',
    },
    'Plasterboard': {
        'description':  'Gypsum plasterboard lining, partitions, and ceilings. Includes standard, moisture-resistant, and fire-rated boards.',
        'waste_rec':    'Clean plasterboard to be segregated and sent to a licensed plasterboard recycler for closed-loop gypsum recovery. Must be kept dry and free from contamination.',
        'risks':        'Contamination with paint, adhesives, or other materials can prevent recycling. Older boards may contain fibres. Care required during removal to maximise clean yield.',
        'potential':    'Low',
        'ewc':          '17 08 02',
    },
    'Glass': {
        'description':  'Glazing units, partition screens, mirrors, and internal glazed doors removed during strip-out.',
        'waste_rec':    'Intact glass panels and screens to be carefully removed and offered for reuse. Broken or laminated glass to be segregated for glass recycling.',
        'risks':        'Safety hazard during removal. Laminated or coated glass may not be recyclable through standard routes. Transport and storage require specialist handling.',
        'potential':    'Medium',
        'ewc':          '17 02 02',
    },
    'Metal': {
        'description':  'Structural and non-structural metal including raised access floor systems, suspended ceiling grid, pipework, ductwork, and fixings.',
        'waste_rec':    'All scrap metal to be segregated by type (ferrous/non-ferrous) and sent to a licenced metal recycler. Raised access floor panels in good condition to be offered for reuse.',
        'risks':        'Mixed metal streams attract lower recycling value. Sharp edges and hazardous fixings require PPE during handling. Some items may contain asbestos-based coatings.',
        'potential':    'High',
        'ewc':          '17 04 05',
    },
    'Hardcore': {
        'description':  'Masonry, concrete, tiles, and ceramic materials arising from internal demolition works.',
        'waste_rec':    'Clean hardcore to be crushed and recycled as secondary aggregate on-site or off-site. Ceramic tiles in good condition to be offered for reuse.',
        'risks':        'Contamination with adhesives or other materials reduces recycling value. Composite tiles (e.g. vinyl-backed ceramic) may require separation.',
        'potential':    'Low',
        'ewc':          '17 01 01',
    },
    'Insulation': {
        'description':  'Thermal and acoustic insulation materials including mineral wool, rigid foam boards, and pipe insulation.',
        'waste_rec':    'Clean rigid insulation boards in good condition to be offered for reuse. Mineral wool and contaminated insulation to be bagged and sent to specialist recycler.',
        'risks':        'Fibrous insulation materials require PPE and may trigger respiratory hazards. Some older foam insulation may contain ozone-depleting substances (ODS) — specialist contractor required.',
        'potential':    'Low',
        'ewc':          '17 06 04',
    },
    'Fibre Ceiling Tiles': {
        'description':  'Suspended mineral fibre and acoustic ceiling tiles from suspended grid systems.',
        'waste_rec':    'Undamaged tiles to be carefully removed and palletised for reuse or donation. Damaged tiles to be sent to a specialist ceiling tile recycler.',
        'risks':        'Fragile — breakage rate during removal typically 15–30%. Staining or moisture damage significantly reduces reuse potential.',
        'potential':    'Medium',
        'ewc':          '17 06 05',
    },
    'Plastic': {
        'description':  'Mixed plastic components including conduit, cable management, switch plates, signage, and fittings.',
        'waste_rec':    'Segregate by plastic type where possible (ABS, PVC, PP) for specialist plastic recycling. Large plastic items in good condition to be offered for reuse.',
        'risks':        'Mixed plastic streams have low recycling value. PVC materials require specialist handling. Some plastics may contain hazardous additives.',
        'potential':    'Low',
        'ewc':          '17 02 03',
    },
    'Vinyl': {
        'description':  'Vinyl sheet flooring and vinyl floor tiles removed during strip-out.',
        'waste_rec':    'Vinyl flooring to be rolled and offered for reuse where condition permits. Worn or damaged vinyl to be sent to a vinyl flooring recycler.',
        'risks':        'Adhesive backing may contain hazardous substances in older installations. Some older vinyl tiles may contain asbestos — survey required before removal.',
        'potential':    'Medium',
        'ewc':          '20 01 39',
    },
    'Rubber': {
        'description':  'Rubber flooring, anti-vibration mounts, and door seals removed during strip-out.',
        'waste_rec':    'Rubber flooring in good condition to be offered for reuse in sports or industrial applications. Waste rubber to be sent to a specialist rubber recycler for crumb production.',
        'risks':        'Adhesive-bonded rubber is difficult to remove cleanly. Synthetic rubber may contain hazardous chemicals limiting disposal routes.',
        'potential':    'Medium',
        'ewc':          '16 01 03',
    },
    'Fabric': {
        'description':  'Textile materials including window blinds, curtains, upholstered furniture fabric, and acoustic panels.',
        'waste_rec':    'Clean fabric items in good condition to be donated to charity or offered for reuse. Contaminated or worn fabrics to be sent for textile recycling.',
        'risks':        'Fire-retardant treatments may contain hazardous chemicals. Heavily soiled or stained items unlikely to be suitable for reuse.',
        'potential':    'Low',
        'ewc':          '20 01 10',
    },
    'Fluorescent Tubes': {
        'description':  'Linear fluorescent lamps and compact fluorescent light fittings removed during de-fit.',
        'waste_rec':    'All fluorescent lamps to be collected by a licensed waste electrical and electronic equipment (WEEE) contractor for specialist mercury recycling.',
        'risks':        'Fluorescent tubes contain mercury — a hazardous substance. Breakage creates a mercury vapour hazard. Must not be disposed of in general waste.',
        'potential':    'Low',
        'ewc':          '20 01 21',
    },
    'Oil / Hydraulic Fluid': {
        'description':  'Hydraulic oils and lubricants from mechanical plant, lifts, and building services equipment.',
        'waste_rec':    'Waste oils to be collected and stored in sealed containers by a licensed waste oil contractor for re-refining or energy recovery.',
        'risks':        'Classified as hazardous waste. Spillage risk during removal and storage. Requires licensed contractor and appropriate manifests.',
        'potential':    'Low',
        'ewc':          '13 01 10',
    },
}

EWC_CODES = {k: v['ewc'] for k, v in MATERIAL_DEFAULTS.items()}

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

def openai_generate(prompt, fallback=""):
    """Generate text via OpenAI. Returns fallback on any failure."""
    if not OPENAI_API_KEY:
        return fallback
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
        return fallback

@app.route("/generate-ai-text", methods=["POST"])
def generate_ai_text():
    data    = request.get_json()
    section = data.get("section")
    report  = data.get("report_data", {})
    addr    = report.get("job_address", "the site")
    client  = report.get("client_name", "the client")
    mats    = report.get("kwp_materials", [])
    mat_str = ", ".join(m.get("name","") for m in mats if m.get("name"))

    prompts = {
        "executive_summary": (
            f"Write a professional executive summary (3–4 paragraphs) for a pre-demolition/refurbishment "
            f"audit at {addr} for client {client}. "
            f"Key waste products identified: {mat_str}. "
            f"Focus on circular economy, waste diversion, and sustainability."
        ),
        "conclusion": (
            f"Write a professional conclusion and recommendations section (2–3 paragraphs) for a "
            f"pre-demolition audit at {addr}. "
            f"Materials: {mat_str}. Recommend targets for reuse, recycling, and landfill diversion."
        ),
        "circular_economy": (
            f"Write 2–3 sentences describing exemplary circular economy commitments for a "
            f"construction project at {addr}. Mention material reuse, recycling targets, and GLA benchmarks."
        ),
        "information_provided": (
            f"Write a bullet-point list of the types of information and documents typically provided "
            f"for a pre-demolition audit at {addr}. Include drawings, surveys, and reports."
        ),
        "benchmark": (
            f"Write one sentence describing the resource efficiency benchmark being adopted for "
            f"the project at {addr}, referencing GLA Whole Life Carbon benchmarks."
        ),
    }

    if section not in prompts:
        return jsonify({"error": "Unknown section"}), 400

    text = openai_generate(prompts[section])
    if not text:
        return jsonify({"error": "AI generation failed. Check OPENAI_API_KEY is set."}), 500
    return jsonify({"text": text})

@app.route("/generate-material-text", methods=["POST"])
def generate_material_text():
    """Generate description/recommendation/risks for a single material."""
    data     = request.get_json()
    mat_name = data.get("material_name", "")
    field    = data.get("field", "description")

    # Use defaults if available
    defaults = MATERIAL_DEFAULTS.get(mat_name, {})

    field_map = {
        "description": "waste_rec",  # overlap intentional
        "waste_rec":   "waste_rec",
        "risks":       "risks",
    }
    if mat_name in MATERIAL_DEFAULTS and field in MATERIAL_DEFAULTS[mat_name]:
        return jsonify({"text": MATERIAL_DEFAULTS[mat_name][field]})

    # Fall back to AI
    prompts = {
        "description":  f"Write 1–2 sentences describing {mat_name} as a waste material in a pre-demolition audit context.",
        "waste_rec":    f"Write 1–2 sentences with waste management recommendations for {mat_name} in a demolition project.",
        "risks":        f"Write 1–2 sentences describing the key risk factors for reusing or recycling {mat_name} from a demolition project.",
    }
    prompt = prompts.get(field, prompts["description"])
    text = openai_generate(prompt, fallback=f"See survey findings for {mat_name}.")
    return jsonify({"text": text})

# ─────────────────────────────────────────────────────────────
# EWC LOOKUP
# ─────────────────────────────────────────────────────────────

@app.route("/ewc-lookup", methods=["POST"])
def ewc_lookup():
    name = request.get_json().get("name", "")
    ewc  = EWC_CODES.get(name, "")
    defaults = MATERIAL_DEFAULTS.get(name, {})
    return jsonify({
        "ewc":         ewc,
        "description": defaults.get("description", ""),
        "waste_rec":   defaults.get("waste_rec", ""),
        "risks":       defaults.get("risks", ""),
        "potential":   defaults.get("potential", "Medium"),
    })

# ─────────────────────────────────────────────────────────────
# EXCEL CALCULATOR PARSER
# ─────────────────────────────────────────────────────────────

CALC_MATERIAL_MAP = [
    (20, 'Carpet',            'Timber'),
    (26, 'Plasterboard',      'Glass'),
    (32, 'Metal',             'Hardcore'),
    (38, 'Insulation',        'Fibre Ceiling Tiles'),
    (44, 'Plastic',           'Vinyl'),
    (50, 'Rubber',            'Fabric'),
    (56, 'Fluorescent Tubes', 'Oil / Hydraulic Fluid'),
]

def parse_calculator_excel(file_bytes):
    from openpyxl import load_workbook
    wb  = load_workbook(io.BytesIO(file_bytes), data_only=True)
    ws  = wb['Sheet1']
    rows = list(ws.iter_rows(values_only=True))

    materials = []
    for base_row, left_name, right_name in CALC_MATERIAL_MAP:
        val_row = rows[base_row + 2]
        pct_row = rows[base_row + 4]
        for name, wt_col, vol_col, pct_col in [
            (left_name,  3, 5, 3),
            (right_name, 9, 11, 9),
        ]:
            materials.append({
                'name':       name,
                'weight_kg':  float(val_row[wt_col]  or 0),
                'volume_m3':  float(val_row[vol_col] or 0),
                'weight_pct': round(float(pct_row[pct_col] or 0) * 100, 1),
                'ewc':        EWC_CODES.get(name, ''),
                'weight_t':   round(float(val_row[wt_col] or 0) / 1000, 3),
            })

    total_row = rows[66]
    return {
        'materials':       materials,
        'total_weight_t':  round(float(total_row[2] or 0), 3),
        'total_volume_m3': round(float(total_row[8] or 0), 3),
    }

@app.route("/parse-calculator", methods=["POST"])
def parse_calculator():
    f = request.files.get("calculator_file")
    if not f:
        return jsonify({"error": "No file uploaded"}), 400
    try:
        return jsonify(parse_calculator_excel(f.read()))
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ─────────────────────────────────────────────────────────────
# PPTX — TEXT REPLACEMENT (handles text boxes AND table cells)
# ─────────────────────────────────────────────────────────────

def _replace_in_paragraph(para, replacements):
    """
    Merge all runs in a paragraph, replace {{KEY}} tokens, write back.
    Handles the common PPTX split-run problem.
    """
    if not para.runs:
        return
    full = ''.join(r.text for r in para.runs)
    new  = full
    for key, val in replacements.items():
        new = new.replace(f'{{{{{key}}}}}', str(val) if val is not None else '')
    if new != full:
        para.runs[0].text = new
        for r in para.runs[1:]:
            r.text = ''

def _replace_in_text_frame(tf, replacements):
    for para in tf.paragraphs:
        _replace_in_paragraph(para, replacements)

def _replace_in_shape(shape, replacements):
    """Replace in text frames, table cells, and grouped shapes."""
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
# Supports multiple photos per placeholder key (e.g. MAT_N_PHOTOS)
# ─────────────────────────────────────────────────────────────

def _replace_image_placeholders(prs, image_data):
    """
    image_data = { 'KEY': bytes }                  — single image
               = { 'KEY': [bytes, bytes, ...] }    — multiple (e.g. MAT_N_PHOTOS)

    When a key appears multiple times on a slide, the first occurrence
    gets photos[0], the second gets photos[1], etc.
    """
    # Normalise to lists
    img_map = {}
    for key, val in image_data.items():
        img_map[key] = [val] if isinstance(val, (bytes, bytearray)) else list(val)

    for slide in prs.slides:
        to_remove  = []
        to_add     = []
        key_usage  = {}

        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            text = shape.text_frame.text.strip()
            for key, photos in img_map.items():
                if f'{{{{{key}}}}}' in text and photos:
                    usage = key_usage.get(key, 0)
                    idx   = min(usage, len(photos) - 1)
                    to_remove.append(shape)
                    to_add.append((shape.left, shape.top, shape.width, shape.height, photos[idx]))
                    key_usage[key] = usage + 1
                    break

        for shape in to_remove:
            shape._element.getparent().remove(shape._element)
        for left, top, w, h, img_bytes in to_add:
            slide.shapes.add_picture(io.BytesIO(img_bytes), left, top, w, h)

# ─────────────────────────────────────────────────────────────
# PPTX — KWP PIE CHART REPLACEMENT
# ─────────────────────────────────────────────────────────────

def _add_kwp_pie_chart(slide, left, top, width, height, mats, value_key):
    """Add a labelled PIE chart. Filters zero-value slices."""
    from pptx.enum.chart import XL_LABEL_POSITION

    visible = [m for m in mats if float(m.get(value_key) or 0) > 0] or mats
    cd = ChartData()
    cd.categories = [m.get('name', '') for m in visible]
    cd.add_series('', [float(m.get(value_key) or 0) for m in visible])

    gf    = slide.shapes.add_chart(XL_CHART_TYPE.PIE, left, top, width, height, cd)
    chart = gf.chart

    plot = chart.plots[0]
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.show_category_name = True
    dl.show_percentage    = True
    dl.show_value         = False
    dl.show_series_name   = False
    dl.show_legend_key    = False

    chart.has_legend = True
    chart.legend.include_in_layout = False

def _replace_kwp_chart_placeholders(prs, kwp_materials):
    if not kwp_materials:
        return
    mats = [m for m in kwp_materials if m.get('name')]
    if not mats:
        return

    CHART_MAP = {
        'KWP_OF_TOTAL_WEIGHT': 'weight_pct',
        'KWP_BY_VOL':          'volume_m3',
        'KWP_BY_TON':          'weight_t',
    }
    for slide in prs.slides:
        to_remove, to_add = [], []
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
        for left, top, w, h, val_col in to_add:
            _add_kwp_pie_chart(slide, left, top, w, h, mats, val_col)

# ─────────────────────────────────────────────────────────────
# FILL TEMPLATE
# ─────────────────────────────────────────────────────────────

def fill_pptx_template(replacements, image_data=None, kwp_materials=None):
    prs = Presentation(PPTX_TEMPLATE_PATH)
    for slide in prs.slides:
        for shape in slide.shapes:
            _replace_in_shape(shape, replacements)
    if image_data:
        _replace_image_placeholders(prs, image_data)
    if kwp_materials:
        _replace_kwp_chart_placeholders(prs, kwp_materials)
    out = io.BytesIO()
    prs.save(out)
    out.seek(0)
    return out

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _first(data, key, default=''):
    vals = data.get(key, [])
    if isinstance(vals, list):
        return vals[0] if vals else default
    return vals if vals else default

def _read_upload(fs):
    if not fs or fs.filename == '':
        return None
    return fs.read()

# ─────────────────────────────────────────────────────────────
# BUILD REPLACEMENTS
# Maps every {{PLACEHOLDER}} in Savills-6.pptx to a form value
# ─────────────────────────────────────────────────────────────

def build_replacements(data, mat_list):
    """
    mat_list: list of dicts (one per material, index 0 = material 1) with keys:
      name, ewc, vol, weigh, weighp, ecf, carb, reuse, ewc_key,
      waste_rec, desc, potential, risks
    """
    def g(k, d=''):
        return _first(data, k, d)

    r = {}

    # ── Cover / global ────────────────────────────────────────
    r['PROJECT_ADDRESS']  = g('job_address')
    r['CLIENT_NAME']      = g('client_name')
    r['DATE_OF_REPORT']   = g('date_of_report', datetime.now().strftime('%d %B %Y'))
    r['REPORT_NUMBER']    = g('report_number')

    # ── Team ──────────────────────────────────────────────────
    r['PREPARED_BY']       = g('prepared_by')
    r['PREPARED_BY_ROLE']  = g('prepared_by_role')
    r['PREPARED_DATE']     = g('prepared_date')
    r['AUTHORISED_BY']     = g('authorised_by')
    r['AUTHORISED_BY_ROLE']= g('authorised_by_role')
    r['AUTHORISED_DATE']   = g('authorised_date')

    # ── Report narrative ──────────────────────────────────────
    r['CIRCULAR_ECONOMY_COMMITMENTS']      = g('circular_economy_commitments')
    r['BENCHMARK_FOR_RESOURCE_EFFICIENCY'] = g('benchmark_resource_efficiency')
    r['INFORMATION_PROVIDED']              = g('information_provided')
    r['KEY_WASTE_PRODUCTS']                = g('key_waste_products')
    r['PROJECT_WEIGHT']                    = g('project_weight')
    r['OVERALL_REUSE_PERCENT']             = g('overall_reuse_percent')
    r['LANDFILL_TARGET_PERCENT']           = g('landfill_target_percent', '95')
    r['RECYCLE_TARGET_PERCENT']            = g('recycle_target_percent', '80')

    # ── Materials 1–20 ────────────────────────────────────────
    # Template uses two different EWC naming schemes:
    #   Slide 27 (rows 1-10): MATERIAL_EWC_N
    #   Slide 28 (rows 11-20): MATERIAL_N_EWC
    #   Detail slides:         MAT_N_EWC
    # We populate all three variants for each material.
    for i, m in enumerate(mat_list[:20], start=1):
        n  = str(i)
        ns = n  # string index

        name    = m.get('name',     '')
        ewc     = m.get('ewc',      '')
        vol     = m.get('vol',      '')
        weigh   = m.get('weigh',    '')
        weighp  = m.get('weighp',   '')
        ecf     = m.get('ecf',      '')
        carb    = m.get('carb',     '')
        reuse   = m.get('reuse',    '')
        waste_r = m.get('waste_rec','')
        desc    = m.get('desc',     '')
        pot     = m.get('potential','Medium')
        risks   = m.get('risks',    '')

        # Name — template has both MATERIAL_N and 'MATERIAL 10' (space) for row 10
        r[f'MATERIAL_{n}']    = name
        if i == 10:
            r['MATERIAL 10']  = name   # space-variant in template

        # EWC — three naming patterns
        r[f'MATERIAL_EWC_{n}'] = ewc   # slide 27 style
        r[f'MATERIAL_{n}_EWC'] = ewc   # slide 28 style
        r[f'MAT_{n}_EWC']      = ewc   # detail slide style

        # Numeric data
        r[f'MAT_{n}_VOL']    = vol
        r[f'MAT_{n}_WEIGH']  = weigh
        r[f'MAT_{n}_WEIGHP'] = weighp
        r[f'MAT_{n}_ECF']    = ecf
        r[f'MAT_{n}_CARB']   = carb
        r[f'MAT_{n}_REUSE']  = reuse

        # Text content
        r[f'MAT_{n}_WASTE_RECOMMENDATIONS'] = waste_r
        r[f'MATERIAL_{n}_DESCRIPTION']      = desc
        r[f'MATERIAL_{n}_POTENTIAL']        = pot
        r[f'MATERIAL_{n}_RISKS']            = risks

    # Blank out any unfilled material slots (21+ won't exist but 1-20 that are empty)
    for i in range(len(mat_list) + 1, 21):
        n = str(i)
        for key in [
            f'MATERIAL_{n}', f'MATERIAL_EWC_{n}', f'MATERIAL_{n}_EWC', f'MAT_{n}_EWC',
            f'MAT_{n}_VOL', f'MAT_{n}_WEIGH', f'MAT_{n}_WEIGHP', f'MAT_{n}_ECF',
            f'MAT_{n}_CARB', f'MAT_{n}_REUSE', f'MAT_{n}_WASTE_RECOMMENDATIONS',
            f'MATERIAL_{n}_DESCRIPTION', f'MATERIAL_{n}_POTENTIAL', f'MATERIAL_{n}_RISKS',
        ]:
            r[key] = ''
        if i == 10:
            r['MATERIAL 10'] = ''
    # Also handle MATERIAL_16 missing col0 edge case in template
    if 'MATERIAL_16' not in r:
        r['MATERIAL_16'] = ''

    return r

# ─────────────────────────────────────────────────────────────
# COLLECT IMAGES
# ─────────────────────────────────────────────────────────────

def _collect_image_data(files, mat_count):
    """
    Single images:  PREP_PHOTO, AUTH_PHOTO, BUILDING_PHOTO
    Spec images:    SPEC_1 … SPEC_7
    Material photos: MAT_N_PHOTOS → [photo1, photo2] per material
    """
    images = {}

    for field, key in [
        ('prepared_by_photo',   'PREP_PHOTO'),
        ('authorised_by_photo', 'AUTH_PHOTO'),
        ('building_photo',      'BUILDING_PHOTO'),
    ]:
        b = _read_upload(files.get(field))
        if b:
            images[key] = b

    for i in range(1, 8):
        b = _read_upload(files.get(f'spec_photo_{i}'))
        if b:
            images[f'SPEC_{i}'] = b

    for i in range(1, mat_count + 1):
        photos = []
        for j in (1, 2):
            b = _read_upload(files.get(f'mat_{i}_photo_{j}'))
            if b:
                photos.append(b)
        if photos:
            images[f'MAT_{i}_PHOTOS'] = photos

    return images

# ─────────────────────────────────────────────────────────────
# BUILD KWP MATERIAL LIST FROM FORM
# ─────────────────────────────────────────────────────────────

def _build_mat_list(data):
    """
    Read mat_N_* fields from form data into a list of dicts.
    Skips entries where name is blank.
    Calculates carbon and weight% if missing.
    """
    mat_list  = []
    total_wt  = 0.0

    # First pass — collect and compute total weight
    raw = []
    for i in range(1, 21):
        n    = str(i)
        name = _first(data, f'mat_{n}_name')
        if not name:
            continue
        wt   = float(_first(data, f'mat_{n}_weigh', '0') or 0)
        total_wt += wt
        raw.append((i, name, wt))

    # Second pass — build full dicts with auto-calculated fields
    for i, name, wt in raw:
        n      = str(i)
        ecf    = float(_first(data, f'mat_{n}_ecf', '0') or 0)
        carb   = _first(data, f'mat_{n}_carb')
        weighp = _first(data, f'mat_{n}_weighp')

        if not carb and ecf and wt:
            carb = str(round(ecf * wt, 2))
        if not weighp and total_wt:
            weighp = str(round(wt / total_wt * 100, 1))

        # Auto-fill text from defaults if blank
        defaults = MATERIAL_DEFAULTS.get(name, {})
        mat_list.append({
            'name':     name,
            'ewc':      _first(data, f'mat_{n}_ewc')  or defaults.get('ewc', ''),
            'vol':      _first(data, f'mat_{n}_vol',   ''),
            'weigh':    str(wt) if wt else '',
            'weighp':   weighp,
            'ecf':      _first(data, f'mat_{n}_ecf',   ''),
            'carb':     carb or '',
            'reuse':    _first(data, f'mat_{n}_reuse',  ''),
            'waste_rec': _first(data, f'mat_{n}_waste_rec') or defaults.get('waste_rec', ''),
            'desc':     _first(data, f'mat_{n}_desc')      or defaults.get('description', ''),
            'potential': _first(data, f'mat_{n}_potential') or defaults.get('potential', 'Medium'),
            'risks':    _first(data, f'mat_{n}_risks')      or defaults.get('risks', ''),
        })

    return mat_list, total_wt

# ─────────────────────────────────────────────────────────────
# MAIN REPORT GENERATION ROUTE
# ─────────────────────────────────────────────────────────────

@app.route("/generate-canva-report", methods=["POST"])
def generate_canva_report():
    data  = request.form.to_dict(flat=False)
    files = request.files

    mat_list, total_wt = _build_mat_list(data)

    # Auto-build KEY_WASTE_PRODUCTS if not manually set
    kwp_text = _first(data, 'key_waste_products')
    if not kwp_text and mat_list:
        kwp_text = ', '.join(m['name'] for m in mat_list)

    # Inject into data for build_replacements
    if kwp_text:
        data['key_waste_products'] = [kwp_text]
    if total_wt and not _first(data, 'project_weight'):
        data['project_weight'] = [f"{total_wt:.2f} tonnes"]

    replacements  = build_replacements(data, mat_list)
    image_data    = _collect_image_data(files, len(mat_list))

    # KWP pie chart data
    kwp_mats = [{
        'name':       m['name'],
        'weight_t':   float(m['weigh'] or 0),
        'weight_pct': float(m['weighp'] or 0),
        'volume_m3':  float(m['vol']   or 0),
    } for m in mat_list]

    try:
        output = fill_pptx_template(replacements, image_data, kwp_mats)
    except FileNotFoundError:
        return jsonify({"error": (
            f"Template '{PPTX_TEMPLATE_PATH}' not found. "
            "Ensure Savills-6.pptx is committed to your repository root."
        )}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Failed to generate report: {str(e)}"}), 500

    addr     = _first(data, 'job_address').replace(' ', '_')[:40]
    filename = f"Audit_{addr}.pptx"
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        as_attachment=True,
        download_name=filename,
    )

# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)
