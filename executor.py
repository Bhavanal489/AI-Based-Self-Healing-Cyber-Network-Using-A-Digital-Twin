
import re
import time


def execute_recovery(net, action="use_backup"):
    """Apply and verify a recovery action on the running Mininet network."""

    if action != "use_backup":
        print(f"[Executor] Unsupported action: {action}")
        return False

    print("\n[Executor] Starting backup-path recovery...")

    try:
        h1 = net.get("h1")

        # Keep the failed primary link unavailable.
        print("[Executor] Keeping primary link s1-s2 DOWN...")
        net.configLinkStatus("s1", "s2", "down")

        # Enable both links needed by the backup path.
        print("[Executor] Enabling backup links...")
        net.configLinkStatus("s1", "s3", "up")
        net.configLinkStatus("s3", "s2", "up")

        # Allow the switching topology time to settle.
        time.sleep(5)

        print("[Executor] Testing H1-to-H2 connectivity...")
        output = h1.cmd("ping -c 5 -W 2 10.0.0.2")
        print(output)

        match = re.search(r"(\d+(?:\.\d+)?)%\s*packet loss", output)

        if match and float(match.group(1)) == 0:
            print("[Executor] SUCCESS: H1 can reach H2.")
            print("[Executor] Primary link remains DOWN.")
            print("[Executor] Backup-path recovery passed connectivity verification.")
            return True

        print("[Executor] FAILED: Connectivity was not restored.")
        return False

    except Exception as error:
        print(f"[Executor] Recovery error: {error}")
        return False
