
import csv
import re
import time
from pathlib import Path


CSV_PATH = Path(__file__).parent / "data" / "telemetry.csv"


def collect_live_telemetry(net):
    """Collect fresh measurements from an already-running Mininet network."""

    h1 = net.get("h1")
    h2 = net.get("h2")

    print("\n[Collector] Collecting fresh telemetry...")

    # Measure packet loss and average round-trip latency.
    ping_output = h1.cmd("ping -c 5 -W 2 10.0.0.2")
    print(ping_output)

    loss_match = re.search(
        r"(\d+(?:\.\d+)?)%\s*packet loss", ping_output
    )
    latency_match = re.search(
        r"rtt min/avg/max/(?:mdev|stddev) = "
        r"[\d.]+/([\d.]+)/", ping_output
    )

    if not loss_match:
        print("[Collector] Could not parse packet loss.")
        return None

    packet_loss = float(loss_match.group(1))
    latency = (
        float(latency_match.group(1))
        if latency_match and packet_loss < 100
        else None
    )

    # Measure throughput only when the hosts can communicate.
    throughput = None

    if packet_loss < 100:
        server = h2.popen(["iperf3", "-s"])
        try:
            time.sleep(1)
            output = h1.cmd(
                "iperf3 -c 10.0.0.2 -t 2"
            )

            # Prefer the receiver's reported bitrate.
            receiver_lines = [
                line for line in output.splitlines()
                if "receiver" in line.lower()
            ]

            for line in receiver_lines:
                match = re.search(
                    r"([\d.]+)\s+(Kbits/sec|Mbits/sec|Gbits/sec)",
                    line
                )
                if match:
                    value = float(match.group(1))
                    unit = match.group(2)
                    if unit == "Kbits/sec":
                        throughput = value / 1000
                    elif unit == "Gbits/sec":
                        throughput = value * 1000
                    else:
                        throughput = value
        finally:
            server.terminate()
            server.wait()

    # Write the latest measurement as a fresh CSV row.
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_exists = CSV_PATH.exists()

    with open(CSV_PATH, "a", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "timestamp",
                "source",
                "destination",
                "avg_latency_ms",
                "packet_loss_percent",
                "throughput_mbps",
            ],
        )

        if not file_exists or CSV_PATH.stat().st_size == 0:
            writer.writeheader()

        writer.writerow({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "h1",
            "destination": "h2",
            "avg_latency_ms": latency if latency is not None else "",
            "packet_loss_percent": packet_loss,
            "throughput_mbps": (
                throughput if throughput is not None else ""
            ),
        })

    print("[Collector] Fresh telemetry saved.")
    print("Latency (ms):", latency)
    print("Packet loss (%):", packet_loss)
    print("Throughput (Mbps):", throughput)

    return {
        "avg_latency_ms": latency,
        "packet_loss_percent": packet_loss,
        "throughput_mbps": throughput,
    }
