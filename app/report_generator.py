"""
report_generator.py – Enhanced PDF report with executive summary and trend analysis.
Includes model performance metrics and key influencing factors (feature importance).
"""
from __future__ import annotations

import json
import os
from datetime import date

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from sqlalchemy.orm import Session

from app.models import HistoricalCrimeData, PredictedCrimeData
import pandas as pd

RISK_COLORS = {"Low": colors.HexColor("#10b981"),
               "Medium": colors.HexColor("#f59e0b"),
               "High": colors.HexColor("#ef4444")}


def generate_pdf_report(state: str, db: Session) -> str | None:
    hist_q = db.query(HistoricalCrimeData).filter(HistoricalCrimeData.state_name == state)
    pred_q = db.query(PredictedCrimeData).filter(PredictedCrimeData.state_name == state)

    df_hist = pd.read_sql(hist_q.statement, db.bind)
    df_pred = pd.read_sql(pred_q.statement, db.bind)

    if df_hist.empty:
        return None

    file_path = f"report_{state.replace(' ', '_')}.pdf"
    doc = SimpleDocTemplate(
        file_path,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    story = []

    # ── Header ──────────────────────────────────────────────────────────────────
    title_style = ParagraphStyle(
        "Title2", parent=styles["Title"],
        fontSize=20, spaceAfter=4,
        textColor=colors.HexColor("#1e293b")
    )
    sub_style = ParagraphStyle(
        "SubTitle2", parent=styles["Normal"],
        fontSize=11, textColor=colors.HexColor("#64748b"), spaceAfter=12
    )
    story.append(Paragraph(f"Crime Analytics Report", title_style))
    story.append(Paragraph(f"State: <b>{state}</b> &nbsp;·&nbsp; Generated: {date.today()}", sub_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
    story.append(Spacer(1, 12))

    # ── Historical Summary ───────────────────────────────────────────────────────
    story.append(Paragraph("Historical Summary (2010–2024)", styles["Heading2"]))
    df_hist = df_hist.sort_values("year")
    latest = df_hist.iloc[-1]
    earliest = df_hist.iloc[0]

    avg_cr = df_hist["crime_rate_per_100k"].mean()
    max_cr = df_hist["crime_rate_per_100k"].max()
    min_cr = df_hist["crime_rate_per_100k"].min()
    trend = "📈 Increasing" if latest["crime_rate_per_100k"] > earliest["crime_rate_per_100k"] else "📉 Decreasing"

    summary_data = [
        ["Metric", "Value"],
        ["Avg Crime Rate (all years)", f"{avg_cr:.1f} per 100k"],
        ["Peak Crime Rate", f"{max_cr:.1f} per 100k ({int(df_hist.loc[df_hist['crime_rate_per_100k'].idxmax(),'year'])})"],
        ["Lowest Crime Rate", f"{min_cr:.1f} per 100k ({int(df_hist.loc[df_hist['crime_rate_per_100k'].idxmin(),'year'])})"],
        ["Latest Rate (2024)", f"{latest['crime_rate_per_100k']:.1f} per 100k"],
        ["Trend Direction", trend],
        ["Latest Literacy Rate", f"{latest['literacy_rate']:.1f}%"],
        ["Latest Unemployment Rate", f"{latest['unemployment_rate']:.1f}%"],
        ["Latest Urbanization Rate", f"{latest['urbanization_rate']:.1f}%"],
        ["Latest Police Strength (per 100k)", f"{latest['police_strength_per_100k']:.1f}"],
    ]

    summary_table = Table(summary_data, colWidths=[3.5 * inch, 3.5 * inch])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#1e40af")),
        ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0), 10),
        ("BACKGROUND",  (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.HexColor("#ffffff")]),
        ("FONTNAME",    (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 1), (-1, -1), 9),
        ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 18))

    # ── Historical Data Table ────────────────────────────────────────────────────
    story.append(Paragraph("Year-by-Year Historical Data", styles["Heading2"]))
    hist_table_data = [["Year", "Crime Rate/100k", "Unemployment%", "Literacy%", "Urban%", "Police/100k"]]
    for _, row in df_hist.iterrows():
        hist_table_data.append([
            str(int(row["year"])),
            f"{row['crime_rate_per_100k']:.1f}",
            f"{row['unemployment_rate']:.1f}",
            f"{row['literacy_rate']:.1f}",
            f"{row['urbanization_rate']:.1f}",
            f"{row['police_strength_per_100k']:.1f}",
        ])

    hist_table = Table(hist_table_data, colWidths=[0.8*inch, 1.3*inch, 1.2*inch, 1.0*inch, 0.9*inch, 1.3*inch])
    hist_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f1f5f9"), colors.white]),
        ("FONTSIZE",    (0, 1), (-1, -1), 8),
        ("GRID",        (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
        ("ALIGN",       (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(hist_table)
    story.append(Spacer(1, 18))

    # ── Forecast Table ───────────────────────────────────────────────────────────
    story.append(Paragraph("ML-Based Crime Rate Forecast", styles["Heading2"]))

    if df_pred.empty:
        story.append(Paragraph("⚠️ No forecast data available. Run Generate Forecast from the dashboard.", styles["Normal"]))
    else:
        df_pred = df_pred.sort_values("year")
        pred_table_data = [["Year", "Predicted Rate/100k", "Risk Level", "Change vs 2024"]]
        base_rate = float(latest["crime_rate_per_100k"])
        for _, row in df_pred.iterrows():
            predicted = float(row["predicted_crime_rate"])
            change = predicted - base_rate
            change_str = f"+{change:.1f}" if change >= 0 else f"{change:.1f}"
            pred_table_data.append([
                str(int(row["year"])),
                f"{predicted:.1f}",
                str(row["crime_level"]),
                change_str,
            ])

        pred_table = Table(pred_table_data, colWidths=[1.0*inch, 1.8*inch, 1.5*inch, 1.7*inch])
        row_colors = []
        level_map = {"High": colors.HexColor("#fef2f2"), "Medium": colors.HexColor("#fffbeb"), "Low": colors.HexColor("#f0fdf4")}
        for i, row in enumerate(pred_table_data[1:], start=1):
            lvl = row[2]
            row_colors.append(("BACKGROUND", (0, i), (-1, i), level_map.get(lvl, colors.white)))

        pred_table.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#1e40af")),
            ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, -1), 9),
            ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
            ("ALIGN",       (1, 0), (-1, -1), "CENTER"),
            ("TOPPADDING",  (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ] + row_colors))
        story.append(pred_table)

    # ── Model performance metrics ─────────────────────────────────────────────
    story.append(Spacer(1, 18))
    story.append(Paragraph("Model Performance Metrics", styles["Heading2"]))
    metrics_path = "model_metrics.json"  # Written by ml_model in CWD (project root)
    if os.path.isfile(metrics_path):
        try:
            with open(metrics_path) as f:
                m = json.load(f)
            metrics_rows = [
                ["Metric", "Value"],
                ["Best Model", m.get("best_model", "–")],
                ["R² Score", f"{m.get('r2', 0):.4f}" if m.get("r2") is not None else "–"],
                ["RMSE", f"{m.get('rmse', 0):.2f}" if m.get("rmse") is not None else "–"],
                ["MAE", f"{m.get('mae', 0):.2f}" if m.get("mae") is not None else "–"],
            ]
            mtable = Table(metrics_rows, colWidths=[2.5 * inch, 3 * inch])
            mtable.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(mtable)
            # Key influencing factors (feature importance)
            fi = m.get("feature_importance")
            if fi and isinstance(fi, dict):
                story.append(Spacer(1, 12))
                story.append(Paragraph("Key Influencing Factors (Feature Importance)", styles["Heading2"]))
                fi_rows = [["Feature", "Importance"]]
                for k, v in sorted(fi.items(), key=lambda x: -x[1])[:10]:
                    fi_rows.append([k.replace("_", " ").title(), f"{float(v):.4f}"])
                fitable = Table(fi_rows, colWidths=[2.5 * inch, 1.5 * inch])
                fitable.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(fitable)
        except Exception:
            story.append(Paragraph("Metrics could not be loaded.", styles["Normal"]))
    else:
        story.append(Paragraph("Run /train to generate model metrics.", styles["Normal"]))

    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0")))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Generated by Crime Rate Prediction System – India | "
        "ML Models: Linear Regression · Random Forest · XGBoost",
        ParagraphStyle("Footer", parent=styles["Normal"], fontSize=7, textColor=colors.HexColor("#94a3b8"))
    ))

    doc.build(story)
    return file_path
