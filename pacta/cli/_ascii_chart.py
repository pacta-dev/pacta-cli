def render_line_chart(
    values: list[float],
    labels: list[str],
    *,
    width: int = 60,
    height: int = 10,
    title: str | None = None,
) -> str:
    """
    Render a simple ASCII line chart.

    Args:
        values: Y-axis values (one per data point)
        labels: X-axis labels (one per data point)
        width: Chart width in characters
        height: Chart height in lines
        title: Optional chart title

    Returns:
        ASCII chart as a string
    """
    if not values:
        return "No data to display."

    lines: list[str] = []

    # Title
    if title:
        lines.append(title)
        lines.append("=" * len(title))
        lines.append("")

    # Calculate scale
    min_val = min(values)
    max_val = max(values)

    # Handle edge case where all values are the same
    if min_val == max_val:
        min_val = 0 if max_val > 0 else max_val - 1
        if max_val == 0:
            max_val = 1

    val_range = max_val - min_val

    # Y-axis label width (for padding)
    y_label_width = max(len(f"{max_val:.0f}"), len(f"{min_val:.0f}")) + 1

    # Calculate chart area dimensions
    chart_width = min(width - y_label_width - 3, len(values) * 3)
    chart_width = max(chart_width, len(values))  # At least 1 char per point

    # Map values to chart positions (column indices)
    if len(values) == 1:
        x_positions = [chart_width // 2]
    else:
        x_positions = [int((i / (len(values) - 1)) * (chart_width - 1)) for i in range(len(values))]

    # Map values to row indices (0 = bottom, height-1 = top)
    def value_to_row(v: float) -> int:
        if val_range == 0:
            return height // 2
        normalized = (v - min_val) / val_range
        return int(normalized * (height - 1))

    # Build the chart grid
    grid: list[list[str]] = [[" " for _ in range(chart_width)] for _ in range(height)]

    # Plot points
    for i, v in enumerate(values):
        row = value_to_row(v)
        col = x_positions[i]
        if 0 <= row < height and 0 <= col < chart_width:
            grid[row][col] = "\u25cf"  # Filled circle

    # Connect points with lines (optional - use dashes for now)
    for i in range(len(values) - 1):
        row1 = value_to_row(values[i])
        row2 = value_to_row(values[i + 1])
        col1 = x_positions[i]
        col2 = x_positions[i + 1]

        # Simple horizontal connection if on same row
        if row1 == row2 and col2 - col1 > 1:
            for c in range(col1 + 1, col2):
                if grid[row1][c] == " ":
                    grid[row1][c] = "-"

    # Render with Y-axis labels
    for row_idx in range(height - 1, -1, -1):
        # Show label at top, middle, and bottom
        if row_idx == height - 1:
            label = f"{max_val:>{y_label_width}.0f}"
        elif row_idx == 0:
            label = f"{min_val:>{y_label_width}.0f}"
        elif row_idx == height // 2:
            mid_val = (max_val + min_val) / 2
            label = f"{mid_val:>{y_label_width}.0f}"
        else:
            label = " " * y_label_width

        # Y-axis line character
        if row_idx == 0:
            axis_char = "\u2514"  # Bottom-left corner
        else:
            axis_char = "\u2502"  # Vertical line

        lines.append(f"{label} {axis_char}{''.join(grid[row_idx])}")

    # X-axis
    lines.append(" " * (y_label_width + 1) + "\u2514" + "\u2500" * chart_width)

    # X-axis labels (simplified - show first and last)
    if labels:
        label_line = " " * (y_label_width + 2)
        if len(labels) == 1:
            label_line += labels[0].center(chart_width)
        else:
            first_label = labels[0][:10]
            last_label = labels[-1][:10]
            spacing = chart_width - len(first_label) - len(last_label)
            if spacing > 0:
                label_line += first_label + " " * spacing + last_label
            else:
                label_line += first_label
        lines.append(label_line)

    return "\n".join(lines)


def render_trend_summary(
    values: list[float],
    labels: list[str],
    metric_name: str,
) -> str:
    """
    Render a summary of the trend.

    Args:
        values: The data values
        labels: The date labels
        metric_name: Name of the metric being tracked

    Returns:
        Summary text
    """
    if not values:
        return "No data available."

    lines: list[str] = []
    lines.append("")

    first_val = values[0]
    last_val = values[-1]
    diff = last_val - first_val

    # Trend direction
    if diff < 0:
        trend_icon = "\u2193"  # Down arrow
        trend_word = "Improving" if metric_name == "violations" else "Decreasing"
    elif diff > 0:
        trend_icon = "\u2191"  # Up arrow
        trend_word = "Worsening" if metric_name == "violations" else "Increasing"
    else:
        trend_icon = "\u2192"  # Right arrow
        trend_word = "Stable"

    diff_str = f"{diff:+.2f}" if isinstance(diff, float) and not diff.is_integer() else f"{diff:+.0f}"
    lines.append(f"Trend: {trend_icon} {trend_word} ({diff_str} over period)")

    # First and last values
    first_str = (
        f"{first_val:.2f}" if isinstance(first_val, float) and not first_val.is_integer() else f"{first_val:.0f}"
    )
    last_str = f"{last_val:.2f}" if isinstance(last_val, float) and not last_val.is_integer() else f"{last_val:.0f}"

    first_label = labels[0] if labels else "start"
    last_label = labels[-1] if labels else "end"

    unit = _metric_unit(metric_name)
    lines.append(f"First: {first_str} {unit} ({first_label})")
    lines.append(f"Last:  {last_str} {unit} ({last_label})")

    # Statistics
    avg_val = float(sum(values) / len(values))
    max_val = max(values)
    min_val = min(values)

    lines.append("")
    avg_str = f"{avg_val:.2f}" if not avg_val.is_integer() else f"{avg_val:.0f}"
    lines.append(f"Average: {avg_str} {unit}")
    lines.append(f"Min: {min_val:.0f}, Max: {max_val:.0f}")

    return "\n".join(lines)


def _metric_unit(metric_name: str) -> str:
    """Get the display unit for a metric."""
    units = {
        "violations": "violations",
        "nodes": "nodes",
        "edges": "edges",
        "density": "ratio",
    }
    return units.get(metric_name, "")
