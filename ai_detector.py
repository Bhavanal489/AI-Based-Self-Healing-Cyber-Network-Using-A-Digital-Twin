
import csv
from pathlib import Path

LATENCY_THRESHOLD_MS = 50
PACKET_LOSS_THRESHOLD_PERCENT = 5
THROUGHPUT_THRESHOLD_MBPS = 10


def load_latest_telemetry():
    csv_path = Path(__file__).parent / "data" / "telemetry.csv"

    if not csv_path.exists():
        print("Telemetry file not found. Run the collector first.")
        return None

    with open(csv_path, "r", newline="") as file:
        rows = list(csv.DictReader(file))

    return rows[-1] if rows else None


def detect_anomalies(telemetry):
    if not telemetry:
        return ["No telemetry data available"]

    anomalies = []

    try:
        packet_loss = float(telemetry["packet_loss_percent"])
    except (ValueError, TypeError, KeyError):
        return ["Packet-loss measurement is missing or invalid"]

    # Packet loss is valid even when no ping replies arrive.
    if packet_loss >= 100:
        anomalies.append(
            f"Connectivity failure: {packet_loss}% packet loss"
        )
    elif packet_loss > PACKET_LOSS_THRESHOLD_PERCENT:
        anomalies.append(f"High packet loss: {packet_loss}%")

    # Latency may be unavailable when all pings fail.
    try:
        raw_latency = telemetry.get("avg_latency_ms", "")
        if raw_latency not in ("", None):
            latency = float(raw_latency)
            if latency > LATENCY_THRESHOLD_MS:
                anomalies.append(f"High latency: {latency} ms")
    except (ValueError, TypeError):
        anomalies.append("Latency measurement is invalid")

    # Throughput may be unavailable when connectivity fails.
    try:
        raw_throughput = telemetry.get("throughput_mbps", "")
        if raw_throughput not in ("", None):
            throughput = float(raw_throughput)
            if throughput < THROUGHPUT_THRESHOLD_MBPS:
                anomalies.append(f"Low throughput: {throughput} Mbps")
    except (ValueError, TypeError):
        anomalies.append("Throughput measurement is invalid")

    return anomalies


if __name__ == "__main__":
    telemetry = load_latest_telemetry()
    anomalies = detect_anomalies(telemetry)

    if anomalies:
        print("Potential anomalies:")
        for anomaly in anomalies:
            print("-", anomaly)
    else:
        print("Network appears healthy.")
