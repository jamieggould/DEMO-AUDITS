"""
AI text generation for Pre-Demolition Audit reports.
Uses the Anthropic API (claude-haiku-4-5) for fast, low-cost generation.
"""
import anthropic


def _call_claude(api_key: str, prompt: str, max_tokens: int = 600) -> str:
    """Shared helper to call the Anthropic API."""
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def _kwp_summary(kwp_materials: list) -> str:
    lines = []
    for m in kwp_materials:
        lines.append(
            f"  - {m.get('name', 'Unknown')}: {m.get('weight_tonnes', 0)} tonnes "
            f"({m.get('pct_weight', 0)}% by weight)"
        )
    return "\n".join(lines) if lines else "  No materials listed."


def generate_executive_summary(report_data: dict, api_key: str) -> str:
    kwp = _kwp_summary(report_data.get('kwp_materials', []))
    total_weight = sum(
        float(m.get('weight_tonnes', 0))
        for m in report_data.get('kwp_materials', [])
    )

    prompt = f"""You are a sustainability consultant writing an executive summary for a professional pre-demolition audit report.

Project details:
- Address: {report_data.get('job_address', '')}
- Client: {report_data.get('client_name', '')}
- Building description: {report_data.get('building_description', '')}
- Gross Internal Area: {report_data.get('total_gia', '')} m²
- Year built: {report_data.get('year_built', '')}
- Total waste materials identified: {total_weight:.1f} tonnes

Key Waste Products (KWP):
{kwp}

Write a professional executive summary for this pre-demolition audit (3 concise paragraphs, approx. 200–250 words total).

Paragraph 1: Introduce the purpose of this audit, the building, and the client.
Paragraph 2: Summarise the key waste products identified, the total tonnage, and the main diversion opportunities.
Paragraph 3: State the commitment to circular economy principles and the expected diversion from landfill.

Use formal, British English. Do not use bullet points. Do not include a heading."""

    return _call_claude(api_key, prompt, max_tokens=500)


def generate_introduction(report_data: dict, api_key: str) -> str:
    prompt = f"""You are a sustainability consultant writing the introduction section of a pre-demolition audit report.

Project details:
- Address: {report_data.get('job_address', '')}
- Client: {report_data.get('client_name', '')}
- Building description: {report_data.get('building_description', '')}
- Gross Internal Area: {report_data.get('total_gia', '')} m²
- Year built: {report_data.get('year_built', '')}

Write a professional introduction (2 paragraphs, approx. 120–150 words total).

Paragraph 1: State who commissioned the audit and why, the scope of the building.
Paragraph 2: Briefly describe the methodology used (visual inspection, desk study, contractor interviews) and objectives (identify, quantify and characterise materials; maximise diversion from landfill).

Use formal, British English. Do not use bullet points. Do not include a heading."""

    return _call_claude(api_key, prompt, max_tokens=350)


def generate_conclusion(report_data: dict, api_key: str) -> str:
    kwp = _kwp_summary(report_data.get('kwp_materials', []))
    total_weight = sum(
        float(m.get('weight_tonnes', 0))
        for m in report_data.get('kwp_materials', [])
    )
    # Calculate approximate diversion rate (reuse + recycling)
    diverted = sum(
        float(m.get('weight_tonnes', 0)) *
        (float(m.get('reuse_pct', 0)) + float(m.get('recycling_pct', 0))) / 100
        for m in report_data.get('kwp_materials', [])
    )
    diversion_rate = (diverted / total_weight * 100) if total_weight > 0 else 0

    prompt = f"""You are a sustainability consultant writing the conclusion and recommendations for a pre-demolition audit report.

Project details:
- Address: {report_data.get('job_address', '')}
- Client: {report_data.get('client_name', '')}
- Total waste materials: {total_weight:.1f} tonnes
- Estimated diversion from landfill: {diversion_rate:.0f}%

Key Waste Products:
{kwp}

Write a professional conclusion and recommendations section (2–3 paragraphs, approx. 200 words).

Paragraph 1: Summarise the overall findings — total tonnage, key materials, and what the audit has demonstrated.
Paragraph 2: State the recommended diversion strategy — what should be reused, recycled, or recovered — and the estimated landfill diversion rate.
Paragraph 3: State the next steps and commitments (e.g. issue waste management plan, appoint specialist contractors, track KPIs).

Use formal, British English. Do not use bullet points. Do not include a heading."""

    return _call_claude(api_key, prompt, max_tokens=500)


def generate_material_recommendation(material_name: str, weight: float,
                                      reuse_potential: str, api_key: str) -> str:
    prompt = f"""You are a sustainability consultant writing a brief recommendation for a specific material identified in a pre-demolition audit.

Material: {material_name}
Estimated weight: {weight:.1f} tonnes
Reuse potential: {reuse_potential}

Write one short paragraph (3–4 sentences) recommending how this material should be managed.
Mention: the preferred diversion route (reuse if potential is High, recycling if Medium, recovery if Low),
suggested contractors or markets, and any pre-treatment required.
Use formal, British English. Do not include a heading."""

    return _call_claude(api_key, prompt, max_tokens=200)
