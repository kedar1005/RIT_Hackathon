from datetime import datetime
from html import escape
import io

import pandas as pd


REPORT_COLUMNS = [
    "id",
    "category",
    "ai_urgency",
    "status",
    "assigned_agent",
    "created_at",
    "address",
]


def _prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=REPORT_COLUMNS)

    available = [column for column in REPORT_COLUMNS if column in df.columns]
    if not available:
        available = list(df.columns)[:7]

    prepared = df[available].copy()
    prepared = prepared.fillna("")
    prepared.columns = [column.replace("_", " ").title() for column in prepared.columns]
    return prepared.astype(str)


def generate_word_report(df: pd.DataFrame) -> bytes:
    prepared = _prepare_dataframe(df)
    generated_at = datetime.now().strftime("%d %b %Y %I:%M %p")

    if prepared.empty:
        table_html = """
        <tr>
            <td colspan="7" style="padding:12px;border:1px solid #cbd5e1;">No data available for the selected filters.</td>
        </tr>
        """
    else:
        header_html = "".join(
            f"<th style='padding:10px;border:1px solid #94a3b8;background:#e2e8f0;text-align:left;'>{escape(column)}</th>"
            for column in prepared.columns
        )
        row_html = []
        for _, row in prepared.iterrows():
            row_html.append(
                "<tr>" +
                "".join(
                    f"<td style='padding:9px;border:1px solid #cbd5e1;vertical-align:top;'>{escape(str(value))}</td>"
                    for value in row
                ) +
                "</tr>"
            )
        table_html = f"<tr>{header_html}</tr>{''.join(row_html)}"

    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>CitiZen AI Complaints Report</title>
<style>
body {{ font-family: Calibri, Arial, sans-serif; color: #0f172a; margin: 28px; }}
h1 {{ margin: 0 0 6px; font-size: 24px; }}
p.meta {{ margin: 0 0 20px; color: #475569; }}
table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
th, td {{ word-wrap: break-word; font-size: 10pt; }}
</style>
</head>
<body>
<h1>CitiZen AI Complaints Report</h1>
<p class="meta">Generated on {escape(generated_at)} | Total rows: {len(prepared)}</p>
<table>{table_html}</table>
</body>
</html>"""
    return html.encode("utf-8")


def _truncate_text(value: str, limit: int) -> str:
    clean = " ".join(value.split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3] + "..."


def generate_pdf_report(df: pd.DataFrame) -> bytes:
    prepared = _prepare_dataframe(df)
    from matplotlib.backends.backend_pdf import PdfPages
    import matplotlib.pyplot as plt

    buffer = io.BytesIO()
    rows_per_page = 18
    total_pages = max((len(prepared) + rows_per_page - 1) // rows_per_page, 1)
    generated_at = datetime.now().strftime("%d %b %Y %I:%M %p")

    with PdfPages(buffer) as pdf:
        for page_index in range(total_pages):
            start = page_index * rows_per_page
            end = start + rows_per_page
            page_rows = prepared.iloc[start:end]

            fig, ax = plt.subplots(figsize=(16.5, 11.0))
            ax.axis("off")

            fig.suptitle("CitiZen AI Complaints Report", fontsize=18, fontweight="bold", y=0.98)
            ax.text(
                0.01,
                0.94,
                f"Generated on {generated_at} | Page {page_index + 1} of {total_pages} | Total rows: {len(prepared)}",
                transform=ax.transAxes,
                fontsize=10,
                color="#475569",
            )

            if page_rows.empty:
                ax.text(
                    0.01,
                    0.85,
                    "No data available for the selected filters.",
                    transform=ax.transAxes,
                    fontsize=12,
                    color="#0f172a",
                )
            else:
                display_rows = page_rows.copy()
                for column in display_rows.columns:
                    limit = 42 if column == "Address" else 20
                    display_rows[column] = display_rows[column].map(lambda value: _truncate_text(str(value), limit))

                table = ax.table(
                    cellText=display_rows.values,
                    colLabels=display_rows.columns,
                    loc="upper left",
                    cellLoc="left",
                    colLoc="left",
                    bbox=[0.01, 0.04, 0.98, 0.84],
                )
                table.auto_set_font_size(False)
                table.set_fontsize(8.5)
                table.scale(1, 1.35)

                column_widths = {
                    "Id": 0.05,
                    "Category": 0.15,
                    "Ai Urgency": 0.10,
                    "Status": 0.10,
                    "Assigned Agent": 0.11,
                    "Created At": 0.16,
                    "Address": 0.31,
                }

                for (row, col), cell in table.get_celld().items():
                    column_name = display_rows.columns[col]
                    if column_name in column_widths:
                        cell.set_width(column_widths[column_name])
                    cell.set_edgecolor("#cbd5e1")
                    if row == 0:
                        cell.set_facecolor("#e2e8f0")
                        cell.set_text_props(weight="bold", color="#0f172a")
                    else:
                        cell.set_facecolor("#ffffff" if row % 2 else "#f8fafc")

            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

    buffer.seek(0)
    return buffer.getvalue()
