
from ai_detector import detect_anomalies
from digital_twin import DigitalTwin
from live_collector import collect_live_telemetry


def plan_recovery(telemetry, anomalies):
    """Choose a recovery action based on telemetry and detected anomalies."""

    if not telemetry:
        return {
            "action": "manual_investigation",
            "reason": "No valid telemetry available."
        }

    if not anomalies:
        return {
            "action": "none",
            "reason": "No anomaly detected."
        }

    try:
        packet_loss = float(telemetry.get("packet_loss_percent"))
    except (ValueError, TypeError):
        packet_loss = None

    try:
        latency = float(telemetry.get("avg_latency_ms"))
    except (ValueError, TypeError):
        latency = None

    try:
        throughput = float(telemetry.get("throughput_mbps"))
    except (ValueError, TypeError):
        throughput = None

    # Severe connectivity failure: propose backup route.
    if packet_loss is not None and packet_loss >= 50:
        return {
            "action": "reroute_candidate",
            "source": "h1",
            "destination": "h2",
            "avoid_link": ("s1", "s2"),
            "reason": (
                "Severe packet loss detected. "
                "Check an alternative path in the Digital Twin."
            )
        }

    if packet_loss is not None and packet_loss > 5:
        return {
            "action": "investigate_connectivity",
            "reason": "High packet loss detected."
        }

    if latency is not None and latency > 50:
        return {
            "action": "investigate_performance",
            "reason": "High latency detected."
        }

    if throughput is not None and throughput < 10:
        return {
            "action": "investigate_performance",
            "reason": "Low throughput detected."
        }

    return {
        "action": "manual_investigation",
        "reason": "An anomaly was detected; no matching recovery rule."
    }


def plan_from_live_network(net):
    """Collect live telemetry, detect link failures, and plan recovery."""

    print("\n=== Self-Healing Decision Cycle ===")
    print("\n[Collector] Collecting fresh telemetry...")

    telemetry = collect_live_telemetry(net)

    if not telemetry:
        print("[Planner] No telemetry available.")
        return None

    print(f"Latency (ms): {telemetry.get('avg_latency_ms')}")
    print(f"Packet loss (%): {telemetry.get('packet_loss_percent')}")
    print(f"Throughput (Mbps): {telemetry.get('throughput_mbps')}")

    # Check the primary link independently of end-to-end connectivity.
    # STP may keep traffic flowing through the backup path.
    try:
        s1 = net.get("s1")
        s2 = net.get("s2")

        primary_down = (
            not s1.intf("s1-eth2").isUp()
            or not s2.intf("s2-eth2").isUp()
        )
    except Exception as error:
        print(f"[Detector] Could not inspect primary link: {error}")
        primary_down = False

    if primary_down:
        print("[Detector] Primary link s1-s2 is DOWN.")

        proposal = {
            "action": "reroute_candidate",
            "source": "h1",
            "destination": "h2",
            "avoid_link": ("s1", "s2"),
            "reason": "Primary link failure detected."
        }

        twin = DigitalTwin()
        twin.update_from_csv()

        print("[Twin] Validating backup path...")

        approved = twin.validate_reroute(
            "h1",
            "h2",
            ("s1", "s2")
        )

        if approved:
            print("[Planner] Backup-path proposal approved.")
            return proposal

        print("[Planner] Digital Twin rejected the proposal.")
        return None

    # Normal anomaly detection when the primary link is operational.
    anomalies = detect_anomalies(telemetry)

    print("\n[Detector] Results:")
    if anomalies:
        for anomaly in anomalies:
            print(f"- {anomaly}")
    else:
        print("No anomalies detected.")

    proposal = plan_recovery(telemetry, anomalies)

    print(f"\n[Planner] Proposed action: {proposal['action']}")
    print(f"[Planner] Reason: {proposal['reason']}")

    # Validate any proposed reroute before returning it.
    if proposal.get("action") == "reroute_candidate":
        twin = DigitalTwin()
        twin.update_from_csv()

        approved = twin.validate_reroute(
            proposal["source"],
            proposal["destination"],
            proposal["avoid_link"]
        )

        if not approved:
            print("[Planner] Digital Twin rejected the proposal.")
            return None

        print("[Planner] Backup-path proposal approved.")

    return proposal
