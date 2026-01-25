"""
Matplotlib chart rendering for image export.

This module requires matplotlib (install with `pip install pacta[viz]`).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def render_trends_chart(
    values: list[float],
    labels: list[str],
    *,
    metric: str,
    output_path: str,
    title: str | None = None,
) -> None:
    """
    Render a trends chart to an image file using matplotlib.

    Args:
        values: Y-axis values (one per data point)
        labels: X-axis labels (one per data point)
        metric: The metric name being tracked
        output_path: Path to save the image (PNG, SVG, PDF supported)
        title: Optional chart title

    Raises:
        ImportError: If matplotlib is not installed
    """
    try:
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise ImportError("matplotlib is required for image export. Install it with: pip install pacta[viz]") from e

    # Parse dates from labels if possible
    dates = []
    for label in labels:
        try:
            # Try to parse "Mon DD" format
            dt = datetime.strptime(label, "%b %d")
            # Use current year
            dt = dt.replace(year=datetime.now().year)
            dates.append(dt)
        except ValueError:
            dates = None
            break

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot data
    if dates:
        ax.plot(dates, values, marker="o", linewidth=2, markersize=8, color="#2563eb")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.xticks(rotation=45)
    else:
        x_positions = list(range(len(values)))
        ax.plot(x_positions, values, marker="o", linewidth=2, markersize=8, color="#2563eb")
        ax.set_xticks(x_positions)
        ax.set_xticklabels(labels, rotation=45, ha="right")

    # Styling
    metric_labels = {
        "violations": "Violations",
        "nodes": "Node Count",
        "edges": "Edge Count",
        "density": "Density (edges/nodes)",
    }
    y_label = metric_labels.get(metric, metric.title())
    ax.set_ylabel(y_label, fontsize=12)
    ax.set_xlabel("Date", fontsize=12)

    # Title
    if title:
        ax.set_title(title, fontsize=14, fontweight="bold")
    else:
        ax.set_title(f"{y_label} Over Time", fontsize=14, fontweight="bold")

    # Grid
    ax.grid(True, alpha=0.3)
    ax.set_axisbelow(True)

    # Fill area under curve
    if dates:
        ax.fill_between(dates, values, alpha=0.1, color="#2563eb")
    else:
        ax.fill_between(x_positions, values, alpha=0.1, color="#2563eb")

    # Add trend annotation
    if len(values) >= 2:
        diff = values[-1] - values[0]
        if diff < 0:
            trend_text = f"Trend: {diff:+.1f} (Improving)" if metric == "violations" else f"Trend: {diff:+.1f}"
            trend_color = "#16a34a"  # Green
        elif diff > 0:
            trend_text = f"Trend: {diff:+.1f} (Worsening)" if metric == "violations" else f"Trend: {diff:+.1f}"
            trend_color = "#dc2626"  # Red
        else:
            trend_text = "Trend: Stable"
            trend_color = "#6b7280"  # Gray

        ax.annotate(
            trend_text,
            xy=(0.02, 0.98),
            xycoords="axes fraction",
            fontsize=10,
            color=trend_color,
            verticalalignment="top",
            fontweight="bold",
        )

    # Tight layout
    plt.tight_layout()

    # Save
    output = Path(output_path)
    fig.savefig(output, dpi=150, bbox_inches="tight")
    plt.close(fig)


def is_matplotlib_available() -> bool:
    """Check if matplotlib is installed."""
    try:
        import matplotlib  # noqa: F401

        return True
    except ImportError:
        return False
