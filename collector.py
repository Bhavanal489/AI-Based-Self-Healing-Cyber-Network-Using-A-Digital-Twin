
import csv
import re
import time
from datetime import datetime
from pathlib import Path

from mininet.net import Mininet
from mininet.node import OVSBridge
from mininet.log import setLogLevel

from network import SelfHealingTopo


def collect_telemetry():
    # Create the same topology defined in network.py
    net = Mininet(
        topo=SelfHealingTopo(),
        switch=OVSBridge,
        controller=None,
        autoSetMacs=True
    )

    try:
        # Start the network
        net.start()

        h1 = net.get("h1")
        h2 = net.get("h2")

        print("Network started. Waiting for connectivity...")
        print("Waiting 35 seconds for switches and STP...")
        time.sleep(35)
        # Wait for H1 to reach H2 before collecting metrics
        connected = False

        for attempt in range(10):
            test_output = h1.cmd("ping -c 1 -W 1 10.0.0.2")

            if "1 received" in test_output or "1 packets received" in test_output:
                connected = True
                break

        time.sleep(2)

        if not connected:
               print("ERROR: H1 cannot reach H2 after waiting.")
               print("Check Mininet connectivity and switch configuration.")
               print(test_output)
               return

        print("Connectivity confirmed. Collecting telemetry...")

        # 1. Measure latency and packet loss
        ping_output = h1.cmd("ping -c 5 -W 2 10.0.0.2")

        latency_match = re.search(
            r"=\s*[\d.]+/([\d.]+)/",
            ping_output
        )

        loss_match = re.search(
            r"([\d.]+)%\s*packet loss",
            ping_output
        )

        avg_latency = (
            float(latency_match.group(1))
            if latency_match else None
        )

        packet_loss = (
            float(loss_match.group(1))
            if loss_match else None
        )

        # 2. Measure throughput using iperf3
        server = h2.popen(["iperf3", "-s"])

        try:
            time.sleep(1)

            iperf_output = h1.cmd(
                "iperf3 -c 10.0.0.2 -t 5"
            )
        finally:
            server.terminate()
            server.wait()

        # Extract the receiver's bitrate
        throughput = None

        for line in iperf_output.splitlines():
            if "receiver" in line:
                match = re.search(
                    r"([\d.]+)\s+(Kbits/sec|Mbits/sec|Gbits/sec)\s+receiver",
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

                    break

        # 3. Prepare one telemetry record
        record = {
            "timestamp": datetime.now().isoformat(
                timespec="seconds"
            ),
            "source": "h1",
            "destination": "h2",
            "avg_latency_ms": avg_latency,
            "packet_loss_percent": packet_loss,
            "throughput_mbps": throughput
        }

        # 4. Save the record to CSV
        csv_path = (
            Path(__file__).parent
            / "data"
            / "telemetry.csv"
        )

        csv_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        columns = list(record.keys())
        file_exists = csv_path.exists()

        with open(csv_path, "a", newline="") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=columns
            )

            if not file_exists or csv_path.stat().st_size == 0:
                writer.writeheader()

            writer.writerow(record)

        print("\nTelemetry collected:")
        for key, value in record.items():
            print(f"{key}: {value}")

        print(f"\nSaved to: {csv_path}")

    finally:
        # Stop the Mininet network
        net.stop()


if __name__ == "__main__":
    setLogLevel("warning")
    collect_telemetry()

