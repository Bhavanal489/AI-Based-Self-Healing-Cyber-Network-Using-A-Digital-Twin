
from collections import deque
import csv
from pathlib import Path
from datetime import datetime


class DigitalTwin:
    def __init__(self):
        # Virtual representation of the network topology
        self.topology = {
    "hosts": ["h1", "h2"],
    "switches": ["s1", "s2", "s3"],
    "links": [
        ("h1", "s1"),
        ("s1", "s2"),
        ("s2", "h2"),
        ("s1", "s3"),
        ("s3", "s2")
             ]
         }
    # Latest observed network measurements
        self.state = {}

    def update_from_csv(self):
        csv_path = (
            Path(__file__).parent
            / "data"
            / "telemetry.csv"
        )

        if not csv_path.exists():
            print("Telemetry file not found.")
            print("Run collector.py first.")
            return False

        with open(csv_path, "r", newline="") as file:
            rows = list(csv.DictReader(file))

        if not rows:
            print("No telemetry records available.")
            return False

        # Use the most recently collected record
        latest = rows[-1]

        self.state = {
            "timestamp": latest["timestamp"],
            "source": latest["source"],
            "destination": latest["destination"],
            "avg_latency_ms": latest["avg_latency_ms"],
            "packet_loss_percent": latest[
                "packet_loss_percent"
            ],
            "throughput_mbps": latest["throughput_mbps"]
        }

        return True

    
    def find_path(self, source, destination, unavailable_link=None):
        """Find a path while optionally excluding one link."""

        graph = {
            node: []
            for node in (
                self.topology["hosts"] + self.topology["switches"]
            )
        }

        blocked_link = (
            frozenset(unavailable_link)
            if unavailable_link is not None
            else None
        )

        for u, v in self.topology["links"]:
            if blocked_link == frozenset((u, v)):
                continue

            graph[u].append(v)
            graph[v].append(u)

        if source not in graph or destination not in graph:
            return None

        queue = deque([(source, [source])])
        visited = {source}

        while queue:
            node, path = queue.popleft()

            if node == destination:
                return path

            for neighbour in graph[node]:
                if neighbour not in visited:
                    visited.add(neighbour)
                    queue.append((neighbour, path + [neighbour]))

        return None

    def validate_reroute(self, source, destination, failed_link):
        """Check whether an alternative path exists in the twin."""

        print("\n[Twin] Validating proposed alternative path...")

        path = self.find_path(
            source,
            destination,
            unavailable_link=failed_link
        )

        if path is None:
            print("[Twin] REJECTED: No alternative path exists.")
            return False

        print("[Twin] APPROVED: An alternative path exists.")
        print("[Twin] Candidate path:", " -> ".join(path))
        print("[Twin] This validates the model, not the live network.")
        return True

    def display(self):
        print("\n========== DIGITAL TWIN ==========")

        print("\n1. Represented topology")
        print("Hosts:", self.topology["hosts"])
        print("Switches:", self.topology["switches"])
        print("Links:")

        for source, destination in self.topology["links"]:
            print(f"  {source} <--> {destination}")

        print("\n2. Latest observed network state")

        if not self.state:
            print("No state available. Update the twin first.")
            return

        print("Timestamp:", self.state["timestamp"])
        print(
            f"Traffic path: {self.state['source']} -> "
            f"{self.state['destination']}"
        )
        print(
            "Average latency:",
            self.state["avg_latency_ms"], "ms"
        )
        print(
            "Packet loss:",
            self.state["packet_loss_percent"], "%"
        )
        print(
            "Throughput:",
            self.state["throughput_mbps"], "Mbps"
        )

        print("\n==================================")

    def run(self):
        if self.update_from_csv():
            self.display()


if __name__ == "__main__":
    twin = DigitalTwin()
    twin.run()
