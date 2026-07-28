"""Realistic seed data for demos, tests, and pilot conversations.

Parts lists are based on common residential HVAC truck stock
(capacitors, contactors, filters, motors, etc.).
"""

from __future__ import annotations

from truck_ready.core import default_parts_for_job_type
from truck_ready.models import InventoryItem, Job


def demo_inventory() -> list[InventoryItem]:
    """Typical mixed truck + shop stock for a small residential HVAC shop."""
    return [
        InventoryItem(
            sku="CAP-45-5",
            name="Dual Run Capacitor 45/5 MFD",
            quantity=6,
            reorder_point=4,
            unit_cost=12.50,
            category="electrical",
        ),
        InventoryItem(
            sku="CAP-35-5",
            name="Dual Run Capacitor 35/5 MFD",
            quantity=4,
            reorder_point=3,
            unit_cost=11.75,
            category="electrical",
        ),
        InventoryItem(
            sku="CAP-40-5",
            name="Dual Run Capacitor 40/5 MFD",
            quantity=2,
            reorder_point=3,
            unit_cost=12.00,
            category="electrical",
        ),
        InventoryItem(
            sku="CONT-30A",
            name="Contactor 30A 1-Pole",
            quantity=5,
            reorder_point=3,
            unit_cost=18.00,
            category="electrical",
        ),
        InventoryItem(
            sku="CONT-40A",
            name="Contactor 40A 2-Pole",
            quantity=3,
            reorder_point=2,
            unit_cost=24.50,
            category="electrical",
        ),
        InventoryItem(
            sku="FILTER-20x25",
            name="Air Filter 20x25x1 MERV 8",
            quantity=18,
            reorder_point=10,
            unit_cost=4.25,
            category="filtration",
        ),
        InventoryItem(
            sku="FILTER-16x25",
            name="Air Filter 16x25x1 MERV 8",
            quantity=8,
            reorder_point=6,
            unit_cost=3.90,
            category="filtration",
        ),
        InventoryItem(
            sku="MTR-0.5HP",
            name="Condenser Fan Motor 1/2 HP",
            quantity=1,
            reorder_point=1,
            unit_cost=145.00,
            category="motors",
        ),
        InventoryItem(
            sku="BELT-48",
            name='Blower Belt 48"',
            quantity=3,
            reorder_point=2,
            unit_cost=9.50,
            category="mechanical",
        ),
        InventoryItem(
            sku="LINESET-50",
            name="Line Set 50 ft",
            quantity=0,
            reorder_point=1,
            unit_cost=185.00,
            category="install",
        ),
        InventoryItem(
            sku="PAD-CONC",
            name="Concrete Pad",
            quantity=2,
            reorder_point=1,
            unit_cost=42.00,
            category="install",
        ),
        InventoryItem(
            sku="WHIP-6/3",
            name="Disconnect Whip 6/3",
            quantity=1,
            reorder_point=1,
            unit_cost=28.00,
            category="electrical",
        ),
        InventoryItem(
            sku="HARDSTART",
            name="Hard Start Kit",
            quantity=4,
            reorder_point=2,
            unit_cost=22.00,
            category="electrical",
        ),
        InventoryItem(
            sku="TXV-3TON",
            name="TXV 3-Ton",
            quantity=1,
            reorder_point=1,
            unit_cost=95.00,
            category="refrigeration",
        ),
    ]


def demo_jobs() -> list[Job]:
    """A realistic day for a 3-truck residential shop."""
    return [
        Job(
            job_id="JOB-1001",
            job_type="Emergency_Repair",
            customer_name="Martinez Residence",
            scheduled_date="2026-07-28",
            assigned_tech="TCH-01",
            required_parts=default_parts_for_job_type("Emergency_Repair"),
            notes="No-cool call, older 3-ton unit",
        ),
        Job(
            job_id="JOB-1002",
            job_type="HVAC_Maintenance",
            customer_name="Chen Residence",
            scheduled_date="2026-07-28",
            assigned_tech="TCH-02",
            required_parts=default_parts_for_job_type("HVAC_Maintenance"),
            notes="Seasonal tune-up + filter change",
        ),
        Job(
            job_id="JOB-1003",
            job_type="Heat_Pump_Install",
            customer_name="Patel Residence",
            scheduled_date="2026-07-28",
            assigned_tech="TCH-01",
            required_parts=default_parts_for_job_type("Heat_Pump_Install"),
            notes="3-ton heat pump change-out",
        ),
        Job(
            job_id="JOB-1004",
            job_type="Emergency_Repair",
            customer_name="Sullivan Residence",
            scheduled_date="2026-07-28",
            assigned_tech="TCH-03",
            required_parts=default_parts_for_job_type("Emergency_Repair"),
            notes="Intermittent cooling, possible capacitor",
        ),
    ]
