import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import io
from datetime import datetime
from zoneinfo import ZoneInfo


def generate_graph_from_csv(
    file_content, timezone="UTC", tick_interval_minutes=15
):
    if timezone is None:
        timezone = "UTC"  # or call get_timezone() if available
    """Generate a graph from CSV data and return the image bytes"""

    # Create a file-like object from the content
    csv_io = io.StringIO(file_content.decode("utf-8"))

    # Load data
    data = pd.read_csv(csv_io)

    # Convert 'time' to local datetime
    if "time" in data.columns:
        data["timestamp"] = (
            pd.to_datetime(data["time"], unit="s")
            .dt.tz_localize("UTC")
            .dt.tz_convert(timezone)
        )
    else:
        # If 'time' column doesn't exist, try to use the first column
        try:
            first_col = data.columns[0]
            data["timestamp"] = pd.to_datetime(data[first_col]).dt.tz_localize(timezone)
        except:
            # If all else fails, use index as time
            current_time = datetime.now(ZoneInfo(timezone))
            data["timestamp"] = pd.date_range(
                end=current_time, periods=len(data), freq="T"
            ).tz_localize(timezone)

    # Calculate total elapsed time
    elapsed = data["timestamp"].iloc[-1] - data["timestamp"].iloc[0]
    total_hours, remainder = divmod(elapsed.total_seconds(), 3600)
    total_minutes = remainder // 60
    elapsed_str = f"{int(total_hours)}h {int(total_minutes)}m"

    # Determine which columns to plot
    temp_columns = []
    duty_column = None

    # Scale temperature readings if they exist
    for col_name in ["set_temp", "pit_temp", "meat_temp1"]:
        if col_name in data.columns:
            data[col_name] = data[col_name] / 5
            temp_columns.append(col_name)

    # Scale duty cycle reading if it exists
    if "duty_cycle" in data.columns:
        data["duty_cycle"] = data["duty_cycle"] / 100
        duty_column = "duty_cycle"

    # If we didn't find expected columns, look for temp in column names
    if not temp_columns:
        for col in data.columns:
            if "temp" in col.lower() and col != "timestamp":
                temp_columns.append(col)
            elif "duty" in col.lower() or "cycle" in col.lower():
                duty_column = col
                # Scale duty if not already scaled (assuming percentage 0-100)
                if data[duty_column].max() > 1.0:
                    data[duty_column] = data[duty_column] / 100

    # Extract the date for title
    graph_date = data["timestamp"].dt.date.iloc[0]

    # Plotting
    fig, ax = plt.subplots(figsize=(16, 9))

    # Color mapping
    colors = {
        "set_temp": "blue",
        "pit_temp": "red",
        "meat_temp1": "orange",
    }

    # Plot temperature lines
    for col in temp_columns:
        color = colors.get(col, "gray")
        style = "--" if "set" in col.lower() else "-"
        ax.plot(
            data["timestamp"],
            data[col],
            label=f"{col.replace('_', ' ').title()} (°F)",
            linestyle=style,
            color=color,
        )

    # Plot duty cycle if available
    if duty_column:
        ax.plot(
            data["timestamp"], data[duty_column], label="Duty Cycle (%)", color="green"
        )

    # Titles and labels
    ax.set_title(
        f"Smoker Data for {graph_date}  (Cook time: {elapsed_str})", fontsize=20
    )
    ax.set_xlabel("Local Time", fontsize=16)
    ax.set_ylabel("Temperature (°F) / Duty Cycle (%)", fontsize=16)

    # Format x-axis to show only time
    local_formatter = mdates.DateFormatter("%H:%M:%S", tz=data["timestamp"].dt.tz)
    ax.xaxis.set_major_formatter(local_formatter)

    # Set ticks every N minutes
    locator = mdates.MinuteLocator(interval=tick_interval_minutes)
    ax.xaxis.set_major_locator(locator)

    # Set y-axis to 25°F increments
    ax.yaxis.set_major_locator(ticker.MultipleLocator(25))

    # Grid, Legend, and Layout
    ax.grid(True, which="both", linestyle="--", linewidth=0.5)
    ax.legend(fontsize=14)
    fig.autofmt_xdate()
    plt.tight_layout()

    # Save to bytes buffer instead of file
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    buf.seek(0)
    plt.close(fig)

    return buf.read()


def generate_graph_from_db(
    temp_logs, timezone="UTC", tick_interval_minutes=15
):
    """Generate a graph from TemperatureLog data and return the image bytes"""
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import matplotlib.ticker as ticker
    import io
    from zoneinfo import ZoneInfo
    from datetime import datetime

    # Convert temperature logs to pandas DataFrame
    data = []
    for log in temp_logs:
        data.append(
            {
                "timestamp": log.timestamp,
                "set_temp": log.set_temp,
                "pit_temp": log.pit_temp,
                "meat_temp1": log.meat_temp1,
                "blower": log.blower,  # Using blower instead of duty_cycle
            }
        )

    # Create DataFrame
    df = pd.DataFrame(data)

    # Skip if no data
    if df.empty:
        return generate_no_data_graph()

    # Make sure timestamp is timezone aware - assume UTC if naive
    if not df.empty and df["timestamp"].iloc[0].tzinfo is None:
        df["timestamp"] = df["timestamp"].apply(lambda dt: dt.replace(tzinfo=ZoneInfo("UTC")))

    # Convert to user's timezone
    if not df.empty:
        user_tz = ZoneInfo(timezone)
        df["timestamp"] = df["timestamp"].apply(lambda dt: dt.astimezone(user_tz))

    # Calculate total elapsed time if we have data
    if len(df) > 1:
        elapsed = df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]
        total_hours, remainder = divmod(elapsed.total_seconds(), 3600)
        total_minutes = remainder // 60
        elapsed_str = f"{int(total_hours)}h {int(total_minutes)}m"
    else:
        elapsed_str = "0h 0m"

    # Extract the date for title
    graph_date = (
        df["timestamp"].dt.date.iloc[0] if not df.empty else datetime.now().date()
    )

    # Plotting
    fig, ax = plt.subplots(figsize=(16, 9))

    # Color mapping
    colors = {
        "set_temp": "blue",
        "pit_temp": "red",
        "meat_temp1": "orange",
    }

    # Plot temperature lines
    for col in ["set_temp", "pit_temp", "meat_temp1"]:
        if col in df.columns and not df[col].isnull().all():
            color = colors.get(col, "gray")
            style = "--" if "set" in col.lower() else "-"
            ax.plot(
                df["timestamp"],
                df[col],
                label=f"{col.replace('_', ' ').title()} (°F)",
                linestyle=style,
                color=color,
            )

        # Plot blower as duty cycle if available
    if "blower" in df.columns and not df["blower"].isnull().all():
        ax.plot(df["timestamp"], df["blower"], label="Blower (%)", color="green")

        # Titles and labels
        ax.set_title(
            f"Smoker Data for {graph_date}  (Cook time: {elapsed_str})", fontsize=20
        )
        ax.set_xlabel("Local Time", fontsize=16)
        ax.set_ylabel("Temperature (°F) / Blower (%)", fontsize=16)

    # Format x-axis to show only time
    try:
        # Use user's timezone for formatting
        user_tz = ZoneInfo(timezone)
        local_formatter = mdates.DateFormatter("%H:%M:%S", tz=user_tz)
        ax.xaxis.set_major_formatter(local_formatter)

        # Set ticks every N minutes
        locator = mdates.MinuteLocator(interval=tick_interval_minutes)
        ax.xaxis.set_major_locator(locator)
    except Exception as e:
        # Fallback if there's an issue with time formatting
        print(f"Error formatting timestamps: {e}")

    # Set y-axis to 25°F increments
    ax.yaxis.set_major_locator(ticker.MultipleLocator(25))

    # Grid, Legend, and Layout
    ax.grid(True, which="both", linestyle="--", linewidth=0.5)
    ax.legend(fontsize=14)
    fig.autofmt_xdate()
    plt.tight_layout()

    # Save to bytes buffer instead of file
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    buf.seek(0)
    plt.close(fig)

    return buf.read()


def generate_graph_from_manual_temps(
    manual_temps, timezone="UTC", tick_interval_minutes=15
):
    """Generate a graph from manual Temperature entries and return the image bytes"""
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import matplotlib.ticker as ticker
    import io
    from zoneinfo import ZoneInfo
    from datetime import datetime
    
    # Use print statements instead of logging for debugging in Docker
    print(f"=== MANUAL TEMP GRAPH DEBUG ===")
    print(f"Called with {len(manual_temps)} manual temperature entries")
    print(f"Timezone: {timezone}")

    # Convert manual temperature entries to pandas DataFrame
    data = []
    for i, temp in enumerate(manual_temps):
        entry = {
            "timestamp": temp.timestamp,
            "meat_temp": temp.meat_temp,
            "smoker_temp": temp.smoker_temp,
            "note": temp.note or "",
        }
        data.append(entry)
        print(f"Entry {i+1}: timestamp={entry['timestamp']}, meat={entry['meat_temp']}, smoker={entry['smoker_temp']}")

    # Create DataFrame
    df = pd.DataFrame(data)
    print(f"DataFrame created with shape: {df.shape}")
    print(f"DataFrame columns: {df.columns.tolist()}")

    # Skip if no data
    if df.empty:
        print("ERROR: DataFrame is empty, generating no-data graph")
        return generate_no_data_graph()

    # Debug: Check the data types and values
    print(f"Timestamp dtype: {df['timestamp'].dtype}")
    print(f"First timestamp: {df['timestamp'].iloc[0]}")
    print(f"Last timestamp: {df['timestamp'].iloc[-1]}")
    
    # Check for valid temperature data
    meat_temp_count = df['meat_temp'].notna().sum()
    smoker_temp_count = df['smoker_temp'].notna().sum()
    print(f"Valid meat_temp entries: {meat_temp_count}")
    print(f"Valid smoker_temp entries: {smoker_temp_count}")
    
    if meat_temp_count > 0:
        print(f"Meat temp range: {df['meat_temp'].min()} to {df['meat_temp'].max()}")
    if smoker_temp_count > 0:
        print(f"Smoker temp range: {df['smoker_temp'].min()} to {df['smoker_temp'].max()}")

    # Make sure timestamp is timezone aware - assume UTC if naive
    if not df.empty:
        first_timestamp = df["timestamp"].iloc[0]
        if first_timestamp.tzinfo is None:
            print("Timestamps are naive, assuming UTC")
            df["timestamp"] = df["timestamp"].apply(lambda dt: dt.replace(tzinfo=ZoneInfo("UTC")))
        else:
            print(f"Timestamps are timezone aware: {first_timestamp.tzinfo}")

        # Convert to user's timezone
        try:
            user_tz = ZoneInfo(timezone)
            print(f"Converting timestamps to {timezone}")
            df["timestamp"] = df["timestamp"].apply(lambda dt: dt.astimezone(user_tz))
            print(f"Converted first timestamp: {df['timestamp'].iloc[0]}")
        except Exception as e:
            print(f"ERROR converting timezone: {e}")
            # Fall back to UTC if timezone conversion fails
            timezone = "UTC"

    # Calculate total elapsed time if we have data
    if len(df) > 1:
        elapsed = df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]
        total_hours, remainder = divmod(elapsed.total_seconds(), 3600)
        total_minutes = remainder // 60
        elapsed_str = f"{int(total_hours)}h {int(total_minutes)}m"
        print(f"Cook time: {elapsed_str}")
    else:
        elapsed_str = "0h 0m"
        print("Only one data point, cook time is 0")

    # Extract the date for title
    try:
        graph_date = df["timestamp"].dt.date.iloc[0] if not df.empty else datetime.now().date()
        print(f"Graph date: {graph_date}")
    except Exception as e:
        print(f"ERROR getting graph date: {e}")
        graph_date = datetime.now().date()

    # Plotting
    try:
        print("Creating matplotlib figure...")
        fig, ax = plt.subplots(figsize=(16, 9))
        print("Figure created successfully")

        # Color mapping for manual entries
        colors = {
            "meat_temp": "orange",
            "smoker_temp": "red",
        }

        # Plot temperature lines
        plotted_any = False
        for col in ["meat_temp", "smoker_temp"]:
            if col in df.columns:
                # Filter out None/NaN values for plotting
                plot_data = df[df[col].notna()]
                print(f"Processing {col}: {len(plot_data)} valid points out of {len(df)} total")
                
                if not plot_data.empty:
                    color = colors.get(col, "gray")
                    print(f"Plotting {col} with color {color}")
                    
                    # Use markers for manual entries since they're typically less frequent
                    ax.plot(
                        plot_data["timestamp"],
                        plot_data[col],
                        label=f"{col.replace('_', ' ').title()} (°F)",
                        color=color,
                        marker='o',
                        markersize=6,
                        linewidth=2,
                        linestyle='-',
                    )
                    plotted_any = True
                    print(f"Successfully plotted {col}")
                else:
                    print(f"No valid data for {col}")

        # If we didn't plot anything, show a message
        if not plotted_any:
            print("WARNING: No valid temperature data to plot")
            ax.text(
                0.5, 0.5, "No valid temperature data to display",
                horizontalalignment="center", verticalalignment="center",
                transform=ax.transAxes, fontsize=16
            )
        else:
            print(f"Successfully plotted data for graph")

        # Titles and labels
        ax.set_title(
            f"Manual Temperature Readings for {graph_date}  (Cook time: {elapsed_str})", 
            fontsize=20
        )
        ax.set_xlabel("Local Time", fontsize=16)
        ax.set_ylabel("Temperature (°F)", fontsize=16)

        # Format x-axis to show only time
        if plotted_any:
            try:
                print("Formatting x-axis...")
                # Use user's timezone for formatting
                user_tz = ZoneInfo(timezone)
                local_formatter = mdates.DateFormatter("%H:%M", tz=user_tz)
                ax.xaxis.set_major_formatter(local_formatter)

                # Set ticks - be more conservative with manual data
                # Use fewer ticks since manual entries are typically sparse
                if len(df) <= 10:
                    # For few data points, show all timestamps
                    ax.set_xticks(df["timestamp"])
                else:
                    # For more data points, use time-based intervals
                    locator = mdates.MinuteLocator(interval=max(15, tick_interval_minutes))
                    ax.xaxis.set_major_locator(locator)
                
                # Set y-axis to 25°F increments, but make sure we have a reasonable range
                y_min, y_max = ax.get_ylim()
                if y_max - y_min < 50:  # If range is too small, expand it
                    y_center = (y_min + y_max) / 2
                    ax.set_ylim(y_center - 50, y_center + 50)
                
                ax.yaxis.set_major_locator(ticker.MultipleLocator(25))
                print("X-axis formatting completed")
                
            except Exception as e:
                print(f"ERROR formatting x-axis: {e}")
                # Continue without custom formatting

        # Grid, Legend, and Layout
        ax.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.7)
        if plotted_any:
            ax.legend(fontsize=14, loc='upper left')
        
        # Rotate x-axis labels for better readability
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        plt.tight_layout()

        # Save to bytes buffer instead of file
        print("Saving graph to buffer...")
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150, bbox_inches='tight')
        buf.seek(0)
        image_data = buf.read()
        plt.close(fig)
        
        print(f"Graph saved successfully. Image size: {len(image_data)} bytes")
        return image_data
        
    except Exception as e:
        print(f"ERROR in graph generation: {str(e)}")
        import traceback
        print("Full traceback:")
        traceback.print_exc()
        
        # Return a basic error graph
        try:
            fig, ax = plt.subplots(figsize=(16, 9))
            ax.text(0.5, 0.5, f"Error generating graph:\n{str(e)}", 
                   horizontalalignment="center", verticalalignment="center",
                   transform=ax.transAxes, fontsize=16)
            ax.set_title("Graph Generation Error", fontsize=20)
            buf = io.BytesIO()
            plt.savefig(buf, format="png", dpi=150)
            buf.seek(0)
            plt.close(fig)
            return buf.read()
        except:
            # If even error graph fails, return no-data graph
            return generate_no_data_graph()


def generate_no_data_graph():
    """Generate a 'No data available' graph image"""
    import matplotlib.pyplot as plt
    import io
    
    print("Generating no-data graph")
    fig, ax = plt.subplots(figsize=(16, 9))
    ax.text(
        0.5,
        0.5,
        "No temperature data available",
        horizontalalignment="center",
        verticalalignment="center",
        transform=ax.transAxes,
        fontsize=20,
    )
    ax.set_title("Temperature Graph", fontsize=20)
    
    # Remove axes
    ax.set_xticks([])
    ax.set_yticks([])
    
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf.read()
