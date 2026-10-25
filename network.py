from executor import execute_recovery
from recovery_planner import plan_from_live_network
from live_collector import collect_live_telemetry
from executor import execute_recovery
from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import OVSBridge
from mininet.cli import CLI
from mininet.log import setLogLevel


class SelfHealingTopo(Topo):
    def build(self):
        self.addHost("h1")
        self.addHost("h2")

        self.addSwitch("s1", stp=True)
        self.addSwitch("s2", stp=True)
        self.addSwitch("s3", stp=True)

        self.addLink("h1", "s1")
        self.addLink("s2", "h2")

        # Primary path
        self.addLink("s1", "s2")

        # Backup path
        self.addLink("s1", "s3")
        self.addLink("s3", "s2")


class SelfHealingCLI(CLI):
    def do_recover(self, line):
        """Run the recovery executor on the active network."""
        action = line.strip() or "restore_primary"
        execute_recovery(self.mn, action)
    def do_telemetry(self, line):
        """Collect fresh measurements from the active network."""
        collect_live_telemetry(self.mn)    
    
    def do_decide(self, line):
        """Collect telemetry, plan recovery, and execute approved proposals."""

        proposal = plan_from_live_network(self.mn)

        if not proposal:
            print("[System] No approved recovery action to execute.")
            return

        if proposal.get("action") != "reroute_candidate":
            print("[System] No executable reroute proposal.")
            return

        print("\n[System] Digital Twin approved the candidate.")
        success = execute_recovery(self.mn, action="use_backup")

        if success:
            print("[System] Recovery completed and connectivity verified.")
        else:
            print("[System] Recovery verification failed.")
    def do_checklinks(self, line):
        """Detect links that are administratively down in Mininet."""
        print("\n[Fault Detector] Checking network links...")

        for link in self.mn.links:
            intf1 = link.intf1
            intf2 = link.intf2

            if not intf1.isUp() or not intf2.isUp():
               print(
                f"[Fault Detector] Link DOWN: "
                f"{intf1.node.name} <-> {intf2.node.name}"
               )

        print("[Fault Detector] Link check complete.")
def run_network():
    topo = SelfHealingTopo()
    net = Mininet(
        topo=topo,
        switch=OVSBridge,
        controller=None,
        autoSetMacs=True
    )

    net.start()

    try:
        print("\nNetwork started successfully!")
        print("Hosts:", net.hosts)
        print("Switches:", net.switches)
        SelfHealingCLI(net)
    finally:
        net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    run_network()
