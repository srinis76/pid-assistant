"""
Mock ticket data for P&ID Assistant MVP
Hardcoded maintenance ticket information for demonstration
"""
from datetime import date, timedelta
from typing import Optional, Dict


def _ago(days: int) -> str:
    return (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")


# Dates are computed relative to today so the data never looks stale in demos
MOCK_TICKETS = {
    "PSV-101": {
        "equipment": "V-101 (High Pressure Separator)",
        "issue": "Safety valve actuator slow response",
        "reported": _ago(45),
        "resolution": "Actuator replaced and calibrated per manufacturer specs",
        "resolved": _ago(44),
        "status": "Closed",
        "priority": "High"
    },
    "FT-103A": {
        "equipment": "P-103 (Export Pump)",
        "issue": "Flow transmitter reading erratic",
        "reported": _ago(30),
        "resolution": "Transmitter recalibrated, impulse lines cleared",
        "resolved": _ago(29),
        "status": "Closed",
        "priority": "Medium"
    },
    "V-102": {
        "equipment": "V-102 (Low Pressure Separator)",
        "issue": "Separator pressure relief valve set point verification",
        "reported": _ago(21),
        "resolution": "PSV-102 tested and verified at 75 PSIG set pressure",
        "resolved": _ago(21),
        "status": "Closed",
        "priority": "Low"
    },
    "V-101": {
        "equipment": "V-101 (High Pressure Separator)",
        "issue": "High-level alarm testing and calibration",
        "reported": _ago(14),
        "resolution": "LSHH-101B tested and calibrated, alarm set at 85% level",
        "resolved": _ago(13),
        "status": "Closed",
        "priority": "Medium"
    },
    "C-104": {
        "equipment": "C-104 (Gas Compressor)",
        "issue": "Vibration sensor alarm during startup",
        "reported": _ago(8),
        "resolution": "False alarm, sensor recalibrated, no mechanical issues found",
        "resolved": _ago(7),
        "status": "Closed",
        "priority": "High"
    },
    "LT-101": {
        "equipment": "V-101 (High Pressure Separator)",
        "issue": "Level transmitter drifting above calibrated range — readings 8% above DCS reference",
        "reported": _ago(3),
        "resolution": None,
        "resolved": None,
        "status": "Open",
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
        "resolved": ticket.get('resolved') or "Pending",
        "resolution": ticket.get('resolution') or "Under investigation"
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
