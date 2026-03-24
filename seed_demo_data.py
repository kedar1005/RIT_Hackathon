"""
CitiZen AI — Demo Data Seeder
Run this script BEFORE the demo to populate the database with realistic data.
Usage: python seed_demo_data.py
"""
import os
import sys
import hashlib
from datetime import datetime, timedelta
import random

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.data_utils import (
    init_database, add_user, add_agent, add_complaint,
    update_complaint_status, add_correction, save_model_version,
    get_model_versions
)


def seed_demo_data():
    """Seed the database with demo complaints, agents, and model versions."""
    print("🚀 CitiZen AI — Demo Data Seeder")
    print("=" * 50)

    # Initialize database
    init_database()
    print("✅ Database initialized")

    # ─── SEED USERS ────────────────────────────────────────────────────
    users = [
        ("Priya Sharma", "priya@email.com", "test123"),
        ("Rahul Desai", "rahul@email.com", "test123"),
        ("Anita Patil", "anita@email.com", "test123"),
        ("Vikram Singh", "vikram@email.com", "test123"),
        ("Neha Gupta", "neha@email.com", "test123"),
    ]

    user_ids = []
    for name, email, pw in users:
        pw_hash = hashlib.sha256(pw.encode()).hexdigest()
        uid = add_user(name, email, pw_hash)
        if uid:
            user_ids.append(uid)
            print(f"  👤 User: {name} ({email})")
        else:
            print(f"  ⚠️  User {email} already exists, skipping")
            user_ids.append(1)

    # ─── SEED AGENTS ────────────────────────────────────────────────────
    agents = [
        ("Officer Mehta", "AGT0001", "agent123", "Roads & Infrastructure"),
        ("Inspector Kaur", "AGT0002", "agent123", "Sanitation & Waste"),
        ("Agent Reddy", "AGT0003", "agent123", "Electricity & Streetlights"),
        ("Field Officer Joshi", "AGT0004", "agent123", "Water Supply"),
    ]

    for name, aid, pw, dept in agents:
        pw_hash = hashlib.sha256(pw.encode()).hexdigest()
        result = add_agent(name, aid, pw_hash, dept)
        if result:
            print(f"  🛡️  Agent: {name} ({aid})")
        else:
            print(f"  ⚠️  Agent {aid} already exists, skipping")

    print()

    # ─── SEED COMPLAINTS ─────────────────────────────────────────────
    # Generate coordinates around Ratnagiri, Maharashtra (sample Indian city)
    base_lat, base_lon = 17.0005, 73.3001

    complaints = [
        # HIGH URGENCY (5)
        {
            "category": "Water Supply Issues",
            "description": "Major water pipeline burst on MG Road near city hospital. Entire street flooded with water. Vehicles stuck, pedestrians unable to cross. Contaminated water mixing with road drainage. Emergency repair needed immediately.",
            "address": "MG Road, Near City Hospital, Ratnagiri",
            "landmark": "Opposite State Bank",
            "urgency": "High",
            "lat": base_lat + 0.005, "lon": base_lon + 0.003
        },
        {
            "category": "Tree Fall & Maintenance",
            "description": "Large banyan tree fallen across main road after heavy winds last night. Completely blocking traffic both ways. Tree has fallen on power lines causing sparking. Extremely dangerous situation. Fire risk.",
            "address": "Station Road, Near Railway Crossing",
            "landmark": "Near Ganesh Temple",
            "urgency": "High",
            "lat": base_lat - 0.003, "lon": base_lon + 0.007
        },
        {
            "category": "Streetlight & Electricity",
            "description": "Exposed high-voltage wires hanging dangerously low near school entrance. Children walk past this area daily. Wire touching metal railing. Sparking observed during rain. Electrocution risk very high.",
            "address": "School Lane, Sector 5",
            "landmark": "Near Government School",
            "urgency": "High",
            "lat": base_lat + 0.008, "lon": base_lon - 0.002
        },
        {
            "category": "Roads & Potholes",
            "description": "Massive sinkhole has formed on highway near bus stop. Almost 3 feet deep and 5 feet wide. A motorcycle accident already happened here yesterday. Very dangerous at night with no warning signs.",
            "address": "NH-66, Near Bus Stand",
            "landmark": "Near Petrol Pump",
            "urgency": "High",
            "lat": base_lat - 0.006, "lon": base_lon + 0.010
        },
        {
            "category": "Drainage & Water Logging",
            "description": "Sewage overflow from main drainage line. Raw sewage flowing on residential streets. Unbearable smell. Health hazard for entire colony. Mosquito breeding ground. Multiple families affected. Disease outbreak risk.",
            "address": "New Colony, Ward 12",
            "landmark": "Behind Market Complex",
            "urgency": "High",
            "lat": base_lat + 0.002, "lon": base_lon - 0.005
        },

        # MEDIUM URGENCY (8)
        {
            "category": "Garbage & Waste Management",
            "description": "Community dustbin overflowing for 3 days. Garbage scattered by stray dogs. Bad smell spreading to nearby shops. Flies everywhere. Regular collection has been missed repeatedly this week.",
            "address": "Main Market, Tilak Chowk",
            "landmark": "Near Post Office",
            "urgency": "Medium",
            "lat": base_lat + 0.004, "lon": base_lon + 0.008
        },
        {
            "category": "Streetlight & Electricity",
            "description": "Dim streetlight on residential street barely providing any illumination. Flickering on and off. Multiple complaints from women residents about safety concerns. Bulb needs replacement urgently.",
            "address": "Savarkar Road, Lane 3",
            "landmark": "Near Shiv Temple",
            "urgency": "Medium",
            "lat": base_lat - 0.001, "lon": base_lon + 0.004
        },
        {
            "category": "Drainage & Water Logging",
            "description": "Storm drain near market area getting blocked frequently. Moderate waterlogging after every rain. Water enters some ground floor shops. Drain needs cleaning and widening. Garbage clogging the inlet.",
            "address": "Market Road, Near Vegetable Market",
            "landmark": "Opposite Municipal Office",
            "urgency": "Medium",
            "lat": base_lat + 0.007, "lon": base_lon - 0.003
        },
        {
            "category": "Traffic & Parking",
            "description": "Traffic signal at main junction malfunctioning. Green light timing too short during rush hour causing long queues. Accidents have increased at this intersection. Signal needs recalibration.",
            "address": "Main Junction, Clock Tower Circle",
            "landmark": "Near Clock Tower",
            "urgency": "Medium",
            "lat": base_lat - 0.004, "lon": base_lon + 0.006
        },
        {
            "category": "Public Safety & Others",
            "description": "Construction site noise continuing past 10 PM. Heavy machinery operating at night. Disturbing sleep of entire neighbourhood. Children and elderly residents suffering. No construction permit displayed.",
            "address": "Patel Nagar, Plot 45",
            "landmark": "Near Community Hall",
            "urgency": "Medium",
            "lat": base_lat + 0.009, "lon": base_lon + 0.001
        },
        {
            "category": "Roads & Potholes",
            "description": "Series of potholes forming on internal colony road after recent rain. Road surface deteriorating. Vehicles getting damaged. Speed is reduced. Road needs proper resurfacing not just patchwork.",
            "address": "Gandhi Nagar, Main Internal Road",
            "landmark": "Near Water Tank",
            "urgency": "Medium",
            "lat": base_lat - 0.002, "lon": base_lon - 0.006
        },
        {
            "category": "Water Supply Issues",
            "description": "Water pressure very low during morning peak hours 6-9 AM. Barely a trickle from taps. Upper floor residents getting almost no water. Possible pipeline leak or insufficient pumping capacity.",
            "address": "Shivaji Nagar, Block C",
            "landmark": "Near Children Park",
            "urgency": "Medium",
            "lat": base_lat + 0.006, "lon": base_lon + 0.009
        },
        {
            "category": "Garbage & Waste Management",
            "description": "Garbage collection truck not following schedule. Supposed to come daily but visits only 2-3 times a week. Bags pile up on the street. Stray animals tear them open. Need regular schedule adherence.",
            "address": "Nehru Colony, Gate 2",
            "landmark": "Near Community Garden",
            "urgency": "Medium",
            "lat": base_lat - 0.005, "lon": base_lon + 0.002
        },

        # LOW URGENCY (7)
        {
            "category": "Public Safety & Others",
            "description": "Park maintenance needed. Grass uncut for weeks, overgrown and unkempt. Park benches need painting. Playground equipment slightly rusty. Overall maintenance required for community park.",
            "address": "Central Park, Sector 8",
            "landmark": "Main entrance near library",
            "urgency": "Low",
            "lat": base_lat + 0.003, "lon": base_lon - 0.004
        },
        {
            "category": "Water Supply Issues",
            "description": "Water meter showing incorrect readings. Bills seem higher than actual usage. Meter might need calibration or replacement. Not urgent but needs checking during routine maintenance visit.",
            "address": "Tilak Nagar, House 42",
            "landmark": "Near Corner Shop",
            "urgency": "Low",
            "lat": base_lat - 0.007, "lon": base_lon + 0.005
        },
        {
            "category": "Traffic & Parking",
            "description": "Parking signs faded and barely readable near market area. Need repainting with reflective paint. Current signs are old and weathered. New signs would help with parking management.",
            "address": "Market Area, Parking Zone B",
            "landmark": "Near Cinema Hall",
            "urgency": "Low",
            "lat": base_lat + 0.001, "lon": base_lon + 0.011
        },
        {
            "category": "Tree Fall & Maintenance",
            "description": "Row of trees along boulevard need routine pruning. Lower branches hanging over walkway. Leaves accumulating on sidewalk. No immediate danger but scheduled maintenance would improve the area.",
            "address": "Laxmi Road, Boulevard Section",
            "landmark": "Near College Gate",
            "urgency": "Low",
            "lat": base_lat - 0.008, "lon": base_lon - 0.001
        },
        {
            "category": "Roads & Potholes",
            "description": "Minor pothole forming near colony entrance. Currently small but could worsen with rain. No immediate danger to vehicles. Preventive patching recommended before monsoon season.",
            "address": "Green Colony, Gate Entrance",
            "landmark": "Near Security Booth",
            "urgency": "Low",
            "lat": base_lat + 0.010, "lon": base_lon + 0.004
        },
        {
            "category": "Garbage & Waste Management",
            "description": "Request for additional garbage bin near new bus stop. Current nearest bin is 200 meters away. People leaving litter around bus stop. A dedicated bin would help keep the area clean.",
            "address": "NH-66, New Bus Stop",
            "landmark": "Near Highway Dhaba",
            "urgency": "Low",
            "lat": base_lat - 0.009, "lon": base_lon + 0.008
        },
        {
            "category": "Roads & Potholes",
            "description": "Road marking and lane dividers faded on main bypass road. White and yellow lines barely visible. Repainting needed for safe night driving. Low urgency as road is relatively new otherwise.",
            "address": "City Bypass Road, Km 3",
            "landmark": "Near Toll Plaza",
            "urgency": "Low",
            "lat": base_lat + 0.011, "lon": base_lon - 0.007
        },
    ]

    print("📋 Seeding complaints...")
    complaint_ids = []
    for i, c in enumerate(complaints):
        uid = user_ids[i % len(user_ids)]
        cid = add_complaint(
            user_id=uid,
            category=c["category"],
            description=c["description"],
            address=c["address"],
            landmark=c["landmark"],
            image_path=None,
            image_hash=None,
            lat=c["lat"],
            lon=c["lon"],
            ai_urgency=c["urgency"],
            user_urgency=c["urgency"],
            ai_confidence=round(random.uniform(0.65, 0.95), 2),
            ai_method="text",
            estimated_resolution={
                "High": "6 hours", "Medium": "2 days", "Low": "4 days"
            }[c["urgency"]]
        )
        if cid:
            complaint_ids.append(cid)
            status_emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}[c["urgency"]]
            print(f"  {status_emoji} #{cid:04d} [{c['urgency']}] {c['category'][:35]}")

    # Update some complaints to In Progress and Resolved
    if len(complaint_ids) >= 10:
        # Set some to In Progress
        for cid in complaint_ids[2:5]:
            update_complaint_status(cid, "In Progress", "AGT0001", "Agent assigned and investigating")
            print(f"  🔄 #{cid:04d} → In Progress")

        # Set some to Resolved
        for cid in complaint_ids[5:8]:
            update_complaint_status(cid, "In Progress", "AGT0002", "Work started")
            update_complaint_status(cid, "Resolved", "AGT0002", "Issue has been resolved. Team dispatched and work completed.")
            print(f"  ✅ #{cid:04d} → Resolved")

    print()

    # ─── SEED CORRECTIONS ───────────────────────────────────────────────
    print("✏️  Seeding AI corrections (15 total)...")

    correction_data = [
        # Category was wrong (5)
        ("Roads & Potholes", "Drainage & Water Logging", "High", "High"),
        ("Garbage & Waste Management", "Public Safety & Others", "Medium", "Medium"),
        ("Water Supply Issues", "Drainage & Water Logging", "High", "High"),
        ("Streetlight & Electricity", "Public Safety & Others", "Medium", "Medium"),
        ("Tree Fall & Maintenance", "Roads & Potholes", "Medium", "Medium"),
        # Urgency was wrong (5)
        ("Roads & Potholes", "Roads & Potholes", "Medium", "High"),
        ("Garbage & Waste Management", "Garbage & Waste Management", "Low", "Medium"),
        ("Water Supply Issues", "Water Supply Issues", "Medium", "High"),
        ("Streetlight & Electricity", "Streetlight & Electricity", "Low", "Medium"),
        ("Drainage & Water Logging", "Drainage & Water Logging", "Medium", "High"),
        # Both wrong (5)
        ("Roads & Potholes", "Water Supply Issues", "Low", "High"),
        ("Garbage & Waste Management", "Drainage & Water Logging", "Low", "Medium"),
        ("Public Safety & Others", "Tree Fall & Maintenance", "Medium", "High"),
        ("Traffic & Parking", "Roads & Potholes", "Low", "Medium"),
        ("Streetlight & Electricity", "Public Safety & Others", "Medium", "High"),
    ]

    for i, (orig_cat, corr_cat, orig_urg, corr_urg) in enumerate(correction_data):
        cid = complaint_ids[i % len(complaint_ids)] if complaint_ids else 1
        success = add_correction(
            complaint_id=cid,
            original_prediction=orig_cat,
            corrected_label=corr_cat,
            original_urgency=orig_urg,
            corrected_urgency=corr_urg,
            corrected_by="AGT0001",
            description=f"Demo correction {i+1}",
            category=corr_cat
        )
        if success:
            print(f"  ✏️  Correction {i+1}: {orig_cat[:20]}→{corr_cat[:20]} | {orig_urg}→{corr_urg}")

    print()

    # ─── SEED MODEL VERSIONS ──────────────────────────────────────────
    print("📦 Seeding model versions...")

    existing = get_model_versions()
    if len(existing) == 0:
        save_model_version(
            version_num=1,
            total_samples=135,
            real_samples=0,
            accuracy=0.74,
            correction_samples=0,
            notes="Initial synthetic training"
        )
        print("  📦 v1: accuracy=74.0%, samples=135 (initial)")

        save_model_version(
            version_num=2,
            total_samples=150,
            real_samples=20,
            accuracy=0.87,
            correction_samples=15,
            notes="Retrained with 15 agent corrections"
        )
        print("  📦 v2: accuracy=87.0%, samples=150 (with corrections)")
    else:
        print("  ⚠️  Model versions already exist, skipping")

    print()
    print("=" * 50)
    print("✅ Demo data seeding complete!")
    print()
    print("📌 Demo Login Credentials:")
    print("   Citizen: priya@email.com / test123")
    print("   Agent:   AGT0001 / agent123")
    print()
    print("🚀 Launch the app with: streamlit run main.py")


if __name__ == "__main__":
    seed_demo_data()
