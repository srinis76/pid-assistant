"""
Mock ticket data for P&ID Digital Assistant MVP
Hardcoded maintenance ticket information for demonstration
"""
from typing import Optional, Dict


# Hardcoded mock ticket data
MOCK_TICKETS = {
    "PSV-101": {
        "equipment": "V-101 (High Pressure Separator)",
        "issue": "Safety valve actuator slow response",
        "reported": "2025-09-15",
        "resolution": "Actuator replaced and calibrated per manufacturer specs",
        "resolved": "2025-09-16",
        "status": "Closed",
        "priority": "High"
    },
    "FT-103A": {
        "equipment": "P-103 (Export Pump)",
        "issue": "Flow transmitter reading erratic",
        "reported": "2025-10-01",
        "resolution": "Transmitter recalibrated, impulse lines cleared",
        "resolved": "2025-10-02",
        "status": "Closed",
        "priority": "Medium"
    },
    "V-102": {
        "equipment": "V-102 (Low Pressure Separator)",
        "issue": "Separator pressure relief valve set point verification",
        "reported": "2025-10-10",
        "resolution": "PSV-102 tested and verified at 75 PSIG set pressure",
        "resolved": "2025-10-10",
        "status": "Closed",
        "priority": "Low"
    },
    "V-101": {
        "equipment": "V-101 (High Pressure Separator)",
        "issue": "High-level alarm testing and calibration",
        "reported": "2025-09-20",
        "resolution": "LSHH-101B tested and calibrated, alarm set at 85% level",
        "resolved": "2025-09-21",
        "status": "Closed",
        "priority": "Medium"
    },
    "C-104": {
        "equipment": "C-104 (Gas Compressor)",
        "issue": "Vibration sensor alarm during startup",
        "reported": "2025-09-28",
        "resolution": "False alarm, sensor recalibrated, no mechanical issues found",
        "resolved": "2025-09-29",
        "status": "Closed",
        "priority": "High"
    }
}


def get_ticket(tag_or_equipment: str) -> Optional[Dict]:
    """
    Get mock ticket for a tag or equipment

    Args:
        tag_or_equipment: Tag ID (e.g., "PSV-101") or equipment ID (e.g., "V-101")

    Returns:
        Ticket dict or None if not found
    """
    return MOCK_TICKETS.get(tag_or_equipment.upper())


def format_ticket(ticket: Dict) -> Dict:
    """
    Format ticket for display

    Returns:
        Dict with formatted ticket data for rendering
    """
    status_emoji = "✅" if ticket["status"] == "Closed" else "⚠️"

    # Return structured data instead of formatted string
    return {
        "equipment": ticket['equipment'],
        "issue": ticket['issue'],
        "status": ticket['status'],
        "status_emoji": status_emoji,
        "priority": ticket['priority'],
        "reported": ticket['reported'],
        "resolved": ticket['resolved'],
        "resolution": ticket['resolution']
    }


# Test function
if __name__ == "__main__":
    # Test ticket retrieval
    print("Testing mock ticket data...")
    print("\n" + "="*50)

    test_tags = ["PSV-101", "V-101", "FT-103A", "C-104", "UNKNOWN"]

    for tag in test_tags:
        ticket = get_ticket(tag)
        if ticket:
            print(f"\n✓ Found ticket for {tag}:")
            print(format_ticket(ticket))
        else:
            print(f"\n✗ No ticket found for {tag}")

    print("="*50)
