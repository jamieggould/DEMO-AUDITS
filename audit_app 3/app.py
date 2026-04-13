"""
Pre-Demolition Audit Generator
Flask web application — Lawmens brand template
"""
import io
import os
import base64
import traceback
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'lawmens-audit-2024')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/health')
def health():
    return 'OK', 200


@app.route('/generate-ai-text', methods=['POST'])
def generate_ai_text_endpoint():
    from ai_generator import (
        generate_executive_summary, generate_conclusion,
        generate_introduction, generate_material_recommendation,
    )

    payload = request.get_json(force=True)
    api_key = payload.get('api_key') or os.environ.get('ANTHROPIC_API_KEY')
    section = payload.get('section')
    report_data = payload.get('report_data', {})

    if not api_key:
        return jsonify({'error': 'No API key provided.'}), 400

    try:
        if section == 'executive_summary':
            text = generate_executive_summary(report_data, api_key)
        elif section == 'conclusion':
            text = generate_conclusion(report_data, api_key)
        elif section == 'introduction':
            text = generate_introduction(report_data, api_key)
        elif section == 'material_recommendation':
            text = generate_material_recommendation(
                report_data.get('material_name', ''),
                float(report_data.get('weight_tonnes', 0)),
                report_data.get('reuse_potential', 'Medium'),
                api_key,
            )
        else:
            return jsonify({'error': f'Unknown section: {section}'}), 400

        return jsonify({'text': text})

    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    try:
        from weasyprint import HTML as WeasyprintHTML
        from chart_generator import (
            generate_waste_diversion_chart,
            generate_kwp_charts,
            generate_carbon_bar_chart,
        )
        from ai_generator import (
            generate_executive_summary, generate_conclusion, generate_introduction,
        )

        data = request.form.to_dict(flat=False)
        files = request.files

        report_data = _process_form_data(data, files)

        # AI text generation
        api_key = _first(data, 'api_key') or os.environ.get('ANTHROPIC_API_KEY')
        use_ai = _first(data, 'use_ai', 'false').lower() == 'true' and bool(api_key)

        if use_ai:
            try:
                report_data['executive_summary'] = generate_executive_summary(report_data, api_key)
                report_data['conclusion_text'] = generate_conclusion(report_data, api_key)
                report_data['introduction_text'] = generate_introduction(report_data, api_key)
            except Exception:
                pass  # Fall back to manual text

        if not report_data.get('executive_summary'):
            report_data['executive_summary'] = _first(data, 'executive_summary')
        if not report_data.get('conclusion_text'):
            report_data['conclusion_text'] = _first(data, 'conclusion_text')
        if not report_data.get('introduction_text'):
            report_data['introduction_text'] = _first(data, 'introduction_text')

        # Charts
        report_data['waste_diversion_chart'] = generate_waste_diversion_chart(
            report_data.get('kwp_materials', [])
        )
        kwp_charts = generate_kwp_charts(report_data.get('kwp_materials', []))
        report_data['kwp_chart_volume'] = kwp_charts.get('volume', '')
        report_data['kwp_chart_weight'] = kwp_charts.get('weight', '')
        report_data['carbon_bar_chart'] = generate_carbon_bar_chart(
            report_data.get('kwp_materials', [])
        )

        # Render HTML template
        html_string = render_template('report.html', data=report_data)

        # Convert to PDF
        pdf_bytes = WeasyprintHTML(string=html_string).write_pdf()

        report_number = report_data.get('report_number', 'DRAFT')
        filename = f"Pre-Demolition-Audit-{report_number}.pdf"

        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename,
        )

    except Exception:
        error_detail = traceback.format_exc()
        print("PDF GENERATION ERROR:\n", error_detail)
        return f"""
        <html><body style="font-family:sans-serif;padding:40px;max-width:700px;">
        <h2 style="color:#c0392b;">PDF Generation Failed</h2>
        <p>Something went wrong generating the PDF. The error has been logged.</p>
        <pre style="background:#f5f5f5;padding:16px;border-radius:6px;font-size:12px;overflow:auto;">{error_detail}</pre>
        <a href="/" style="color:#0d4f6c;">← Go back</a>
        </body></html>
        """, 500


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _first(data, key, default=''):
    """Get first value for a key from a flat=False form dict."""
    vals = data.get(key, [])
    return vals[0] if vals else default


def _encode_upload(file_storage) -> str:
    """Base64-encode an uploaded file for embedding in HTML."""
    if not file_storage or not file_storage.filename:
        return ''
    raw = file_storage.read()
    if not raw:
        return ''
    ext = file_storage.filename.rsplit('.', 1)[-1].lower()
    mime = {
        'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
        'png': 'image/png', 'gif': 'image/gif',
        'webp': 'image/webp',
    }.get(ext, 'image/jpeg')
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"


def _safe_float(val, default=0.0):
    try:
        return float(str(val).replace(',', '').strip())
    except (TypeError, ValueError):
        return default


def _process_form_data(data: dict, files) -> dict:
    report_data = {
        'report_title':           _first(data, 'report_title', 'Pre-Demolition Audit'),
        'job_address':            _first(data, 'job_address'),
        'client_name':            _first(data, 'client_name'),
        'report_number':          _first(data, 'report_number'),
        'report_date':            _first(data, 'report_date', datetime.now().strftime('%B %Y')),
        'building_type':          _first(data, 'building_type'),
        'building_description':   _first(data, 'building_description'),
        'total_gia':              _first(data, 'total_gia'),
        'year_built':             _first(data, 'year_built'),
        'num_storeys':            _first(data, 'num_storeys'),
        'planning_ref':           _first(data, 'planning_ref'),
        'prepared_by_name':       _first(data, 'prepared_by_name'),
        'prepared_by_position':   _first(data, 'prepared_by_position'),
        'prepared_by_date':       _first(data, 'prepared_by_date'),
        'authorised_by_name':     _first(data, 'authorised_by_name'),
        'authorised_by_position': _first(data, 'authorised_by_position'),
        'authorised_by_date':     _first(data, 'authorised_by_date'),
        'executive_summary':      '',
        'conclusion_text':        '',
        'introduction_text':      '',
        'total_weight':           0.0,
        'total_volume':           0.0,
        'total_carbon':           0.0,
        'floor_plans':            [],
        'kwp_materials':          [],
        'reuse_items':            [],
        'building_photo':         '',
        'prepared_by_photo':      '',
        'authorised_by_photo':    '',
    }

    # Photos
    for field in ('building_photo', 'prepared_by_photo', 'authorised_by_photo'):
        f = files.get(field)
        if f:
            report_data[field] = _encode_upload(f)

    # Floor plans
    fp_files = files.getlist('floor_plan_images')
    fp_names = data.get('floor_plan_names', [])
    for i, fp in enumerate(fp_files):
        encoded = _encode_upload(fp)
        if encoded:
            name = fp_names[i] if i < len(fp_names) else f'Floor {i + 1}'
            report_data['floor_plans'].append({'image': encoded, 'name': name})

    # KWP materials
    mat_names = data.get('material_name', [])
    for i in range(len(mat_names)):
        name = mat_names[i].strip()
        if not name:
            continue

        def gv(key, idx=i):
            vals = data.get(key, [])
            return vals[idx] if idx < len(vals) else ''

        weight  = _safe_float(gv('weight_tonnes'))
        volume  = _safe_float(gv('volume_m3'))
        carbon  = _safe_float(gv('embodied_carbon'))
        reuse   = _safe_float(gv('reuse_pct'))
        recycle = _safe_float(gv('recycling_pct'))
        landfill = _safe_float(gv('landfill_pct'))

        material = {
            'name':            name,
            'ewc_code':        gv('ewc_code'),
            'volume_m3':       volume,
            'weight_tonnes':   weight,
            'pct_weight':      _safe_float(gv('pct_weight')),
            'carbon_factor':   gv('carbon_factor'),
            'source':          gv('material_source'),
            'embodied_carbon': carbon,
            'reuse_pct':       reuse,
            'recycling_pct':   recycle,
            'landfill_pct':    landfill,
            'recommendation':  gv('material_recommendation'),
        }
        report_data['kwp_materials'].append(material)
        report_data['total_weight'] += weight
        report_data['total_volume'] += volume
        report_data['total_carbon'] += carbon

    # Auto-fill % by weight if blank
    total_w = report_data['total_weight']
    for m in report_data['kwp_materials']:
        if m['pct_weight'] == 0 and total_w > 0:
            m['pct_weight'] = round(m['weight_tonnes'] / total_w * 100, 1)

    # Material reuse items
    reuse_names = data.get('reuse_name', [])
    for i, rname in enumerate(reuse_names):
        rname = rname.strip()
        if not rname:
            continue

        def rv(key, idx=i):
            vals = data.get(key, [])
            return vals[idx] if idx < len(vals) else ''

        item = {
            'name':            rname,
            'reuse_potential': rv('reuse_potential') or 'Medium',
            'description':     rv('reuse_description'),
            'risk_factors':    rv('reuse_risk_factors'),
            'photos':          [],
        }
        for pf in files.getlist(f'reuse_photos_{i}'):
            encoded = _encode_upload(pf)
            if encoded:
                item['photos'].append(encoded)

        report_data['reuse_items'].append(item)

    return report_data


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n  Audit Generator running at  http://127.0.0.1:{port}\n")
    app.run(debug=False, host='0.0.0.0', port=port)
