"""
Chart generator for Pre-Demolition Audit reports.
Produces donut charts as base64-encoded PNG images.
"""
import io
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


# Lawmens brand colour palette
LAWMENS_COLOURS = [
    '#0d4f6c',  # Dark teal (primary)
    '#2e8b6e',  # Green
    '#5ba3c9',  # Light blue
    '#e8a838',  # Amber
    '#c0392b',  # Red
    '#8e44ad',  # Purple
    '#27ae60',  # Bright green
    '#2c3e50',  # Dark navy
    '#e67e22',  # Orange
    '#1abc9c',  # Turquoise
    '#95a5a6',  # Gray
    '#d35400',  # Dark orange
]


def _fig_to_base64(fig) -> str:
    """Convert a matplotlib figure to a base64-encoded PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                transparent=True)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return f"data:image/png;base64,{encoded}"


def generate_waste_diversion_chart(kwp_materials: list) -> str:
    """
    Single donut chart: % by weight of total waste.
    Returns base64 PNG.
    """
    if not kwp_materials:
        return ""

    labels = [m['name'] for m in kwp_materials]
    weights = [float(m.get('weight_tonnes', 0)) for m in kwp_materials]
    total = sum(weights)
    if total == 0:
        return ""

    pcts = [w / total * 100 for w in weights]
    colours = LAWMENS_COLOURS[:len(labels)]

    fig, ax = plt.subplots(figsize=(5, 5), facecolor='none')
    wedges, texts = ax.pie(
        pcts,
        labels=None,
        colors=colours,
        startangle=90,
        wedgeprops=dict(width=0.55, edgecolor='white', linewidth=2),
        pctdistance=0.75,
    )

    # Centre text
    ax.text(0, 0.12, f"{total:.0f}", ha='center', va='center',
            fontsize=20, fontweight='bold', color='#0d4f6c')
    ax.text(0, -0.18, 'tonnes', ha='center', va='center',
            fontsize=10, color='#555555')

    # Legend below chart
    legend_patches = [
        mpatches.Patch(color=colours[i], label=f"{labels[i]} ({pcts[i]:.1f}%)")
        for i in range(len(labels))
    ]
    ax.legend(
        handles=legend_patches,
        loc='lower center',
        bbox_to_anchor=(0.5, -0.45),
        ncol=2,
        frameon=False,
        fontsize=8,
        handlelength=1.2,
    )

    ax.set_aspect('equal')
    fig.subplots_adjust(bottom=0.35)
    return _fig_to_base64(fig)


def generate_kwp_charts(kwp_materials: list) -> dict:
    """
    Two donut charts side by side:
      - By volume (m³)
      - By weight (tonnes)
    Returns dict with keys 'volume' and 'weight', each a base64 PNG.
    """
    charts = {}

    for metric, key, unit in [
        ('volume_m3', 'volume', 'm³'),
        ('weight_tonnes', 'weight', 'tonnes'),
    ]:
        values = [float(m.get(metric, 0)) for m in kwp_materials]
        total = sum(values)
        if total == 0:
            charts[key] = ""
            continue

        labels = [m['name'] for m in kwp_materials]
        colours = LAWMENS_COLOURS[:len(labels)]

        fig, ax = plt.subplots(figsize=(4.5, 5), facecolor='none')
        wedges, _ = ax.pie(
            values,
            labels=None,
            colors=colours,
            startangle=90,
            wedgeprops=dict(width=0.55, edgecolor='white', linewidth=2),
        )

        # Centre text
        ax.text(0, 0.12, f"{total:.0f}", ha='center', va='center',
                fontsize=18, fontweight='bold', color='#0d4f6c')
        ax.text(0, -0.18, unit, ha='center', va='center',
                fontsize=9, color='#555555')

        # Legend
        legend_patches = [
            mpatches.Patch(
                color=colours[i],
                label=f"{labels[i]}\n{values[i]:.1f} {unit}"
            )
            for i in range(len(labels))
        ]
        ax.legend(
            handles=legend_patches,
            loc='lower center',
            bbox_to_anchor=(0.5, -0.55),
            ncol=2,
            frameon=False,
            fontsize=7.5,
            handlelength=1.2,
        )

        ax.set_aspect('equal')
        fig.subplots_adjust(bottom=0.4)
        charts[key] = _fig_to_base64(fig)

    return charts


def generate_carbon_bar_chart(kwp_materials: list) -> str:
    """
    Horizontal bar chart showing A1-A3 embodied carbon per material.
    Returns base64 PNG.
    """
    materials = [
        m for m in kwp_materials
        if m.get('embodied_carbon') and float(str(m['embodied_carbon']).replace(',', '') or 0) > 0
    ]
    if not materials:
        return ""

    names = [m['name'] for m in materials]
    values = [
        float(str(m['embodied_carbon']).replace(',', ''))
        for m in materials
    ]
    colours = LAWMENS_COLOURS[:len(names)]

    fig, ax = plt.subplots(figsize=(6, max(3, len(names) * 0.6)), facecolor='none')
    bars = ax.barh(names, values, color=colours, edgecolor='white', height=0.6)

    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + max(values) * 0.01, bar.get_y() + bar.get_height() / 2,
                f'{val:.1f}', va='center', fontsize=8, color='#333333')

    ax.set_xlabel('tCO₂e (A1–A3)', fontsize=9, color='#555555')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(labelsize=8)
    ax.invert_yaxis()

    fig.tight_layout()
    return _fig_to_base64(fig)
