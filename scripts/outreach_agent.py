#!/usr/bin/env python3
"""
APEX LinkedIn & Executive Outreach Execution Engine
Doctrine: Zero Improvisation · Strict Approved Templates · State Machine Tracking
"""

import sys
import os
import argparse
import json
import sqlite3
from datetime import datetime

PIPELINE_FILE = "/root/job-app-helix/artifacts/LINKEDIN_OUTREACH_PIPELINE.json"
DB_PATH = "/root/job-app-helix/artifacts/application-operations.sqlite3"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def load_spec():
    with open(PIPELINE_FILE, "r") as f:
        return json.load(f)

def cmd_status(args):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT target, company, role, contact_name, platform, status, next_action, next_action_date, notion_url FROM outreach_pipeline;")
    rows = cur.fetchall()
    conn.close()

    print("==========================================================================================")
    print(" 🚀 APEX LINKEDIN & EXECUTIVE OUTREACH PIPELINE STATUS")
    print(f" Telemetry Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Rate Limit: 5 Conns/day, 3 DMs/day")
    print("==========================================================================================")
    for r in rows:
        print(f"\n[{r['company'].upper()}] - {r['role']}")
        print(f"  Target Key    : {r['target']}")
        print(f"  Contact       : {r['contact_name']}")
        print(f"  Platform      : {r['platform']}")
        print(f"  Status        : {r['status'].upper()}")
        print(f"  Next Action   : {r['next_action']} ({r['next_action_date']})")
        print(f"  Notion Spec   : {r['notion_url']}")
    print("\nMaster Notion URL: https://app.notion.com/p/3f4b1e4f322381408dc2da3735a3d0ba")

def cmd_target(args):
    target_key = args.name.lower()
    spec = load_spec()
    t = spec["targets"].get(target_key)
    if not t:
        print(f"Error: Target '{target_key}' not found. Available: {list(spec['targets'].keys())}")
        sys.exit(1)

    print("==========================================================================================")
    print(f" 🎯 TARGET SPEC: {t['company']} ({t['role']})")
    print("==========================================================================================")
    print(f"Contact Name    : {t['primary_contact']}")
    print(f"Status          : {t['status'].upper()}")
    print(f"Notion URL      : {t['notion_url']}")
    print("\n--- SEARCH QUERIES ---")
    print(f"Primary Search  : {t['primary_search']}")
    if "secondary_search" in t:
        print(f"Secondary Search: {t['secondary_search']}")
    print("\n--- CONNECTION NOTE (Send with Connection Request) ---")
    print(t.get("connection_note", "None"))
    print("\n--- APPROVED MESSAGE (Send via InMail or Post-Acceptance DM) ---")
    print(t.get("approved_message", "None"))

def cmd_prompt(args):
    spec = load_spec()
    print("==========================================================================================")
    print(" 🤖 AGENT SYSTEM PROMPT (Copy-Paste Ready for Browser Agent)")
    print("==========================================================================================")
    print(spec["system_prompt"])

def cmd_update(args):
    conn = get_db()
    cur = conn.cursor()
    updates = []
    params = []
    if args.status:
        updates.append("status = ?")
        params.append(args.status)
    if args.notes:
        updates.append("notes = ?")
        params.append(args.notes)
    if args.next_action:
        updates.append("next_action = ?")
        params.append(args.next_action)
    if args.next_action_date:
        updates.append("next_action_date = ?")
        params.append(args.next_action_date)

    if not updates:
        print("No updates specified.")
        return

    params.append(args.target.lower())
    sql = f"UPDATE outreach_pipeline SET {', '.join(updates)} WHERE target = ?;"
    cur.execute(sql, params)
    conn.commit()
    conn.close()
    print(f"Successfully updated target '{args.target}'.")

def main():
    parser = argparse.ArgumentParser(description="APEX LinkedIn Outreach Execution Engine")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("status", help="Show status of all targets")
    p_prompt = subparsers.add_parser("prompt", help="Print agent system prompt")

    p_target = subparsers.add_parser("target", help="Show specific target spec and message")
    p_target.add_argument("name", help="Target name (supabase, harvey_ai, scale_ai, clickup)")

    p_update = subparsers.add_parser("update", help="Update target status in SQLite")
    p_update.add_argument("target", help="Target name")
    p_update.add_argument("--status", help="New status (pending, connection_sent, connected, messaged, replied, cold)")
    p_update.add_argument("--notes", help="Execution notes")
    p_update.add_argument("--next-action", help="Next scheduled action")
    p_update.add_argument("--next-action-date", help="Next action date (YYYY-MM-DD)")

    args = parser.parse_args()
    if args.command == "status" or not args.command:
        cmd_status(args)
    elif args.command == "prompt":
        cmd_prompt(args)
    elif args.command == "target":
        cmd_target(args)
    elif args.command == "update":
        cmd_update(args)

if __name__ == "__main__":
    main()
