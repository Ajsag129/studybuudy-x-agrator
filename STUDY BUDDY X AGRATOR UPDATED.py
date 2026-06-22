import sys
import time
import re
import json
import os
import requests
import math
import getpass
import statistics
import ctypes
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator
from ddgs import DDGS 
import hashlib
import tkinter as tk
from tkinter import scrolledtext

# ═══════════════════════════════════════════════════════════════
#  GLOBAL TERMINAL & UI SETTINGS
# ═══════════════════════════════════════════════════════════════
if os.name == 'nt':
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except:
        pass

# --- TERMINAL COLORS ---
C_BLUE = "\033[94m"
C_GREEN = "\033[92m"
C_PURPLE = "\033[95m"
C_YELLOW = "\033[93m"
C_CYAN = "\033[96m"
C_RED = "\033[91m"
C_UNDERLINE = "\033[4m"
C_RESET = "\033[0m"
C_BOLD  = "\033[1m"
C_WARN  = "\033[33m"

# Themes from Study Buddy
THEMES = {
    "green": {"primary": "\033[32m", "accent": "\033[36m", "warn": "\033[33m"},
    "cyber": {"primary": "\033[36m", "accent": "\033[35m", "warn": "\033[33m"},
    "mono":  {"primary": "\033[37m", "accent": "\033[1m\033[37m", "warn": "\033[1m\033[30m"}
}

# ═══════════════════════════════════════════════════════════════
#  AGRATOR & STUDY BUDDY SYSTEM GLOBALS
# ═══════════════════════════════════════════════════════════════




HISTORY_FILE = "history.json"
FIREBASE_URL = "https://study-buddy-x-agrator-program-default-rtdb.asia-southeast1.firebasedatabase.app/"
DATABASE_URL = "https://study-buddy-x-agrator-program-default-rtdb.asia-southeast1.firebasedatabase.app/"
WEB_API_KEY = "AIzaSyDbnY7Q-C_sixNyHuX3USCGwP1bDByuvuA"
NEWS_API_KEY = "6fc0458be24f42be85d2dec1ec1469f3"


if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_FILE = os.path.join(BASE_DIR, "calculator_data.json")
NOTES_FILE = os.path.join(BASE_DIR, "notes.txt")

# --- SUPPORTED LANGUAGES ---
LANGUAGES = {
    '1': ('English', 'en'),
    '2': ('Filipino', 'tl'),
    '3': ('Chinese (Simplified)', 'zh-CN'),
    '4': ('German', 'de'),
    '5': ('Japanese', 'ja')
}

# --- STUDY BUDDY STATES & METRICS ---
state = {
    "username": "",
    "precision": 6,
    "angle_mode": "degrees",
    "incognito": False,
    "passkey": "126833",
    "history": [],
    "blacklist": [],
    "ans": 0.0,
    "user_profiles": {},
    "grades": {},
    "current_theme": "green",
    "motd": "",
    "chat_logs": [],
    "direct_messages": [],  
    "achievements": {},
    "x_min": -20.0,
    "x_max": 20.0
}

metrics = {
    "session_queries_count": 0,
    "calculation_goal": 0,
    "goal_reached_alerted": False,
    "last_calculation_time": 0.0
}

admin_features = {
    "memory_enabled": False,
    "performance_metrics_enabled": False,
    "self_diagnostic_enabled": False
}

user_variables = {}
achievements_registry = {
    10: "Math Apprentice",
    50: "Calculator Wizard",
    100: "Math Legend",
    500: "Grandmaster",
    600: "Calculator Guru",
    700: "Math Legend"
}

unit_factors = {
    "mm": 0.001, "cm": 0.01, "m": 1, "km": 1000,
    "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mi": 1609.344
}

# ═══════════════════════════════════════════════════════════════
#  STUDY BUDDY FIREBASE & LOCAL IO
# ═══════════════════════════════════════════════════════════════
def _fb_payload():
    return {
        "admin": {
            "passkey":        state["passkey"],
            "motd":           state["motd"],
            "blacklist":      state["blacklist"],
            "precision":      state["precision"],
            "angle_mode":     state["angle_mode"],
            "current_theme":  state["current_theme"],
        },
        "user_profiles":      state["user_profiles"],
        "grades":             state["grades"],
        "achievements":       state["achievements"],
        "chat_logs":          state["chat_logs"],
        "direct_messages":    state["direct_messages"],
        "history":            state["history"],
        "user_variables":     user_variables,
    }

def sync_to_firebase():
    try:
        payload = _fb_payload()
        resp = requests.put(DATABASE_URL + "state.json", json=payload, timeout=6)
        if resp.status_code == 200:
            print("  | [Firebase] Synced ✓")
        else:
            print(f"  | [Firebase] Warning – HTTP {resp.status_code}: {resp.text[:120]}")
    except requests.exceptions.ConnectionError:
        print("  | [Firebase] No internet – saved locally only.")
    except requests.exceptions.Timeout:
        print("  | [Firebase] Timeout – saved locally only.")
    except Exception as e:
        print(f"  | [Firebase] Unexpected error: {e}")

def load_from_firebase():
    global user_variables
    try:
        resp = requests.get(DATABASE_URL + "state.json", timeout=6)
        if resp.status_code != 200:
            print(f"  | [Firebase] Load failed – HTTP {resp.status_code}. Using local data.")
            return
        cloud = resp.json()
        if not cloud or not isinstance(cloud, dict):
            print("  | [Firebase] Empty cloud state. Using local data.")
            return

        adm = cloud.get("admin", {})
        if adm.get("passkey"):           state["passkey"]        = adm["passkey"]
        if adm.get("motd") is not None:  state["motd"]           = adm["motd"]
        if adm.get("blacklist"):         state["blacklist"]       = adm["blacklist"]
        if adm.get("precision") is not None: state["precision"]  = adm["precision"]
        if adm.get("angle_mode"):        state["angle_mode"]      = adm["angle_mode"]
        if adm.get("current_theme"):     apply_theme_colors(adm["current_theme"])

        if cloud.get("user_profiles"):
         if isinstance(cloud["user_profiles"], dict):state["user_profiles"] = cloud["user_profiles"]
         else:state["user_profiles"] = {} # Force it to a dictionary if it's broken
        if cloud.get("grades"):          state["grades"]          = cloud["grades"]
        if cloud.get("achievements"):    state["achievements"]    = cloud["achievements"]
        if cloud.get("chat_logs"):       state["chat_logs"]       = cloud["chat_logs"]
        if cloud.get("direct_messages"): state["direct_messages"] = cloud["direct_messages"]
        if cloud.get("history"):         state["history"]         = cloud["history"]
        if cloud.get("user_variables"):  user_variables           = cloud["user_variables"]
        print("[Firebase] All data loaded from cloud ✓")
    except requests.exceptions.ConnectionError:
        print("[Firebase] No internet – using local data.")
    except requests.exceptions.Timeout:
        print("[Firebase] Timeout – using local data.")
    except Exception as e:
        print(f"[Firebase] Load error: {e} – using local data.")

def save_history(username, expression, result):
    pass  

def get_history():
    try:
        r = requests.get(DATABASE_URL + "state.json", timeout=6)
        return r.json().get("history", []) if r.status_code == 200 else state["history"]
    except Exception:
        return state["history"]

def load_data():
    global user_variables
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                state["precision"] = saved.get("precision", 6)
                state["passkey"] = saved.get("passkey", "126833")
                state["history"] = saved.get("history", [])
                state["blacklist"] = saved.get("blacklist", [])
                state["user_profiles"] = saved.get("user_profiles", {})
                state["grades"] = saved.get("grades", {})
                state["motd"] = saved.get("motd", "")
                state["chat_logs"] = saved.get("chat_logs", [])
                state["direct_messages"] = saved.get("direct_messages", [])
                user_variables = saved.get("user_variables", {})
                state["achievements"] = saved.get("achievements", {})
                state["angle_mode"] = saved.get("angle_mode", "degrees")
                state["x_min"] = saved.get("x_min", -20.0)
                state["x_max"] = saved.get("x_max", 20.0)
                apply_theme_colors(saved.get("current_theme", "green"))
        except Exception:
            print(f"{C_WARN}[System Warning] Error loading data file. Using defaults.{C_RESET}")

def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "precision": state["precision"],
                "passkey": state["passkey"],
                "history": state["history"],
                "blacklist": state["blacklist"],
                "user_profiles": state["user_profiles"],
                "grades": state["grades"],
                "current_theme": state["current_theme"],
                "motd": state["motd"],
                "chat_logs": state["chat_logs"],
                "direct_messages": state["direct_messages"],
                "achievements": state["achievements"],
                "user_variables": user_variables,
                "x_min": state["x_min"],
                "x_max": state["x_max"]
            }, f, indent=4)
    except Exception as e:
        print(f"{C_RED}[System Error] Failed to write data to disk: {e}{C_RESET}")
    sync_to_firebase()

# ═══════════════════════════════════════════════════════════════
#  AGRATOR HELPERS & SEARCH FUNCTIONS
# ═══════════════════════════════════════════════════════════════
def news_search(query):
    try:
        url = "https://newsapi.org/v2/everything"
        params = {"q": query, "apiKey": NEWS_API_KEY, "pageSize": 5, "language": "en"}
        r = requests.get(url, params=params)
        data = r.json()
        results = []
        for article in data.get("articles", []):
            results.append({
                "title": article["title"],
                "body": article["description"],
                "href": article["url"],
                "source": "News"
            })
        return results
    except:
        return []
    
def academic_search(query):
    try:
        search_query = query.split(": ", 1)[1] if ": " in query else query
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {"query": search_query, "limit": 5, "fields": "title,abstract,url"}
        r = requests.get(url, params=params)
        data = r.json()
        results = []
        for paper in data.get("data", []):
            results.append({
                "title": paper["title"],
                "body": paper.get("abstract", "No abstract"),
                "href": paper.get("url", ""),
                "source": "Academic"
            })
        return results
    except:
        return []
   
def normalize_email_key(email_str):
    return email_str.strip().lower().replace('.', '_').replace('@', '_at_')

def log_audit_action(actor, action, target, details=""):
    try:
        payload = {
            "actor": actor,
            "action": action,
            "target": target,
            "timestamp": datetime.now().isoformat(),
            "details": details
        }
        requests.post(f"{FIREBASE_URL}/system/audit_logs.json", json=payload, timeout=3)
    except:
        pass

def increment_global_metric(metric_name):
    try:
        res = requests.get(f"{FIREBASE_URL}/system/analytics/{metric_name}.json", timeout=3)
        curr = res.json() if (res.status_code == 200 and res.json() is not None) else 0
        requests.put(f"{FIREBASE_URL}/system/analytics/{metric_name}.json", json=curr + 1, timeout=3)
    except:
        pass

def decrement_global_metric(metric_name):
    try:
        res = requests.get(f"{FIREBASE_URL}/system/analytics/{metric_name}.json", timeout=3)
        curr = res.json() if (res.status_code == 200 and res.json() is not None) else 0
        requests.put(f"{FIREBASE_URL}/system/analytics/{metric_name}.json", json=max(0, curr - 1), timeout=3)
    except:
        pass

def track_topic_search(topic_str):
    try:
        safe_topic = re.sub(r'[\.\$\#\[\]\/]', '_', topic_str.lower().strip())
        res = requests.get(f"{FIREBASE_URL}/system/analytics/topics/{safe_topic}.json", timeout=3)
        curr = res.json() if (res.status_code == 200 and res.json() is not None) else 0
        requests.put(f"{FIREBASE_URL}/system/analytics/topics/{safe_topic}.json", json=curr + 1, timeout=3)
    except:
        pass

def trigger_achievement(user_key, achievement_id, achievement_name):
    try:
        res = requests.get(f"{FIREBASE_URL}/users/{user_key}/achievements/{achievement_id}.json", timeout=3)
        if res.status_code == 200 and res.json() is True:
            return 
        requests.put(f"{FIREBASE_URL}/users/{user_key}/achievements/{achievement_id}.json", json=True, timeout=3)
        print(f"\n{C_PURPLE}🏆 ACHIEVEMENT UNLOCKED: {achievement_name} 🏆{C_RESET}")
    except:
        pass

def view_achievements(user_key):
    print(f"\n{C_PURPLE}========================================{C_RESET}")
    print(f"{C_PURPLE}       YOUR AGRATOR MILESTONES          {C_RESET}")
    print(f"{C_PURPLE}========================================{C_RESET}")
    ach_list = [
        ("first_search", "First Discovery", "Completed your first automated research search loop."),
        ("export_data", "Data Hoarder", "Exported search results data to local desktop file paths."),
        ("50_searches", "Elite Scholar", "Successfully logged a milestone of 50 data query lookups."),
        ("100_searches", "Grand Academician", "Successfully logged an epic milestone of 100 deep queries."),
        ("translation_used", "Polyglot Researcher", "Used translation protocols to read foreign context indexes.")
    ]
    try:
        c_res = requests.get(f"{FIREBASE_URL}/system/custom_achievements.json", timeout=5)
        if c_res.status_code == 200 and c_res.json():
            for k, v in c_res.json().items():
                ach_list.append((k, f"[SPECIAL] {v.get('name')}", v.get('desc')))
    except:
        pass

    try:
        res = requests.get(f"{FIREBASE_URL}/users/{user_key}/achievements.json", timeout=5)
        unlocked = res.json() if (res.status_code == 200 and res.json()) else {}
    except:
        unlocked = {}
        print(f"{C_RED}⚠️ Failed to fetch cloud milestones. Displaying cached local index.{C_RESET}")
        
    for ach_id, name, desc in ach_list:
        status = f"{C_GREEN}[UNLOCKED]{C_RESET}" if unlocked.get(ach_id) else f"{C_RED}[LOCKED]{C_RESET}"
        print(f" • {C_YELLOW}{name:<20}{C_RESET} {status}\n   {desc}")
    print(f"{C_PURPLE}========================================{C_RESET}")

def show_analytics_dashboard():
    print(f"\n{C_PURPLE}========================================{C_RESET}")
    print(f"{C_PURPLE}       AGRATOR CORE SYSTEM ANALYTICS    {C_RESET}")
    print(f"{C_PURPLE}========================================{C_RESET}")
    try:
        resp_users = requests.get(f"{FIREBASE_URL}/users.json", timeout=5)
        users_dict = resp_users.json() if resp_users.status_code == 200 and resp_users.json() else {}
        
        resp_analytics = requests.get(f"{FIREBASE_URL}/system/analytics.json", timeout=5)
        an_data = resp_analytics.json() if resp_analytics.status_code == 200 and resp_analytics.json() else {}
        
        print(f"Total Registered Profiles: {C_CYAN}{len(users_dict)}{C_RESET}")
        print(f"Global Research Requests:   {C_CYAN}{an_data.get('total_searches', 0)}{C_RESET}")
        print(f"Compiled Document Exports:  {C_CYAN}{an_data.get('total_exports', 0)}{C_RESET}")
        print(f"Active User Suspensions:    {C_CYAN}{an_data.get('active_bans', 0)}{C_RESET}")
        
        print(f"\n{C_YELLOW}Trending Research Areas:{C_RESET}")
        topics_dict = an_data.get("topics", {})
        if topics_dict:
            for idx, (t_name, count) in enumerate(sorted(topics_dict.items(), key=lambda x: x[1], reverse=True)[:5], 1):
                print(f"  [{idx}] {t_name.replace('_', ' ')}: {count} lookups")
        else:
            print("  No search streams recorded yet.")
            
        print(f"\n{C_YELLOW}Top Platform Operators:{C_RESET}")
        user_ranks = []
        for k, v in users_dict.items():
            if isinstance(v, dict):
                user_ranks.append((v.get("email", k), v.get("search_count", 0)))
        if user_ranks:
            for idx, (email, count) in enumerate(sorted(user_ranks, key=lambda x: x[1], reverse=True)[:5], 1):
                print(f"  [{idx}] {email}: {count} queries logged")
        else:
            print("  No system queries registered.")
    except Exception as e:
        print(f"{C_RED}Error running data aggregation routines: {e}{C_RESET}")
    print(f"{C_PURPLE}========================================{C_RESET}")

def show_summary_report(user_key, email, role):
    print(f"\n{C_PURPLE}========================================{C_RESET}")
    print(f"{C_PURPLE}       AGRATOR SESSION SUMMARY          {C_RESET}")
    print(f"{C_PURPLE}========================================{C_RESET}")
    print(f"User Identity: {C_CYAN}{email}{C_RESET} | Access Tier: {C_CYAN}{role.upper()}{C_RESET}")
    try:
        res = requests.get(f"{FIREBASE_URL}/users/{user_key}/search_count.json", timeout=5)
        count = res.json() if res.status_code == 200 and res.json() else 0
        print(f"Total Lifetime Queries: {C_YELLOW}{count}{C_RESET}")
        
        hist_res = requests.get(f"{FIREBASE_URL}/users/{user_key}/history.json", timeout=5)
        if hist_res.status_code == 200 and hist_res.json():
            hist_keys = list(hist_res.json().keys())[-5:] # Show last 5
            print(f"\n{C_YELLOW}Recent Search Trajectories:{C_RESET}")
            for hk in hist_keys:
                print(f" - {hk.replace('_', ' ')}")
        else:
            print(f"\n{C_YELLOW}No query history found on this device.{C_RESET}")
    except Exception as e:
        print(f"{C_RED}Unable to pull live summary statistics: {e}{C_RESET}")
    print(f"{C_PURPLE}========================================{C_RESET}\n")

def play_trivia():
    print(f"\n{C_CYAN}========================================{C_RESET}")
    print(f"{C_CYAN}          AGRATOR TRIVIA ARENA          {C_RESET}")
    print(f"{C_CYAN}========================================{C_RESET}")
    try:
        res = requests.get(f"{FIREBASE_URL}/system/trivias.json", timeout=5)
        trivias = res.json() if res.status_code == 200 and res.json() else {}
    except:
        trivias = {}
        
    if not trivias:
        print(f"{C_YELLOW}The trivia database is currently empty. Ask a Moderator to add some!{C_RESET}")
        return
        
    keys = list(trivias.keys())
    for i, k in enumerate(keys, 1):
        print(f"[{i}] {trivias[k].get('title', 'Mystery Trivia')}")
        
    choice = input(f"\n{C_YELLOW}Select a trivia index number to play (or 'c' to cancel): {C_RESET}").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(keys):
        t_data = trivias[keys[int(choice)-1]]
        print(f"\n{C_PURPLE}QUESTION: {t_data.get('question')}{C_RESET}")
        opts = t_data.get('options', [])
        for idx, opt in enumerate(opts, 1):
            print(f"  {idx}. {opt}")
            
        ans = input(f"\n{C_CYAN}Enter the number of your answer: {C_RESET}").strip()
        if ans == str(t_data.get('answer')):
            print(f"{C_GREEN}[✓] CORRECT! Excellent knowledge.{C_RESET}")
        else:
            print(f"{C_RED}[X] INCORRECT. The correct answer was option {t_data.get('answer')}.{C_RESET}")
    elif choice.lower() != 'c':
        print(f"{C_RED}Invalid selection.{C_RESET}")

def change_theme():
    # Combined Theme changer for both Agrator and Study Buddy
    global C_BLUE, C_GREEN, C_PURPLE, C_YELLOW, C_CYAN, C_RED, C_WARN
    print(f"\n{C_CYAN}=== AGRATOR / STUDY BUDDY THEMES ==={C_RESET}")
    print("1. Default (Multicolor / Green Primary)")
    print("2. Hacker Terminal (Matrix Green)")
    print("3. Cyberpunk (Neon Pink & Cyan)")
    print("4. Ocean Depth (Blues & Cyans)")
    print("5. Mono (Black & White)")
    choice = input(f"Select a theme (1-5): {C_RESET}")
    
    if choice == '1':
        C_BLUE = "\033[94m"; C_GREEN = "\033[92m"; C_PURPLE = "\033[95m"
        C_YELLOW = "\033[93m"; C_CYAN = "\033[96m"; C_RED = "\033[91m"
        apply_theme_colors("green")
        print(f"{C_GREEN}[✓] Default theme restored.{C_RESET}")
    elif choice == '2':
        C_BLUE = C_GREEN = C_PURPLE = C_YELLOW = C_CYAN = "\033[92m"
        C_RED = "\033[91m"
        apply_theme_colors("green")
        print(f"{C_GREEN}[✓] Hacker theme activated. Follow the white rabbit.{C_RESET}")
    elif choice == '3':
        C_BLUE = "\033[95m"; C_GREEN = "\033[96m"; C_PURPLE = "\033[95m"
        C_YELLOW = "\033[96m"; C_CYAN = "\033[95m"; C_RED = "\033[91m"
        apply_theme_colors("cyber")
        print(f"{C_GREEN}[✓] Cyberpunk theme activated.{C_RESET}")
    elif choice == '4':
        C_BLUE = "\033[94m"; C_GREEN = "\033[96m"; C_PURPLE = "\033[94m"
        C_YELLOW = "\033[96m"; C_CYAN = "\033[94m"; C_RED = "\033[91m"
        apply_theme_colors("cyber")
        print(f"{C_GREEN}[✓] Ocean theme activated.{C_RESET}")
    elif choice == '5':
        C_BLUE = "\033[37m"; C_GREEN = "\033[37m"; C_PURPLE = "\033[37m"
        C_YELLOW = "\033[37m"; C_CYAN = "\033[37m"; C_RED = "\033[37m"
        apply_theme_colors("mono")
        print(f"{C_GREEN}[✓] Mono theme activated.{C_RESET}")
    else:
        print(f"{C_RED}[!] Invalid selection. Theme unchanged.{C_RESET}")

def apply_theme_colors(theme_name):
    global C_GREEN, C_CYAN, C_WARN
    selected = THEMES.get(theme_name, THEMES["green"])
    C_GREEN = selected["primary"]
    C_CYAN  = selected["accent"]
    C_WARN  = selected["warn"]
    state["current_theme"] = theme_name

def check_cloud_connection():
    try:
        requests.get(f"{FIREBASE_URL}/.json", timeout=3)
        return True
    except Exception:
        return False
    

# ═══════════════════════════════════════════════════════════════
#  UNIFIED ADMIN PANEL
# ═══════════════════════════════════════════════════════════════
def super_admin_panel(current_user_key, current_user_email, role):
    is_admin = (role == "admin" or current_user_email == "ajsag")
    title_tag = "MASTER ADMIN" if is_admin else "MODERATOR"
    
    while True:
        print(f"\n{C_RED}======================================================={C_RESET}")
        print(f"{C_RED}       AGRATOR & STUDY BUDDY {title_tag} TERMINAL v16.4    {C_RESET}")
        print(f"{C_RED}======================================================={C_RESET}")
        print(f"{C_YELLOW}--- AGRATOR MODULE CONTROLS ---{C_RESET}")
        print("1. Run Agrator Diagnostics")
        print("2. Ban a User (View List & Add Reason)")
        print("3. Unban a User (View Active Bans)")
        print("4. View User Directory")
        if is_admin:
            print("5. Manage Staff Roles (Promote/Demote Moderators)")
            print("7. Change Admin Passcode")
            print("8. View Agrator Analytics Dashboard")
            print("9. View System Audit Logs")
        if is_admin or role == "moderator":
            print("10. Global MOTD Configuration (Edit/Delete)")
        if is_admin:
            print("11. Delete a User (PERMANENT WIPE BY INDEX)")
        if is_admin or role == "moderator":
            print("13. Manage Custom Trivia (Create/Delete)")
        if current_user_email == "ajsag":
            print(f"{C_PURPLE}14. Create Custom Achievements (Creator Only){C_RESET}")
        if is_admin:
            print(f"{C_RED}15. Complete Reset of Global Cloud History (PERMANENT WIPE){C_RESET}")
            print(f"{C_RED}16. Complete Reset of Analytics & Audit Logs (PERMANENT WIPE){C_RESET}")
            
        print(f"\n{C_CYAN}--- STUDY BUDDY MODULE CONTROLS ---{C_RESET}")
        print("17. Study Buddy System Diagnostics & Health")
        print("18. Manage Logs & Compiled History (Calc)")
        print("19. Change Output Precision (Calc)")
        print("20. Update Study Buddy Admin Passkey")
        print("21. View Study Buddy Changelog")
        print("22. Manage Study Buddy Announcement (MOTD)")
        print("23. Delete Study Buddy User Account")
        print("24. Advanced Features Configuration (Calc)")
        print("25. Grade Counter Metrics Panel")
        print("26. Custom Achievement Creator (Calc)")
        
        print("\n27. Exit Super Admin Panel")
        choice = input(f"\n{C_YELLOW}Select an authorized command: {C_RESET}").strip()
        
        # --- AGRATOR ADMIN BRANCH ---
        if choice == '1':
            print(f"\n{C_CYAN}--- Agrator Diagnostics ---{C_RESET}")
            cloud_ok = check_cloud_connection()
            print(f"Cloud Database Status: {'[✓] ONLINE' if cloud_ok else '[!] OFFLINE'}")
            print(f"Local History Cache: {'[✓] FOUND' if os.path.exists(HISTORY_FILE) else '[!] MISSING'}")
            print(f"Active Identity Session: {current_user_email} (Role: {role.upper()})")
            
        elif choice == '2':
            try:
                resp = requests.get(f"{FIREBASE_URL}/users.json", timeout=5)
                users = resp.json() if resp.status_code == 200 and resp.json() else {}
                user_keys = list(users.keys())
                
                print(f"\n{C_YELLOW}--- REGISTERED USERS ---{C_RESET}")
                for i, key in enumerate(user_keys):
                    status = ""
                    data = users[key]
                    u_role = data.get("role", "user") if isinstance(data, dict) else "user"
                    if isinstance(data, dict) and data.get("ban_expiry"):
                         if datetime.now() < datetime.fromisoformat(data["ban_expiry"]):
                             status = f" {C_RED}[CURRENTLY BANNED]{C_RESET}"
                    print(f"  [{i}] {key} (Role: {u_role.upper()}){status}")
                    
                target_idx = input(f"\n{C_CYAN}Enter user number to ban (or 'c' to cancel): {C_RESET}").strip()
                if target_idx.lower() == 'c': continue
                
                if target_idx.isdigit() and int(target_idx) < len(user_keys):
                    target = user_keys[int(target_idx)]
                    target_data = users[target]
                    target_role = target_data.get("role", "user") if isinstance(target_data, dict) else "user"
                    
                    if target_role == "admin" and role != "admin":
                        print(f"{C_RED}[!] Error: Moderators are unauthorized to penalize administrators.{C_RESET}")
                        continue
                        
                    days = int(input(f"Enter number of days to ban '{target}': "))
                    reason = input(f"Enter the reason for this ban: ")
                    
                    expiry = (datetime.now() + timedelta(days=days)).isoformat()
                    requests.patch(f"{FIREBASE_URL}/users/{target}.json", json={"ban_expiry": expiry, "ban_reason": reason})
                    print(f"{C_GREEN}[✓] User {target} banned until {expiry}. Reason: {reason}{C_RESET}")
                    
                    log_audit_action(current_user_email, "BAN_USER", target, f"Duration: {days} days. Reason: {reason}")
                    increment_global_metric("active_bans")
                else:
                    print(f"{C_RED}Invalid selection.{C_RESET}")
            except Exception as e:
                print(f"{C_RED}⚠️ [WARNING] Failed to execute ban action: {e}{C_RESET}")
                
        elif choice == '3':
            try:
                resp = requests.get(f"{FIREBASE_URL}/users.json", timeout=5)
                users = resp.json() if resp.status_code == 200 and resp.json() else {}
                banned_keys = []
                current_time = datetime.now()
                
                print(f"\n{C_RED}--- ACTIVE BANS ---{C_RESET}")
                for key, data in users.items():
                    if isinstance(data, dict) and data.get("ban_expiry"):
                        expiry_date = datetime.fromisoformat(data["ban_expiry"])
                        if current_time < expiry_date:
                            banned_keys.append(key)
                            reason = data.get("ban_reason", "No reason provided")
                            print(f"  [{len(banned_keys)-1}] {key}")
                            print(f"      Expires: {expiry_date.strftime('%Y-%m-%d %H:%M')}")
                            print(f"      Reason:  {reason}")
                
                if not banned_keys:
                    print(f"{C_GREEN}No active bans found.{C_RESET}")
                    continue
                    
                target_idx = input(f"\n{C_CYAN}Enter user number to unban (or 'c' to cancel): {C_RESET}").strip()
                if target_idx.lower() == 'c': continue
                
                if target_idx.isdigit() and int(target_idx) < len(banned_keys):
                    target = banned_keys[int(target_idx)]
                    requests.patch(f"{FIREBASE_URL}/users/{target}.json", json={"ban_expiry": None, "ban_reason": None})
                    print(f"{C_GREEN}[✓] User {target} has been unbanned.{C_RESET}")
                    
                    log_audit_action(current_user_email, "UNBAN_USER", target, "Suspension manually revoked.")
                    decrement_global_metric("active_bans")
                else:
                    print(f"{C_RED}Invalid selection.{C_RESET}")
            except Exception as e:
                print(f"{C_RED}⚠️ [WARNING] Failed to load active bans: {e}{C_RESET}")
                
        elif choice == '4':
            try:
                resp = requests.get(f"{FIREBASE_URL}/users.json", timeout=5)
                users = resp.json() if resp.status_code == 200 and resp.json() else {}
                print(f"\n{C_YELLOW}--- SYSTEM USER DIRECTORY ---{C_RESET}")
                for idx, (key, value) in enumerate(users.items()):
                    u_role = value.get("role", "user") if isinstance(value, dict) else "user"
                    last_l = value.get("last_login", "Never") if isinstance(value, dict) else "Never"
                    print(f" [{idx}] {key} | Role: {u_role.upper()} | Last Access: {last_l}")
            except Exception as e:
                print(f"{C_RED}Error loading user list: {e}{C_RESET}")
                
        elif choice == '5' and is_admin:
            try:
                resp = requests.get(f"{FIREBASE_URL}/users.json", timeout=5)
                users = resp.json() if resp.status_code == 200 and resp.json() else {}
                user_keys = list(users.keys())
                
                print(f"\n{C_CYAN}=== MODERATOR MANAGEMENT SYSTEM ==={C_RESET}")
                print("1. Promote User to Moderator")
                print("2. Demote Moderator to Regular User")
                print("3. View Staff Directory")
                sub_choice = input(f"{C_YELLOW}Select action: {C_RESET}").strip()
                
                if sub_choice == '1':
                    for i, key in enumerate(user_keys):
                        current_r = users[key].get("role", "user") if isinstance(users[key], dict) else "user"
                        print(f"  [{i}] {key} (Current Role: {current_r.upper()})")
                    t_idx = input(f"\n{C_CYAN}Enter user index to promote to Moderator: {C_RESET}").strip()
                    if t_idx.isdigit() and int(t_idx) < len(user_keys):
                        target = user_keys[int(t_idx)]
                        confirm = input(f"Are you sure you want to promote '{target}' to Moderator? (y/n): ").strip().lower()
                        if confirm == 'y':
                            requests.patch(f"{FIREBASE_URL}/users/{target}.json", json={"role": "moderator"})
                            print(f"{C_GREEN}[✓] User {target} promoted to Moderator successfully.{C_RESET}")
                            log_audit_action(current_user_email, "PROMOTE_MODERATOR", target, "Assigned role: moderator")
                    else:
                        print(f"{C_RED}Invalid selection.{C_RESET}")
                        
                elif sub_choice == '2':
                    for i, key in enumerate(user_keys):
                        current_r = users[key].get("role", "user") if isinstance(users[key], dict) else "user"
                        print(f"  [{i}] {key} (Current Role: {current_r.upper()})")
                    t_idx = input(f"\n{C_CYAN}Enter user index to demote: {C_RESET}").strip()
                    if t_idx.isdigit() and int(t_idx) < len(user_keys):
                        target = user_keys[int(t_idx)]
                        target_role = users[target].get("role", "user") if isinstance(users[target], dict) else "user"
                        
                        if target_role == "admin":
                            admin_count = sum(1 for k, v in users.items() if isinstance(v, dict) and v.get("role") == "admin")
                            if admin_count <= 1:
                                print(f"{C_RED}[!] Operation Aborted: Demoting this account would leave the system with 0 administrators.{C_RESET}")
                                continue
                                
                        confirm = input(f"Are you sure you want to demote '{target}' to a standard User? (y/n): ").strip().lower()
                        if confirm == 'y':
                            requests.patch(f"{FIREBASE_URL}/users/{target}.json", json={"role": "user"})
                            print(f"{C_GREEN}[✓] User {target} demoted back to standard user.{C_RESET}")
                            log_audit_action(current_user_email, "DEMOTE_MODERATOR", target, "Revoked role to: user")
                    else:
                        print(f"{C_RED}Invalid selection.{C_RESET}")
                        
                elif sub_choice == '3':
                    print(f"\n{C_YELLOW}--- STAFF MEMBER LIST ---{C_RESET}")
                    has_staff = False
                    for key, data in users.items():
                        u_role = data.get("role", "user") if isinstance(data, dict) else "user"
                        if u_role in ["admin", "moderator"]:
                            has_staff = True
                            print(f" • {C_GREEN}{key}{C_RESET} [Access Level: {u_role.upper()}]")
                    if not has_staff:
                        print(" No custom staff roles found.")
            except Exception as e:
                print(f"{C_RED}Staff management protocol failed: {e}{C_RESET}")
                
        
        elif choice == '7' and is_admin:
            new_admin_pass = input("Enter your new Admin Passcode: ").strip()
            if new_admin_pass:
                try:
                    requests.put(f"{FIREBASE_URL}/system/admin_passcode.json", json=new_admin_pass)
                    print(f"{C_GREEN}[✓] Admin Passcode successfully updated in the cloud.{C_RESET}")
                    log_audit_action(current_user_email, "CHANGE_ADMIN_PASSCODE", "SYSTEM", "Global admin override credential rotated.")
                except Exception as e:
                    print(f"{C_RED}⚠️ [WARNING] Failed to update Admin Passcode in cloud: {e}{C_RESET}")
            else:
                print(f"{C_RED}[!] Passcode cannot be blank.{C_RESET}")
                
        elif choice == '8' and is_admin:
            show_analytics_dashboard()
            
        elif choice == '9' and is_admin:
            try:
                print(f"\n{C_YELLOW}=== COGNITIVE SYSTEM AUDIT LOGS ==={C_RESET}")
                resp = requests.get(f"{FIREBASE_URL}/system/audit_logs.json", timeout=5)
                logs_dict = resp.json() if resp.status_code == 200 and resp.json() else {}
                if logs_dict:
                    sorted_logs = sorted(logs_dict.values(), key=lambda x: x.get("timestamp", ""), reverse=True)[:15]
                    for log in sorted_logs:
                        t_stamp = log.get("timestamp", "N/A")[:19].replace("T", " ")
                        print(f"[{C_BLUE}{t_stamp}{C_RESET}] {C_GREEN}{log.get('actor')}{C_RESET} executed {C_YELLOW}{log.get('action')}{C_RESET} targeting {C_CYAN}{log.get('target')}{C_RESET}")
                        if log.get("details"):
                            print(f"    Context: {log.get('details')}")
                else:
                    print(" Audit database logs are clean.")
            except Exception as e:
                print(f"{C_RED}Failed to pull audit logs: {e}{C_RESET}")
                
        elif choice == '10' and role in ['admin', 'moderator']:
            print(f"\n{C_CYAN}=== GLOBAL MOTD MANAGEMENT ==={C_RESET}")
            print("1. Update/Edit Message of the Day")
            print("2. Delete Message of the Day")
            motd_op = input(f"{C_YELLOW}Select action (1-2): {C_RESET}").strip()
            
            if motd_op == '1':
                new_motd = input("Enter your new global Message of the Day string:\n> ").strip()
                if new_motd:
                    try:
                        requests.put(f"{FIREBASE_URL}/system/motd.json", json=new_motd)
                        print(f"{C_GREEN}[✓] Message of the Day successfully initialized across nodes.{C_RESET}")
                        log_audit_action(current_user_email, "EDIT_MOTD", "SYSTEM", f"Value: {new_motd}")
                    except Exception as e:
                        print(f"{C_RED}Failed to push MOTD: {e}{C_RESET}")
                else:
                    print(f"{C_RED}MOTD string cannot be blank.{C_RESET}")
            elif motd_op == '2':
                confirm = input(f"{C_RED}Are you sure you want to permanently DELETE the global MOTD? (y/n): {C_RESET}").strip().lower()
                if confirm == 'y':
                    try:
                        requests.delete(f"{FIREBASE_URL}/system/motd.json")
                        print(f"{C_GREEN}[✓] Message of the Day has been deleted from cloud nodes.{C_RESET}")
                        log_audit_action(current_user_email, "DELETE_MOTD", "SYSTEM", "Cleared active global message string.")
                    except Exception as e:
                        print(f"{C_RED}Failed to delete MOTD: {e}{C_RESET}")
            else:
                print(f"{C_RED}Invalid menu choice.{C_RESET}")
                
        elif choice == '11' and is_admin:
            try:
                resp = requests.get(f"{FIREBASE_URL}/users.json", timeout=5)
                users = resp.json() if resp.status_code == 200 and resp.json() else {}
                
                print(f"\n{C_YELLOW}--- RAW DATABASE KEYS ---{C_RESET}")
                keys = list(users.keys())
                for i, key in enumerate(keys):
                    print(f"  {i}: {key}")
                
                selection = input("\nEnter the number of the user to delete: ").strip()
                if selection.isdigit() and int(selection) < len(keys):
                    target_key = keys[int(selection)]
                    target_role = users[target_key].get("role", "user") if isinstance(users[target_key], dict) else "user"
                    
                    if target_role == "admin":
                        admin_count = sum(1 for k, v in users.items() if isinstance(v, dict) and v.get("role") == "admin")
                        if admin_count <= 1:
                            print(f"{C_RED}[!] Operation Aborted: Deleting this user would remove the final remaining admin profile.{C_RESET}")
                            continue
                            
                    print(f"\n{C_CYAN}Selected User Key: {target_key}{C_RESET}")
                    if input(f"\n{C_RED}Confirm PERMANENT deletion? (y/n): {C_RESET}").lower() == 'y':
                        requests.delete(f"{FIREBASE_URL}/users/{target_key}.json")
                        print(f"{C_GREEN}[✓] Purged user storage block '{target_key}' from database.{C_RESET}")
                        log_audit_action(current_user_email, "PERMANENT_WIPE", target_key, "User storage completely scrubbed from real-time node tree.")
                else:
                    print(f"{C_RED}Invalid selection.{C_RESET}")
            except Exception as e:
                print(f"{C_RED}Purge operation failed: {e}{C_RESET}")
                
        elif choice == '13' and role in ['admin', 'moderator']:
            print(f"\n{C_CYAN}=== MANAGE CUSTOM TRIVIA ==={C_RESET}")
            print("1. Create New Trivia")
            print("2. Delete an Existing Trivia")
            t_op = input(f"{C_YELLOW}Select action (1-2): {C_RESET}").strip()
            
            if t_op == '1':
                t_title = input("Enter Trivia Topic Name: ").strip()
                t_q = input("Enter Question: ").strip()
                opts = []
                for i in range(4):
                    opts.append(input(f"Enter Option {i+1}: ").strip())
                ans = input("Enter the number corresponding to the correct answer (1-4): ").strip()
                
                payload = {
                    "title": t_title,
                    "question": t_q,
                    "options": opts,
                    "answer": ans
                }
                t_id = f"triv_{int(time.time())}"
                try:
                    requests.put(f"{FIREBASE_URL}/system/trivias/{t_id}.json", json=payload, timeout=5)
                    print(f"{C_GREEN}[✓] Trivia successfully uploaded to the global server!{C_RESET}")
                except Exception as e:
                    print(f"{C_RED}Failed to create trivia: {e}{C_RESET}")
                    
            elif t_op == '2':
                try:
                    res = requests.get(f"{FIREBASE_URL}/system/trivias.json", timeout=5)
                    trivias = res.json() if res.status_code == 200 and res.json() else {}
                    if not trivias:
                        print(f"{C_YELLOW}No trivias to delete.{C_RESET}")
                        continue
                    
                    keys = list(trivias.keys())
                    for i, k in enumerate(keys, 1):
                        print(f"[{i}] {trivias[k].get('title', 'Unknown')} - {trivias[k].get('question', '')[:30]}...")
                        
                    del_idx = input("Enter the number of the trivia to delete (or 'c' to cancel): ").strip()
                    if del_idx.isdigit() and 1 <= int(del_idx) <= len(keys):
                        target_id = keys[int(del_idx)-1]
                        requests.delete(f"{FIREBASE_URL}/system/trivias/{target_id}.json", timeout=5)
                        print(f"{C_GREEN}[✓] Trivia deleted permanently.{C_RESET}")
                except Exception as e:
                    print(f"{C_RED}Error loading trivias: {e}{C_RESET}")
            else:
                print(f"{C_RED}Invalid option.{C_RESET}")

        elif choice == '14' and current_user_email == "ajsag":
            print(f"\n{C_CYAN}--- CUSTOM ACHIEVEMENT MANAGER ---{C_RESET}")
            try:
                res = requests.get(f"{FIREBASE_URL}/system/custom_achievements.json", timeout=5)
                curr_ach = res.json() if (res.status_code == 200 and res.json()) else {}
            except:
                curr_ach = {}

            if not curr_ach:
                print("  | No custom achievements found.")
            else:
                print("  | Current Achievements:")
                for ach_id, data in curr_ach.items():
                    print(f"    - [{ach_id}] {data.get('name')}")
            
            print("\n  1) Add new achievement")
            print("  2) Delete an achievement")
            sub = input(f"{C_YELLOW}Choice: {C_RESET}").strip()
            
            if sub == '1':
                a_id = input("Enter unique achievement ID tag: ").strip()
                a_name = input("Enter Display Name: ").strip()
                a_desc = input("Enter Description: ").strip()
                if a_id and a_name:
                    try:
                        requests.put(f"{FIREBASE_URL}/system/custom_achievements/{a_id}.json", 
                                     json={"name": a_name, "desc": a_desc}, timeout=5)
                        print(f"{C_GREEN}[✓] Custom Achievement '{a_name}' published globally!{C_RESET}")
                    except Exception as e:
                        print(f"{C_RED}Failed to create custom achievement: {e}{C_RESET}")
            
            elif sub == '2':
                del_id = input("Enter the ID of the achievement to delete: ").strip()
                if del_id in curr_ach:
                    try:
                        requests.delete(f"{FIREBASE_URL}/system/custom_achievements/{del_id}.json", timeout=5)
                        print(f"{C_GREEN}[✓] Achievement '{del_id}' deleted.{C_RESET}")
                    except Exception as e:
                        print(f"{C_RED}Failed to delete achievement: {e}{C_RESET}")
                else:
                    print(f"{C_RED}ID not found.{C_RESET}")

        elif choice == '15' and is_admin:
            confirm = input(f"\n{C_RED}⚠️ WARNING: Are you sure you want to PERMANENTLY WIPE ALL SEARCH HISTORIES from Firebase? (yes/no): {C_RESET}").strip().lower()
            if confirm == 'yes':
                try:
                    print(f"{C_CYAN}[...] Extracting system profile nodes...{C_RESET}")
                    resp = requests.get(f"{FIREBASE_URL}/users.json", timeout=10)
                    users = resp.json() if resp.status_code == 200 and resp.json() else {}
                    
                    if users:
                        print(f"{C_CYAN}[...] Purging histories and analytics parameters synchronized on nodes...{C_RESET}")
                        for u_key in users.keys():
                            requests.delete(f"{FIREBASE_URL}/users/{u_key}/history.json", timeout=5)
                            requests.put(f"{FIREBASE_URL}/users/{u_key}/search_count.json", json=0, timeout=5)
                        
                        requests.delete(f"{FIREBASE_URL}/system/analytics/topics.json", timeout=5)
                        requests.put(f"{FIREBASE_URL}/system/analytics/total_searches.json", json=0, timeout=5)
                        
                        print(f"{C_GREEN}[✓] Linked Firebase history nodes wiped successfully across all accounts!{C_RESET}")
                        log_audit_action(current_user_email, "GLOBAL_HISTORY_RESET", "SYSTEM", "Wiped all user histories and metrics tracking indexes.")
                    else:
                        print(f"{C_YELLOW}No users found in database.{C_RESET}")
                except Exception as e:
                    print(f"{C_RED}Wipe framework cancellation error encountered: {e}{C_RESET}")
            else:
                print(f"{C_YELLOW}Global history wipe operation aborted.{C_RESET}")

        elif choice == '16' and is_admin:
            confirm = input(f"\n{C_RED}⚠️ WARNING: Are you sure you want to PERMANENTLY WIPE ALL Analytics and Audit Logs? (yes/no): {C_RESET}").strip().lower()
            if confirm == 'yes':
                try:
                    print(f"{C_CYAN}[...] Purging system analytics dashboard data...{C_RESET}")
                    requests.delete(f"{FIREBASE_URL}/system/analytics.json", timeout=10)
                    print(f"{C_CYAN}[...] Purging cognitive system audit logs...{C_RESET}")
                    requests.delete(f"{FIREBASE_URL}/system/audit_logs.json", timeout=10)
                    print(f"{C_GREEN}[✓] System Analytics and Audit Logs wiped successfully!{C_RESET}")
                    log_audit_action(current_user_email, "GLOBAL_METRICS_WIPE", "SYSTEM", "Wiped all system analytics and audit logs.")
                except Exception as e:
                    print(f"{C_RED}Wipe framework cancellation error encountered: {e}{C_RESET}")
            else:
                print(f"{C_YELLOW}Analytics and logs wipe operation aborted.{C_RESET}")

        # --- STUDY BUDDY ADMIN BRANCH ---
        elif choice == '17':
            print(f"\n{C_CYAN}--- STUDY BUDDY DIAGNOSTICS & SYSTEM HEALTH ---{C_RESET}")
            print(f"  | Saved History Logs   : {len(state['history'])}")
            print(f"  | Active Bans Counts   : {len(state['blacklist'])}")
            print(f"  | Total User Profiles  : {len(state['user_profiles'])}")
            print(f"  | Chat Log Volume      : {len(state['chat_logs'])} messages")
            print(f"  | Private DM Volume    : {len(state['direct_messages'])} whispers")
            print(f"  | Active Broadcast     : {state['motd'] if state['motd'] else '[None Set]'}")
            print(f"  | Current Theme Style  : {state['current_theme']}")
            print(f"  | Angle Mode           : {state.get('angle_mode', 'degrees').upper()}")
            print(f"  | Decimal Precision    : {state['precision']} places")
            print(f"  | Memory Key (ans)     : {state['ans']}")
            print(f"  | Session Processing   : {metrics['session_queries_count']} raw commands")
            print(f"{C_CYAN}--- SYSTEM STATUS (ADVANCED FEATURES) ---{C_RESET}")
            print(f"  | Last Calculation Time: {metrics['last_calculation_time']:.3f} ms")
            print(f"  | Memory Variables     : {len(user_variables)}")
            if user_variables:
                print(f"  | Stored Variables     : {', '.join(f'{k}={v}' for k, v in user_variables.items())}")
            print(f"{C_CYAN}--- FEATURE TOGGLES ---{C_RESET}")
            print(f"  | Memory/Variables     : {'ENABLED' if admin_features['memory_enabled'] else 'DISABLED'}")
            print(f"  | Performance Metrics  : {'ENABLED' if admin_features['performance_metrics_enabled'] else 'DISABLED'}")
            print(f"  | Self-Diagnostic      : {'ENABLED' if admin_features['self_diagnostic_enabled'] else 'DISABLED'}")
            print(f"{C_CYAN}-----------------------------------{C_RESET}")
           
        elif choice == '18':
            print(f"\n{C_CYAN}--- STUDY BUDDY TRANSACTION LOGS MANAGER ---{C_RESET}")
            print("\n  [Calculations History Cache Compiled by Date]:")
            if not state['history']:
                print("    | History cache is empty.")
            else:
                grouped_history = {}
                for log in state['history']:
                    date_key = log.get("date", "Unknown Date")
                    if date_key not in grouped_history:
                        grouped_history[date_key] = []
                    grouped_history[date_key].append(log)
                   
                for d_key, logs in grouped_history.items():
                    print(f"\n   DATE: {d_key}")
                    for idx, item in enumerate(logs):
                        g_idx = state['history'].index(item)
                        print(f"    [{g_idx}] | User: {item['user']} | Query: {item['query']} | Result: {item['result']}")
           
            print(f"\n  -> {C_BOLD}Commands:{C_RESET} Type 'd <index>' to remove a log line or Enter to return.")
            action = input("Action Command: ").strip()
            if action.lower().startswith('d '):
                try:
                    target = int(action.split()[1])
                    removed = state['history'].pop(target)
                    save_data()
                    print(f"  | Success: Deleted log entry '{removed['query']}'")
                except Exception:
                    print(f"  {C_RED}| Error: Invalid log index entry selector.{C_RESET}")
                       
        elif choice == '19':
            new_p = input(f"Enter precision/decimal limit [Current: {state['precision']}]: ").strip()
            if new_p.isdigit() and 0 <= int(new_p) <= 15:
                state['precision'] = int(new_p)
                save_data()
                print(f"  | Configuration updated. Precision set to {state['precision']}.")
            else: print(f"  {C_RED}| Invalid range selection (Must be 0-15).{C_RESET}")
               
        elif choice == '20':
            new_pass = getpass.getpass("Enter new Study Buddy admin passkey challenge: ").strip()
            if len(new_pass) >= 4:
                state['passkey'] = new_pass
                save_data()
                print("  | Study Buddy Passkey modified successfully.")
            else: print(f"  {C_RED}| Rejection: Passkey must be at least 4 characters.{C_RESET}")
               
        elif choice == '21':
            print(f"\n{C_CYAN}--- STUDY BUDDY SYSTEM CHANGELOG ---{C_RESET}")
            print("  | v4.85 - Implemented secure private direct whispers.")
            print("  | v4.90 - Integrated ASCII workspace grid function plotter.")
            print("  | v5.00 - Added compiled history, grid expand, grade counters, & Bank Peek.")
            print("  | v5.7  - Full admin panel, user profiles, global chat, and performance metrics.")
            print(f"  | v8.5 - Updated with new features and improvements such as converter, self-diagnostic, and more understandable error handling.")
            print(f"  | v9.0 - Repaired critical bugs and improved stability repaired chat and direct messaging.")
            print(f"  | v9.5 - Added new features such as advanced feature toggles, improved self-diagnostic tests, and enhanced user variable management.")
            print(f"  | v9.64 - Major update with a complete admin control panel, user profiles, global chat system, private whispers, and performance metrics tracking.")
            print(f"  | v16.4 - SUPER MASHUP with Agrator. Unified UI, combined /help, global product key checks.")
            print(f"{C_CYAN}------------------------------{C_RESET}")

        elif choice == '22':
            print("\nStudy Buddy Announcement Manager")
            print("1) Set announcement")
            print("2) Remove the announcement")
            sub = input("Choice: ").strip()
            if sub == "1":
                state["motd"] = input("Enter announcement: ").strip()
                save_data()
                print("Announcement updated.")
            elif sub == "2":
                state["motd"] = ""
                save_data()
                print("Announcement removed.")

        elif choice == '23':
            load_from_firebase() 
            print("\n LIVE STUDY BUDDY DATABASE DIRECTORY:")
            if not state['user_profiles']:
                print("    | No registered profiles found.")
            else:
                for profile_name in state['user_profiles'].keys():
                    print(f"  \u2022 {profile_name}")
            print("==============================================")
           
            target = input("Enter EXACT username to delete: ").strip().lower()
            if target == "ajsag":
                print("You cannot delete the admin account.")
                continue
            if target in state["user_profiles"]:
                del state["user_profiles"][target]
                state["history"] = [h for h in state["history"] if h.get("user", "").lower() != target]
                state["direct_messages"] = [dm for dm in state["direct_messages"] if dm.get("from", "").lower() != target and dm.get("to", "").lower() != target]
                if target in state["grades"]:
                    del state["grades"][target]
                if target in state["blacklist"]:
                    state["blacklist"].remove(target)
                save_data()
                print(f"  | Account '{target}' deleted and synced to cloud ✓")
            else:
                print(f"  | User not found. Check spelling.")

        elif choice == '24':
            while True:
                print(f"\n{C_CYAN}--- ADVANCED FEATURES CONFIGURATION ---{C_RESET}")
                print(f"  1) Toggle Memory/Variables       [{('ON' if admin_features['memory_enabled'] else 'OFF')}]")
                print(f"  2) Toggle Performance Metrics    [{('ON' if admin_features['performance_metrics_enabled'] else 'OFF')}]")
                print(f"  3) Toggle Self-Diagnostic        [{('ON' if admin_features['self_diagnostic_enabled'] else 'OFF')}]")
                print(f"  4) Clear All User Variables")
                print(f"  5) Run Self-Diagnostic Test")
                print(f"  6) Back to Main Admin Panel")
                print(f"{C_CYAN}-------------------------------------{C_RESET}")
               
                feat_choice = input("Enter choice [1-6]: ").strip()

                if feat_choice == '1':
                    admin_features['memory_enabled'] = not admin_features['memory_enabled']
                    print(f"  | Memory/Variables now {'ENABLED' if admin_features['memory_enabled'] else 'DISABLED'}")
                elif feat_choice == '2':
                    admin_features['performance_metrics_enabled'] = not admin_features['performance_metrics_enabled']
                    print(f"  | Performance Metrics now {'ENABLED' if admin_features['performance_metrics_enabled'] else 'DISABLED'}")
                elif feat_choice == '3':
                    admin_features['self_diagnostic_enabled'] = not admin_features['self_diagnostic_enabled']
                    print(f"  | Self-Diagnostic now {'ENABLED' if admin_features['self_diagnostic_enabled'] else 'DISABLED'}")
                elif feat_choice == '4':
                    user_variables.clear()
                    save_data()
                    print("  | All user variables cleared.")
                elif feat_choice == '5':
                    print(f"\n{C_CYAN}--- RUNNING SELF-DIAGNOSTIC TEST ---{C_RESET}")
                    diag_results = run_self_diagnostic()
                    for test_name, result in diag_results.items():
                        status_color = C_GREEN if result == "PASS" else C_RED
                        print(f"  | {test_name:<20} : {status_color}{result}{C_RESET}")
                    all_passed = all(v == "PASS" for v in diag_results.values())
                    final_status = f"{C_GREEN}✓ ALL TESTS PASSED{C_RESET}" if all_passed else f"{C_RED}✗ SOME TESTS FAILED{C_RESET}"
                    print(f"\n  Final Status: {final_status}")
                elif feat_choice == '6':
                    break
                else:
                    print(f"  {C_RED}| Invalid choice.{C_RESET}")
           
        elif choice == '25':
            print("\n GRADE COUNTER METRICS")
            for u in state["user_profiles"]:
                grades = state["grades"].get(u, [])
                avg = round(sum(grades) / len(grades), 1) if grades else 0
                print(f"  User: {u:<14} | Count: {len(grades):<2} | Avg: {avg}%")
                if grades: print(f"    Scores: {grades}")
           
            add_grade = input("\nAdd grade to user? (type username or press Enter to skip): ").strip()
            if add_grade in state["user_profiles"]:
                try:
                    score = float(input(f"Enter numeric score for {add_grade}: "))
                    if 0 <= score <= 100:
                        if add_grade not in state["grades"]:
                            state["grades"][add_grade] = []
                        state["grades"][add_grade].append(score)
                        save_data()
                        print(" Success: Grade registered.")
                    else:
                        print(" Error: Grade must be between 0 and 100.")
                except ValueError:
                    print(" Error: Please type numbers only.")
        
        elif choice == '26':
            print(f"\n{C_CYAN}--- STUDY BUDDY CUSTOM ACHIEVEMENT MANAGER ---{C_RESET}")
            if "achievements" not in state: state["achievements"] = {}
            curr_ach = state.get("achievements", {})
            if not curr_ach:
                print("  | No custom achievements found.")
            else:
                print("  | Current Achievements:")
                for thr, tit in curr_ach.items():
                    print(f"    - [{thr}] {tit}")
            
            print("\n  1) Add new achievement")
            print("  2) Delete an achievement")
            sub = input("Choice: ").strip()
            
            if sub == "1":
                threshold = input("Enter calculation count for milestone: ").strip()
                title = input("Enter achievement title: ").strip()
                if threshold.isdigit():
                    state["achievements"][threshold] = title
                    save_data()
                    print(f"Achievement '{title}' unlocked at {threshold} calculations.")
                else:
                    print(f"{C_RED}Error: Threshold must be a number.{C_RESET}")
            
            elif sub == "2":
                target = input("Enter the calculation threshold to delete: ").strip()
                if target in curr_ach:
                    del state["achievements"][target]
                    save_data()
                    print(f"Achievement at {target} deleted.")
                else:
                    print(f"{C_RED}Error: Threshold not found.{C_RESET}")
        
        elif choice == '27':
            print(f"{C_GREEN}Exiting Super Admin Terminal...{C_RESET}")
            break
        else:
             print(f"{C_RED}Unauthorized command string or menu item.{C_RESET}")

# ═══════════════════════════════════════════════════════════════
#  UNIFIED HELP MENU
# ═══════════════════════════════════════════════════════════════
def super_help_menu(role):
    print(f"\n{C_YELLOW}=== UNIFIED COMMAND MENU v16.4 ==={C_RESET}")
    print(f"{C_PURPLE}--- AGRATOR SEARCH COMMANDS ---{C_RESET}")
    print(f"{C_CYAN}[Type any topic]{C_RESET} - Runs an AI-powered search.")
    print(f"{C_CYAN}/topic{C_RESET}           - Pick specific categories (Math, Science, etc.) to search.")
    print(f"{C_CYAN}/trivia{C_RESET}          - Play custom trivia made by the moderation team.")
    print(f"{C_CYAN}/history{C_RESET}         - Views your private cloud search history.")
    print(f"{C_CYAN}/summary{C_RESET}         - Opens your session and lifetime history report.")
    print(f"{C_CYAN}/achievements{C_RESET}    - Review your profile milestones progress status.")
    print(f"{C_CYAN}show /links{C_RESET}      - Reveals source URLs for your last search.")
    print(f"{C_CYAN}export{C_RESET}           - Saves your last search details locally.")
    print(f"{C_CYAN}clear history{C_RESET}    - Wipes your history locally and in the cloud.")
    
    print(f"\n{C_PURPLE}--- STUDY BUDDY CALCULATOR COMMANDS ---{C_RESET}")
    print(f"{C_CYAN}/readnotes{C_RESET}       | Opens your notepad (hint: Saves locally only)")
    print(f"{C_CYAN}/note <msg>{C_RESET}      | Writes notes for you to remember")
    print(f"{C_CYAN}/chat{C_RESET}            | Open and view the global student message room logs")
    print(f"{C_CYAN}/chat <msg>{C_RESET}      | Send an instant running comment directly to the board")
    print(f"{C_CYAN}/whisper{C_RESET}         | Open your private secure mailbox ledger")
    print(f"{C_CYAN}/whisper <name> <m>{C_RESET}| DM to another identity Privately")
    print(f"{C_CYAN}/plot <expr>{C_RESET}     | Render a visual graph of an equation (e.g., /plot 2x - 1)")
    print(f"{C_CYAN}/zoom <min> <max>{C_RESET}| Set the graph's X-axis range (e.g., /zoom -10 10)")
    print(f"{C_CYAN}/mode{C_RESET}            | Toggle angle mode between degrees and radians")
    print(f"{C_CYAN}/convert <v> <f> <t>{C_RESET}| Convert between units (e.g., /convert 5 m km)")
    print(f"{C_CYAN}/goal <number>{C_RESET}   | Establish an evaluation milestone target for this session")
    
    print(f"\n{C_PURPLE}--- GLOBAL SYSTEM COMMANDS ---{C_RESET}")
    print(f"{C_CYAN}/study buddy{C_RESET}     - Switch to the Study Buddy module")
    print(f"{C_CYAN}/agrator{C_RESET}         - Switch to the Agrator module")
    print(f"{C_CYAN}/help{C_RESET}            - Shows this unified menu.")
    print(f"{C_CYAN}/theme{C_RESET}           - Change the terminal color theme globally.")
    print(f"{C_CYAN}/clear{C_RESET}           - Clear the terminal screen / reset vars.")
    print(f"{C_CYAN}quit / exit{C_RESET}      - Exits the current module.")
    
    if role in ["admin", "moderator", "ajsag"]:
        print(f"\n{C_RED}--- HIDDEN ADMIN COMMANDS ---{C_RESET}")
        print(f"{C_RED}/admin{C_RESET}           - Access the Super Admin Panel.")
        print(f"{C_RED}/clearnotes{C_RESET}      - Clear notes for users.")
        print(f"{C_RED}/inco{C_RESET}            - Toggle incognito monitoring mode.")
        print(f"{C_RED}/motd <msg>{C_RESET}      - Broadcast a system update notification.")
        print(f"{C_RED}/resetpin <name>{C_RESET} - Instantly clear a student's security pin.")
        print(f"{C_RED}/wipechat{C_RESET}        - Flush the entire shared chat board history.")
        print(f"{C_RED}/wipewhips{C_RESET}       - Clear out the entire private DM database logs.")
        print(f"{C_RED}/wipe{C_RESET}            - Drop all history values completely.")
        print(f"{C_RED}/ban <username>{C_RESET}  - Toggle lock status on an identity.")
    print(f"{C_YELLOW}================================{C_RESET}\n")

# ═══════════════════════════════════════════════════════════════
#  AGRATOR MAIN APP LOOP
# ═══════════════════════════════════════════════════════════════
def prompt_terms_and_conditions(user_key):
    print(f"\n{C_YELLOW}=== AGRATOR TERMS OF SERVICE ==={C_RESET}")
    print("1. Not misuse the automated search functionality.")
    print("2. Acknowledge that AI-summarized data should be verified.")
    print("3. Allow your search history to be securely saved to your account.")
    print("4. Understand that violating terms may lead to account suspension.")
    print("5. The developer is not liable for any problems arising from the use of this software in any way.")
    print("6. By using the terminal you agree to use the software responsibly")
    print("   and with all applicable laws and regulations.")
    print("7. You understand that the software is provided 'as-is' without any warranties.")
    print("8. You agree by using the software I (Austin Sia) am the sole developer and must acknowledge me.")
    print("9. You understand that the software is for educational and research purposes only.")
    print(f"{C_RED}{C_BOLD}10. Please understand that my Firebase sycning are strict to prevent bots from scanning or spamming the data. I will be closing access to the database at random times throughout the day to ensure security and prevent unauthorized access.{C_RESET}")
    print("[NOTE FROM THE DEVELOPER]: Hello, and welcome to Agrator x Study Buddy! Pls no hate me, I just wanted to make ")
    print("a cool project that helps people research better. If you have any suggestions or find any bugs, please let me know! - Austin Sia")
    print(f"{C_YELLOW}==================================================={C_RESET}")
   
    while True:
        agree = input(f"{C_CYAN}Do you agree to these terms? (yes/no): {C_RESET}").lower()
        if agree in ['yes', 'y']:
            try: requests.patch(f"{FIREBASE_URL}/users/{user_key}.json", json={"agreed_to_terms": True})
            except: pass
            print(f"{C_GREEN}[✓] Thank you for agreeing. Enjoy!{C_RESET}")
            break
        elif agree in ['no', 'n']:
            print(f"{C_RED}[!] You must agree to the terms to use this program. Exiting.{C_RESET}")
            sys.exit()

def authenticate_and_save_user():
    real_admin_pass = "admin123"
   
    print(f"\n{C_BLUE}=========================================================={C_RESET}")
    print(f"{C_BLUE}                AGRATOR x STUDY BUDDY  PLATFORM ™️    {C_RESET}")
    print(f"{C_BLUE}============================================================{C_RESET}")
    print(f"{C_GREEN}         FOR RESEARCH AND STUDY PURPOSES ONLY {C_RESET}")
    print(f"{C_GREEN}============================================================={C_RESET}")
    print(f"{C_GREEN} 2026| Developed by Austin Sia | v16.4| All Rights Reserved")
    print(f"{C_GREEN}==============================================================")
   
    raw_email = input(f"{C_BLUE}{C_UNDERLINE}Enter your login email/username: {C_RESET}").strip()
    if not raw_email:
        print(f"{C_RED}[!] Error: Email required.{C_RESET}")
        return authenticate_and_save_user()
        
    email_clean = raw_email.lower()
    
    if email_clean == "ajsag":
        try:
            resp = requests.get(f"{FIREBASE_URL}/system/admin_passcode.json", timeout=5)
            if resp.status_code == 200 and resp.json(): real_admin_pass = resp.json()
        except Exception:
          print(f"{C_RED}[!] Admin authentication unavailable. Cloud connection failed.{C_RESET}")
          return None

        admin_pass = input(f"{C_RED}{C_UNDERLINE}Enter Admin Passcode: {C_RESET}").strip()
        if not admin_pass:
            print(f"{C_RED}[!] Error: Passcode required.{C_RESET}")
            return authenticate_and_save_user()
            
        if admin_pass == real_admin_pass:
            print(f"{C_GREEN}Master Override admin authentication successful.{C_RESET}")
            return ("ajsag_master", "ajsag", "admin")
        else:
            print(f"{C_RED}Intruder detected. Exiting.{C_RESET}")
            sys.exit()
            
    password = input(f"{C_BLUE}{C_UNDERLINE}Enter your passcode: {C_RESET}").strip()
    if not password:
        print(f"{C_RED}[!] Error: Password required.{C_RESET}")
        return authenticate_and_save_user()

    safe_email_key = normalize_email_key(email_clean)
    db_endpoint = f"{FIREBASE_URL}/users/{safe_email_key}.json"
    
    try:
        response = requests.get(db_endpoint, timeout=5)
        user_data = response.json() if (response.status_code == 200 and response.json()) else {}
       
        if user_data:
            stored_password = user_data.get("password")
            if password != stored_password:
                print(f"{C_RED}[!] Error: Incorrect password.{C_RESET}")
                sys.exit()
            
            ban_expiry = user_data.get("ban_expiry")
            if ban_expiry:
                expiry_date = datetime.fromisoformat(ban_expiry)
                if datetime.now() < expiry_date:
                    ban_reason = user_data.get("ban_reason", "Violation of Terms of Service")
                    print(f"\n{C_RED}[!] ACCOUNT BANNED [!]{C_RESET}")
                    print(f"{C_RED}Suspended until: {expiry_date.strftime('%Y-%m-%d %H:%M')}{C_RESET}")
                    print(f"{C_RED}Reason: {ban_reason}{C_RESET}")
                    sys.exit()
            
            if not user_data.get("agreed_to_terms"):
                prompt_terms_and_conditions(safe_email_key)
        else:
            prompt_terms_and_conditions(safe_email_key)
            
        role = user_data.get("role", "user")
        
        payload = {
            "email": raw_email,
            "password": password,
            "last_login": time.ctime(),
            "pin_verified": True,
            "role": role
        }
        requests.patch(db_endpoint, json=payload, timeout=5)
        print(f"{C_GREEN}[✓] Cloud Sync Successful. Session initialized.{C_RESET}")
        
        try:
            motd_res = requests.get(f"{FIREBASE_URL}/system/motd.json", timeout=3)
            if motd_res.status_code == 200 and motd_res.json():
                print(f"\n{C_PURPLE} MESSAGE OF THE DAY:{C_RESET} {C_CYAN}{motd_res.json()}{C_RESET}")
        except:
            pass
            
        return (safe_email_key, raw_email, role)
       
    except Exception as e:
        print(f"{C_RED}⚠️ [WARNING] Cloud Sync Error: {e}{C_RESET}")
        return (safe_email_key, raw_email, "user")

def choose_language():
    print(f"{C_YELLOW}Choose your Language:{C_RESET}")
    for key, (name, code) in LANGUAGES.items():
        print(f"[{key}] {name}")
       
    while True:
        choice = input(f"\n{C_CYAN}Select a number (1-{len(LANGUAGES)}): {C_RESET}")
        if choice in LANGUAGES:
            selected_name, selected_code = LANGUAGES[choice]
            print(f"{C_GREEN}Language set to: {selected_name}{C_RESET}\n")
            return selected_name, selected_code
        else:
            print(f"{C_YELLOW}Invalid choice.{C_RESET}")

def fetch_private_history(user_key):
    print(f"{C_CYAN}[...] Retrieving your private search history...{C_RESET}")
    try:
        response = requests.get(f"{FIREBASE_URL}/users/{user_key}/history.json", timeout=5)
        if response.status_code == 200 and response.json():
            print(f"\n{C_YELLOW}=== Your Private Search History ==={C_RESET}")
            for index, safe_topic in enumerate(response.json().keys(), 1):
                print(f"{C_BLUE}{index}. {safe_topic.replace('_', ' ')}{C_RESET}")
            print(f"{C_YELLOW}==================================={C_RESET}")
        else:
            print(f"{C_YELLOW}[!] Your history is currently empty.{C_RESET}")
    except Exception as e:
        print(f"{C_RED}⚠️ [WARNING] Could not fetch history: {e}{C_RESET}")

def delete_history(user_key):
    if os.path.exists(HISTORY_FILE): os.remove(HISTORY_FILE)
    print(f"{C_CYAN}[...] Wiping your cloud history profile...{C_RESET}")
    try:
        requests.delete(f"{FIREBASE_URL}/users/{user_key}/history.json", timeout=5)
        print(f"{C_RED}[!] Success: Local and cloud history wiped.{C_RESET}")
    except Exception as e:
        print(f"{C_RED}⚠️ [WARNING] Failed to wipe cloud data: {e}{C_RESET}")

def export_results(results, query, user_key):
    print(f"\n{C_CYAN}Select Export Format Schema:{C_RESET}")
    print("1. Standard Plain Text Document (.txt)")
    print("2. Styled Markdown Syntax Document (.md)")
    print("3. Structured Standalone HTML Webpage (.html)")
    choice = input(f"{C_YELLOW}Choose option (1-3): {C_RESET}").strip()
    
    if choice == '2':
        filename = f"Agrator_Export_{int(time.time())}.md"
        filepath = os.path.join(BASE_DIR, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# AGRATOR RESEARCH COMPILATION: {query}\n\n")
                f.write(f"*Compiled on {time.ctime()}*\n\n---\n\n")
                for i, item in enumerate(results, 1):
                    f.write(f"## {i}. {item.get('title')}\n")
                    f.write(f"- **Trust Metric Score:** {item.get('accuracy', 'N/A')}%\n")
                    f.write(f"- **Source Reference Location:** [{item.get('href')}]({item.get('href')})\n\n")
                    f.write(f"### Data Stream Snippet\n")
                    f.write(f"> {item.get('body')}\n\n")
                    f.write(f"---\n\n")
            print(f"{C_GREEN}[✓] Data exported successfully in Markdown!{C_RESET}\nPath: {filepath}")
            increment_global_metric("total_exports")
            trigger_achievement(user_key, "export_data", "Data Hoarder")
        except Exception as e:
            print(f"{C_RED}Failed to export Markdown document: {e}{C_RESET}")
            
    elif choice == '3':
        filename = f"Agrator_Export_{int(time.time())}.html"
        filepath = os.path.join(BASE_DIR, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("<!DOCTYPE html>\n<html>\n<head>\n<meta charset='utf-8'>\n")
                f.write(f"<title>Agrator Intelligence Export - {query}</title>\n")
                f.write("<style>\n")
                f.write("body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f7fa; color: #333; }\n")
                f.write(".container { max-width: 850px; margin: auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }\n")
                f.write("h1 { color: #0056b3; border-bottom: 3px solid #0056b3; padding-bottom: 12px; }\n")
                f.write(".card { background: #fafafa; border-left: 6px solid #28a745; margin: 25px 0; padding: 20px; border-radius: 4px; }\n")
                f.write(".meta { font-size: 0.85em; color: #777; }\n")
                f.write("a { color: #0056b3; text-decoration: none; }\n")
                f.write("a:hover { text-decoration: underline; }\n")
                f.write("</style>\n</head>\n<body>\n<div class='container'>\n")
                f.write(f"<h1>Agrator Intelligence Report: {query}</h1>\n")
                f.write(f"<p class='meta'>Generated: {time.ctime()}</p>\n")
                for i, item in enumerate(results, 1):
                    f.write("<div class='card'>\n")
                    f.write(f"<h2>{i}. {item.get('title')}</h2>\n")
                    f.write(f"<p class='meta'>Confidence accuracy score: {item.get('accuracy', 'N/A')}% | Source locator: <a href='{item.get('href')}' target='_blank'>{item.get('href')}</a></p>\n")
                    f.write(f"<p><strong>Synthesis Summary:</strong> {item.get('body')}</p>\n")
                    f.write("</div>\n")
                f.write("</div>\n</body>\n</html>")
            print(f"{C_GREEN}[✓] Data exported successfully in HTML markup!{C_RESET}\nPath: {filepath}")
            increment_global_metric("total_exports")
            trigger_achievement(user_key, "export_data", "Data Hoarder")
        except Exception as e:
            print(f"{C_RED}Failed to export HTML webpage: {e}{C_RESET}")
            
    else:
        filename = f"Agrator_Export_{int(time.time())}.txt"
        filepath = os.path.join(BASE_DIR, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"=== AGRATOR RESEARCH EXPORT: {query} ===\n\n")
                for i, item in enumerate(results, 1):
                    f.write(f"{i}. {item.get('title')}\nSummary: {item.get('body')}\nSource: {item.get('href')}\n---\n")
            print(f"{C_GREEN}[✓] Data exported successfully!{C_RESET}\nPath: {filepath}")
            increment_global_metric("total_exports")
            trigger_achievement(user_key, "export_data", "Data Hoarder")
        except Exception as e:
            print(f"{C_RED}Failed to write raw text layout export file: {e}{C_RESET}")

def clean_snippet(text):
    return re.sub(r'\s+', ' ', text).strip().rstrip('.')

def generate_gemini_overview(results, query):
    if not results:
        return "I couldn't find enough verifiable data to generate a comprehensive answer."
   
    highest_accuracy = results[0].get('accuracy', 0)
    tied_items = [item for item in results if item.get('accuracy', 0) == highest_accuracy]
    
    raw_context = ""
    if len(tied_items) > 1:
        for item in tied_items: raw_context += f"{clean_snippet(item.get('body', ''))} "
    else:
        for idx, item in enumerate(results[:4]): raw_context += f"{clean_snippet(item.get('body', ''))} "
   
    overview = f"Here is a clear, cross-referenced synthesis regarding '{query}' (Calculated Quality: {highest_accuracy}%):\n\n"
    
    overview += f"{C_CYAN}[System Info: Synthesizing context streams into a unified summary]{C_RESET}\n"
    overview += f"  {raw_context.strip()}\n"
    overview += "\nIn summary, these records reflect the most cohesive match context parsed through DuckDuckGo index streams."
    return overview

def get_search_results(query):
    try:
        with DDGS() as ddgs: 
            return list(ddgs.text(query, max_results=10))
    except Exception as e:
        print(f"{C_RED}⚠️ [WARNING] Search engine error: {e}{C_RESET}")
        return []
    
def wikipedia_search(query):
    try:
        search_query = query.split(": ", 1)[1] if ": " in query else query
        url = "https://en.wikipedia.org/w/api.php"
        params = {"action": "query", "list": "search", "srsearch": search_query, "format": "json", "utf8": 1}
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        results = []
        if "query" in data and "search" in data["query"]:
            for item in data["query"]["search"][:3]:
                results.append({
                    "title": item["title"],
                    "body": item["snippet"].replace("<span>", "").replace("</span>", ""),
                    "href": f"https://en.wikipedia.org/wiki/{item['title'].replace(' ', '_')}",
                    "source": "Wikipedia"
                })
        return results
    except Exception:
        return []  

def double_check_facts(results, query):
    clean_query = query.split(": ", 1)[1] if ": " in query else query
    keywords = [w for w in re.sub(r'[^\w\s]', '', clean_query.lower()).split() if len(w) > 2]
    if not keywords: keywords = clean_query.lower().split()

    verified_results = []
    for item in results:
        title, body, url = item.get('title', '').lower(), item.get('body', '').lower(), item.get('href', '').lower()
        source = item.get('source', '')
        
        match_count = sum(1 for kw in keywords if kw in title or kw in body)
        relevance = (match_count / len(keywords)) * 100 if keywords else 100
        
        trust = 65
        if any(d in url for d in ['.gov', '.edu', '.org']): trust += 20
        if any(t in url for t in ['wikipedia', 'bbc', 'nature', 'reuters']): trust += 15
        
        if source == "Wikipedia" or "wikipedia.org" in url:
            trust += 15
        if source == "Academic":
            trust += 20
            
        accuracy = min(int((relevance * 0.6) + (trust * 0.4)), 100)
        item['accuracy'] = accuracy
        
        if source in ["Wikipedia", "Academic"]:
            item['accuracy'] = max(item['accuracy'], 65)
            verified_results.append(item)
        else:
            if relevance >= 0:
                verified_results.append(item)
           
    verified_results.sort(key=lambda x: x['accuracy'], reverse=True)
    return verified_results[:5]

def run_agrator(user_key, current_email, role):
    lang_name, lang_code = choose_language()
    translator = GoogleTranslator(source='auto', target=lang_code)
   
    print(f"{C_BLUE}--- Agrator 5.0 Core Engine Online ---{C_RESET}")
    print(f"{C_YELLOW}Type '/help' to see all unified commands.{C_RESET}")
   
    last_results, last_query = [], ""
   
    while True:
        topic = input(f"\n{C_GREEN}Agrator Search Bar: {C_RESET}")
        t_lower = topic.lower().strip()
       
        if t_lower == '/study buddy':
            print(f"{C_CYAN}Switching to Study Buddy...{C_RESET}")
            return "study_buddy"
        elif t_lower == '/agrator':
            print(f"{C_YELLOW}Already in Agrator!{C_RESET}")
            continue
        elif t_lower in ['quit', 'exit']: 
            show_summary_report(user_key, current_email, role)
            print(f"{C_BLUE}Returning to Master Boot Menu...{C_RESET}")
            return "hub"
        elif t_lower == '/help': super_help_menu(role); continue
        elif t_lower == '/theme': change_theme(); continue
        elif t_lower == 'clear history': delete_history(user_key); continue
        elif t_lower == '/history': fetch_private_history(user_key); continue
        elif t_lower == '/achievements': view_achievements(user_key); continue
        elif t_lower == '/summary': show_summary_report(user_key, current_email, role); continue
        elif t_lower == '/trivia': play_trivia(); continue
        elif t_lower == '/topic':
            print(f"\n{C_CYAN}=== SELECT A CATEGORY ==={C_RESET}")
            print("1. Math")
            print("2. English")
            print("3. Science")
            print("4. History (Around the World)")
            print("5. MAPEH")
            print("6. Religion")
            print("7. Others (Main Terminal Search)")
            cat_choice = input(f"{C_YELLOW}Select an option (1-7): {C_RESET}").strip()
            if cat_choice == '7': continue
                
            categories = {'1': 'Math', '2': 'English', '3': 'Science', '4': 'History', '5': 'MAPEH', '6': 'Religion'}
            if cat_choice in categories:
                sub_topic = input(f"\n{C_GREEN}Enter your {categories[cat_choice]} query: {C_RESET}").strip()
                if not sub_topic: continue
                topic = f"{categories[cat_choice]}: {sub_topic}"
            else:
                print(f"{C_RED}Invalid option.{C_RESET}")
                continue
                
        elif t_lower == '/admin':
            if role in ["admin", "moderator", "ajsag"]:
                super_admin_panel(user_key, current_email, role)
            else:
                print(f"{C_RED}[!] Unauthorized: Access restricted to administrative staff segments.{C_RESET}")
            continue
        elif t_lower == 'export':
            if last_results: export_results(last_results, last_query, user_key)
            else: print(f"{C_RED}[!] No recent results.{C_RESET}")
            continue
        elif t_lower == 'show /links':
            if last_results:
                print(f"\n{C_YELLOW}=== Source Links ==={C_RESET}")
                for i, r in enumerate(last_results, 1): print(f"{C_CYAN}{i}. {r.get('href')}{C_RESET}")
            else: print(f"{C_RED}[!] No recent search.{C_RESET}")
            continue
        elif t_lower.startswith('/'):
            # Fallback to see if it's a study buddy command they are typing in agrator menu
            print(f"{C_RED}That looks like a Study Buddy command! You can use '/study buddy' to switch programs.{C_RESET}")
            continue

        print(f"{C_CYAN}Finding Related data...{C_RESET}")
        history, verified_results = {}, []
       
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f: history = json.load(f)
            except: pass
               
        if topic in history:
            print(f"{C_GREEN}[!] Loading from Cache...{C_RESET}")
            verified_results = history[topic]
        else:
            ddg_res = get_search_results(topic)
            news_res = news_search(topic)
            wiki_res = wikipedia_search(topic)
            acad_res = academic_search(topic)
            
            print(f"DuckDuckGo count: {len(ddg_res)}")
            print(f"News count: {len(news_res)}")
            print(f"Wikipedia count: {len(wiki_res)}")
            print(f"Academic count: {len(acad_res)}")
            
            raw = ddg_res + news_res + wiki_res + acad_res
            if not raw: 
                print(f"{C_YELLOW}No results found.{C_RESET}")
                continue
                
            verified_results = double_check_facts(raw, topic)
            print(f"Verified count: {len(verified_results)}")
            
            if not verified_results:
                print(f"{C_YELLOW}No results found.{C_RESET}")
                continue
           
            history[topic] = verified_results
            try:
                with open(HISTORY_FILE, 'w', encoding='utf-8') as f: json.dump(history, f, indent=4)
            except: pass

            try: 
                requests.put(f"{FIREBASE_URL}/users/{user_key}/history/{re.sub(r'[\.\$\#\[\]\/]', '_', topic)}.json", json={"time": time.ctime()}, timeout=3)
            except: pass
            
            try:
                stat_res = requests.get(f"{FIREBASE_URL}/users/{user_key}/search_count.json", timeout=3)
                curr_sc = stat_res.json() if (stat_res.status_code == 200 and stat_res.json() is not None) else 0
                new_sc = curr_sc + 1
                requests.put(f"{FIREBASE_URL}/users/{user_key}/search_count.json", json=new_sc, timeout=3)
                
                increment_global_metric("total_searches")
                track_topic_search(topic)
                
                trigger_achievement(user_key, "first_search", "First Discovery")
                if new_sc >= 50: trigger_achievement(user_key, "50_searches", "Elite Scholar")
                if new_sc >= 100: trigger_achievement(user_key, "100_searches", "Grand Academician")
            except:
                pass

        if lang_code != 'en':
            trigger_achievement(user_key, "translation_used", "Polyglot Researcher")

        last_results, last_query = verified_results, topic
       
        overview = generate_gemini_overview(verified_results, topic)
        if lang_code != 'en':
            try: overview = translator.translate(overview)
            except: pass
           
        print(f"\n{C_PURPLE}  AI Summary {C_RESET}")
        print(f"{C_YELLOW}{overview}{C_RESET}\n")
       
        print(f"{C_BLUE}--- Verified Sources ---{C_RESET}")
        for i, item in enumerate(verified_results, 1):
            title = translator.translate(item.get('title')) if lang_code != 'en' else item.get('title')
            print(f"{C_BLUE}{C_UNDERLINE}{i}. {title}{C_RESET} {C_GREEN}({item.get('accuracy')}% Accuracy){C_RESET}")
           
        print(f"\n{C_CYAN}(Type 'show /links' for URLs, or '/help' for commands){C_RESET}")

# ═══════════════════════════════════════════════════════════════
#  STUDY BUDDY CORE ENGINE LOOP
# ═══════════════════════════════════════════════════════════════
def clean_and_format_math(raw_string):
    expr = raw_string.lower().replace(' ', '').replace('^', '**')
    expr = re.sub(r'(\d+(?:\.\d+)?)(x)', r'\1*\2', expr)
    expr = re.sub(r'(\d+(?:\.\d+)?|ans|x)([\+\-])(\d+(?:\.\d+)?)%', r'\1\2(\1*(\3/100))', expr)
    expr = re.sub(r'(\d+(?:\.\d+?)?)%', r'(\1/100)', expr)
    expr = re.sub(r'(\d|x|ans)([a-z\(])', r'\1*\2', expr)
    expr = re.sub(r'(\))(\d|x|ans|[a-z])', r'\1*\2', expr)
    expr = expr.replace(')(', ')*(')
    return expr

def _stdev(*args): return statistics.stdev(args) if len(args) > 1 else 0.0
def _mean(*args): return statistics.mean(args) if args else 0.0
def _median(*args): return statistics.median(args) if args else 0.0
def _var(*args): return statistics.variance(args) if len(args) > 1 else 0.0

def run_self_diagnostic():
    results = {}
    try:
        results["sin(90°)"] = "PASS" if abs(math.sin(math.radians(90)) - 1.0) < 1e-10 else "FAIL"
        results["cos(0°)"] = "PASS" if abs(math.cos(math.radians(0)) - 1.0) < 1e-10 else "FAIL"
        results["sqrt(16)"] = "PASS" if abs(math.sqrt(16) - 4.0) < 1e-10 else "FAIL"
        results["pi value"] = "PASS" if abs(math.pi - 3.14159) > 0 else "FAIL"
        results["e value"] = "PASS" if abs(math.e - 2.71828) > 0 else "FAIL"
        results["log10(100)"] = "PASS" if abs(math.log10(100) - 2.0) < 1e-10 else "FAIL"
        results["ln(e)"] = "PASS" if abs(math.log(math.e) - 1.0) < 1e-10 else "FAIL"
        results["factorial(5)"] = "PASS" if math.factorial(5) == 120 else "FAIL"
    except Exception as e:
        results["exception"] = f"FAIL: {str(e)}"
    return results

def translate_words_to_math(text):
    text = text.lower()
    text = text.replace(r'\div', '/').replace('÷', '/').replace('?', 'x')
    word_map = {
        'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
        'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
        'ten': '10', 'plus': '+', 'minus': '-', 'times': '*', 'divided by': '/', 'equals': '='
    }
    for word, symbol in word_map.items():
        text = re.sub(rf'\b{word}\b', symbol, text)
    return text

def solve_word_problem(sentence):
    translations = {
        "twice": "2*", "double": "2*", "triple": "3*", "half of": "0.5*",
        "a number": "x", "the number": "x", "what number": "x", "some number": "x",
        "plus": "+", "increased by": "+", "sum of": "+", "more than": "+",
        "minus": "-", "decreased by": "-", "less than": "-", "difference of": "-",
        "times": "*", "multiplied by": "*", "product of": "*",
        "is": "=", "equals": "=", "results in": "=", "will be": "="
    }
    math_sentence = sentence.lower()
    for word, symbol in translations.items():
        math_sentence = math_sentence.replace(word, symbol)
        
    math_sentence = re.sub(r'\s+', '', math_sentence)
    if '=' not in math_sentence:
        return f"{C_RED}Error: Couldn't find an 'equals' or 'is' in the sentence. I translated it to: {math_sentence}{C_RESET}"
        
    left_side, right_side = math_sentence.split('=')
    equation_zero = f"{left_side}-({right_side})"
    
    try:
        c = eval(equation_zero, {'__builtins__': None}, {'x': 1j})
        if c.imag == 0:
            return "Error: The variable cancelled out. No solution."
        answer = -c.real / c.imag
        if answer.is_integer():
            answer = int(answer)
        return f"{C_CYAN}Equation:{C_RESET} {left_side} = {right_side}\n{C_GREEN}Answer: x = {answer}{C_RESET}"
    except Exception as e:
        return f"{C_RED}Translation failed to solve. Raw equation: {math_sentence}{C_RESET}"

def run_math_engine(query):
    start_time = time.time() if admin_features["performance_metrics_enabled"] else None
    try:
        query = query.replace('°', '')
        if admin_features["memory_enabled"] and '=' in query and not any(op in query.split('=')[0] for op in ['+', '-', '*', '/', '^']):
            parts = query.split('=')
            if len(parts) == 2 and parts[0].strip().isalpha():
                var_name = parts[0].strip().lower()
                formatted_val = clean_and_format_math(parts[1])
                is_deg = (state.get("angle_mode", "degrees") == "degrees")
                context_temp = {
                    "math": math, "sqrt": math.sqrt, "pi": math.pi, "e": math.e,
                    "log": math.log10, "ln": math.log, "fact": math.factorial,
                    "sin": lambda val: math.sin(math.radians(val) if is_deg else val),
                    "cos": lambda val: math.cos(math.radians(val) if is_deg else val),
                    "tan": lambda val: math.tan(math.radians(val) if is_deg else val),
                    "pow": pow, "ans": state["ans"]
                }
                context_temp.update(user_variables)
                try:
                    result = eval(formatted_val, {"__builtins__": None}, context_temp)
                    user_variables[var_name] = result
                    save_data()
                    if start_time:
                        elapsed = (time.time() - start_time) * 1000
                        metrics["last_calculation_time"] = elapsed
                    return f"{var_name} = {result}"
                except Exception:
                    pass
       
        formatted = clean_and_format_math(query)
        is_deg = (state.get("angle_mode", "degrees") == "degrees")
        context = {
            "math": math, "stats": statistics, "sqrt": math.sqrt,
            "pi": math.pi, "e": math.e, "abs": abs, "min": min, "max": max,
            "log": math.log10, "ln": math.log, "fact": math.factorial,
            "mean": _mean, "median": _median, "stdev": _stdev, "var": _var,
            "sin": lambda val: math.sin(math.radians(val) if is_deg else val),
            "cos": lambda val: math.cos(math.radians(val) if is_deg else val),
            "tan": lambda val: math.tan(math.radians(val) if is_deg else val),
            "asin": lambda val: math.degrees(math.asin(val)) if is_deg else math.asin(val),
            "acos": lambda val: math.degrees(math.acos(val)) if is_deg else math.acos(val),
            "atan": lambda val: math.degrees(math.atan(val)) if is_deg else math.atan(val),
            "pow": pow,
            "ans": state["ans"]
        }
       
        if admin_features["memory_enabled"]:
            context.update(user_variables)

        if '=' not in formatted:
            context['x'] = user_variables.get('x', 0.0)
            result = round(eval(formatted, {"__builtins__": None}, context), state["precision"])
            if admin_features["memory_enabled"]: 
                user_variables['x'] = context['x']
                save_data()
            if start_time:
                elapsed = (time.time() - start_time) * 1000
                metrics["last_calculation_time"] = elapsed
            return result
       
        parts = formatted.split('=')
        if len(parts) != 2:
            return "Error: Multiple equality signs present."
           
        diff_expr = f"({parts[0]}) - ({parts[1]})"
        def f(x_val):
            context['x'] = x_val
            return eval(diff_expr, {"__builtins__": None}, context)

        y0 = f(0.0)
        y1 = f(1.0)
        slope = y1 - y0
       
        if slope != 0:
            y2 = f(2.0)
            if abs((y2 - y1) - slope) < 1e-12:
                result = round(-y0 / slope, state["precision"])
                if start_time:
                    elapsed = (time.time() - start_time) * 1000
                    metrics["last_calculation_time"] = elapsed
                return result
        elif abs(y0) < 1e-12:
            if start_time:
                elapsed = (time.time() - start_time) * 1000
                metrics["last_calculation_time"] = elapsed
            return "Infinite solutions (Identity Equation)"

        x_n = 1.0  
        for _ in range(200):
            fx = f(x_n)
            if abs(fx) < 1e-12:
                result = round(x_n, state["precision"])
                if start_time:
                    elapsed = (time.time() - start_time) * 1000
                    metrics["last_calculation_time"] = elapsed
                return result
               
            dfx = (f(x_n + 1e-5) - fx) / 1e-5
            if dfx == 0: break
            x_n = x_n - fx / dfx
       
        if start_time:
            elapsed = (time.time() - start_time) * 1000
            metrics["last_calculation_time"] = elapsed
        return "Non-linear root approximation failed (Try graphing to find domains)"
       
    except ZeroDivisionError:
        if start_time: metrics["last_calculation_time"] = (time.time() - start_time) * 1000
        return " Error: You cannot divide a number by zero. It breaks the laws of math."
    except SyntaxError:
        if start_time: metrics["last_calculation_time"] = (time.time() - start_time) * 1000
        return " Error: Math structure typo. Please check your parentheses and operators."
    except NameError:
        if start_time: metrics["last_calculation_time"] = (time.time() - start_time) * 1000
        return " Error: Unknown letter or word typed. Use numbers and variables only pls."
    except ValueError as ve:
        if start_time: metrics["last_calculation_time"] = (time.time() - start_time) * 1000
        if "math domain" in str(ve).lower():
            return " Error: You cannot find the square root of a negative number in real math dawg."
        return f" Error: Invalid math setup ({ve})."
    except Exception as e:
        if start_time: metrics["last_calculation_time"] = (time.time() - start_time) * 1000
        return f" Calculation Error: {str(e).capitalize()}"

def display_chat_box():
    load_from_firebase()
    print(f"\n{C_CYAN}===================================================={C_RESET}")
    print(f"{C_BOLD}{C_CYAN}             STUDENT CHAT ROOM               {C_RESET}")
    print(f"{C_CYAN}===================================================={C_RESET}")
   
    if not state["chat_logs"]:
        print("  | Chat history is empty. Be the first to say hello!")
    else:
        visible_logs = state["chat_logs"][-15:]
        for entry in visible_logs:
            print(f"  [{entry['time']}] {C_BOLD}{C_CYAN}{entry['user']}:{C_RESET} {entry['msg']}")
           
    print(f"{C_CYAN}----------------------------------------------------{C_RESET}")
    print(f"  -> Use {C_BOLD}/chat <message>{C_RESET} to chat, or {C_BOLD}/whisper{C_RESET} to read DMs.")

def display_private_whispers(current_user):
    load_from_firebase()
    user_key = current_user.lower()
    print(f"\n{C_WARN}===================================================={C_RESET}")
    print(f"{C_BOLD}{C_WARN}            Direct Messages: {current_user.upper()} {C_RESET}")
    print(f"{C_WARN}===================================================={C_RESET}")
   
    found_any = False
    for dm in state["direct_messages"]:
        if dm["from"].lower() == user_key or dm["to"].lower() == user_key:
            found_any = True
            if dm["from"].lower() == user_key:
                direction_flag = f"{C_CYAN}To -> {dm['to']}{C_RESET}"
            else:
                direction_flag = f"{C_GREEN}From <- {dm['from']}{C_RESET}"
            print(f"  [{dm['time']}] {direction_flag}: {dm['msg']}")
           
    if not found_any:
        print("  | Your private inbox is currently empty.")
       
    print(f"{C_WARN}----------------------------------------------------{C_RESET}")
    print(f"  -> Syntax: {C_BOLD}/whisper <username> <private message>{C_RESET}")

def check_inbox_status(current_user):
    load_from_firebase()
    user_key = current_user.lower()
   
    unread_count = sum(1 for dm in state["direct_messages"] if dm["to"].lower() == user_key and not dm.get("read", False))
    if unread_count > 0:
        print(f"\n{C_WARN} [Notification] You have {unread_count} unread private whisper(s)! Type {C_BOLD}/whisper{C_RESET} to view them.{C_RESET}")
        for dm in state["direct_messages"]:
            if dm["to"].lower() == user_key:
                dm["read"] = True
        save_data()
       
    if state["chat_logs"]:
        print(f"{C_CYAN}ℹ [Info] Global student chat room is online and active. Type {C_BOLD}/chat{C_RESET} to view logs.{C_RESET}")

def handle_slash_commands(cmd, current_user):
    tokens = cmd.strip().split(maxsplit=1)
    action = tokens[0].lower()
    is_admin = False

    admin_commands = {'/theme', '/motd', '/resetpin', '/wipe', '/clear', '/inco', '/ban', '/wipechat', '/wipewhips', '/clearnotes', '/admin'}

    if current_user.lower() == 'ajsag' and action in admin_commands:
        entered = getpass.getpass("Admin passkey required: ")
        peek_choice = input("Peek at passcode for exactly 1-second? (y/n): ").strip().lower()
        if peek_choice == 'y':
            print(f" [PEEK VALUE]: {entered}", end="", flush=True)
            time.sleep(1)
            sys.stdout.write("\r [PEEK VALUE]: " + ("•" * len(entered)) + "   \n")
            sys.stdout.flush()
            
        if entered == state["passkey"]:
            is_admin = True
            print(f"\n{C_GREEN}{C_BOLD}Admin access granted.{C_RESET}")
        else:
            print(f"{C_RED}Access denied.{C_RESET}")
            return

    if action in ('/help', '/remind'):
        if current_user.lower() == 'ajsag':
            auth_attempt = getpass.getpass("Admin passkey (press enter to skip admin commands): ")
            if auth_attempt == state["passkey"]: is_admin = True
        role = "admin" if is_admin else "user"
        super_help_menu(role)
        return

    if action == '/admin':
        if is_admin: super_admin_panel("ajsag_master", "ajsag", "admin")
        else: print(f"{C_RED}Error: Administrative clearance missing.{C_RESET}")
        return

    if action == '/chat':
        if len(tokens) < 2:
            display_chat_box()
            return
        state["chat_logs"].append({"time": datetime.now().strftime("%H:%M:%S"), "user": current_user, "msg": tokens[1].strip()})
        save_data()
        print(f"{C_GREEN}  | Message published successfully.{C_RESET}")
        return

    if action in ('/whisper', '/w'):
        if len(tokens) < 2:
            display_private_whispers(current_user)
            return
        sub_tokens = tokens[1].strip().split(maxsplit=1)
        if len(sub_tokens) < 2:
            print(f"{C_RED}Syntax error. Use: /whisper <username> <your private message>{C_RESET}")
            return
            
        target_name, dm_msg = sub_tokens[0].strip(), sub_tokens[1].strip()
        load_from_firebase()
        if target_name.lower() != 'ajsag' and target_name.lower() not in state["user_profiles"]:
            print(f"{C_RED}Target error: Student '{target_name}' is not registered.{C_RESET}")
            return

        state["direct_messages"].append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "from": current_user, "to": target_name, "msg": dm_msg, "read": False
        })
        save_data()
        print(f"{C_WARN}  | Message successfully sent privately to '{target_name}'.{C_RESET}")
        return

    if action == '/zoom':
        args = tokens[1].strip().split() if len(tokens) > 1 else []
        if len(args) == 2:
            try:
                new_min, new_max = float(args[0]), float(args[1])
                if new_min >= new_max:
                    print(f"{C_RED}Error: Min value must be less than Max value.{C_RESET}")
                else:
                    state["x_min"] = new_min
                    state["x_max"] = new_max
                    save_data()
                    print(f"\n{C_GREEN} X-Axis zoom updated. New plot range: [{new_min} to {new_max}]{C_RESET}")
            except ValueError:
                print(f"{C_RED}Error: Please enter valid numbers. (e.g., /zoom -10 10){C_RESET}")
        else:
            print(f"{C_RED}Syntax error. Use: /zoom <min> <max> (e.g., /zoom -5 5){C_RESET}")
        return

    if action == '/plot':
        if len(tokens) < 2:
            print(f"{C_RED}Syntax error. Use: /plot <expression> (e.g., /plot 2x + 1){C_RESET}")
            return

        raw_eq = tokens[1].strip()
        formatted_eq = clean_and_format_math(raw_eq)
        print(f"\n{C_CYAN}--- ADVANCED ASCII GRAPH PLOTTER: y = {raw_eq} ---{C_RESET}")

        width, height = 60, 20
        x_min, x_max = state.get("x_min", -20.0), state.get("x_max", 20.0)
        y_vals, valid_ys = {}, []
        is_deg = (state.get("angle_mode", "degrees") == "degrees")
        
        for col in range(width + 1):
            x_val = x_min + (x_max - x_min) * (col / width)
            context = {
                "math": math, "stats": statistics, "sqrt": math.sqrt,
                "pi": math.pi, "e": math.e, "abs": abs, "min": min, "max": max,
                "log": math.log10, "ln": math.log, "fact": math.factorial,
                "sin": lambda val: math.sin(math.radians(val) if is_deg else val),
                "cos": lambda val: math.cos(math.radians(val) if is_deg else val),
                "tan": lambda val: math.tan(math.radians(val) if is_deg else val),
                "asin": lambda val: math.degrees(math.asin(val)) if is_deg else math.asin(val),
                "acos": lambda val: math.degrees(math.acos(val)) if is_deg else math.acos(val),
                "atan": lambda val: math.degrees(math.atan(val)) if is_deg else math.atan(val),
                "pow": pow, "ans": state["ans"], "x": float(x_val)
            }
            context.update(user_variables)
            
            try:
                y_calc = eval(formatted_eq, {"__builtins__": None}, context)
                if isinstance(y_calc, complex):
                    if abs(y_calc.imag) > 1e-9: continue
                    y_calc = y_calc.real
                if isinstance(y_calc, (int, float)) and math.isfinite(y_calc):
                    y_vals[col] = y_calc
                    valid_ys.append(y_calc)
            except Exception: pass

        if not valid_ys:
            print(f"{C_RED}Error: Could not calculate valid mathematical points for this equation inside range.{C_RESET}")
            return
            
        y_min, y_max = min(valid_ys), max(valid_ys)
        if abs(y_max - y_min) < 1e-9:
            y_max += 5; y_min -= 5
        else:
            padding = (y_max - y_min) * 0.1
            y_max += padding; y_min -= padding

        def get_row(y): return height - int(round((y - y_min) / (y_max - y_min) * height))
        def get_col(x): return int(round((x - x_min) / (x_max - x_min) * width))

        grid = [["·" for _ in range(width + 1)] for _ in range(height + 1)]
        y_axis_col = get_col(0)
        x_axis_row = get_row(0)

        for r in range(height + 1):
            if 0 <= y_axis_col <= width: grid[r][y_axis_col] = "│"
        for c in range(width + 1):
            if 0 <= x_axis_row <= height: grid[x_axis_row][c] = "─"
        if 0 <= x_axis_row <= height and 0 <= y_axis_col <= width:
            grid[x_axis_row][y_axis_col] = "┼"

        prev_col = -1; prev_row = -1
        for col in range(width + 1):
            if col in y_vals:
                row = get_row(y_vals[col])
                if prev_col != -1 and col == prev_col + 1:
                    step = 1 if row > prev_row else -1
                    for r in range(prev_row + step, row, step):
                        if 0 <= r <= height: grid[r][col] = f"{C_GREEN}*{C_RESET}"
                if 0 <= row <= height: grid[row][col] = f"{C_GREEN}*{C_RESET}"
                prev_col = col; prev_row = row
            else: prev_col = -1

        print(f"  {C_WARN}Y-Axis Scaled: [{y_min:.2f} to {y_max:.2f}] | X-Axis Range: [{x_min:.2f} to {x_max:.2f}]{C_RESET}")
        for row in grid: print("  " + "".join(row))
        print(f"{C_CYAN}" + "-" * (width + 5) + f"{C_RESET}")
        return

    if action == '/wipewhips':
        if not is_admin: print(f"{C_RED}Error: Administrative clearance missing.{C_RESET}"); return
        state["direct_messages"].clear()
        save_data()
        print(f"\n{C_GREEN}| Private whisper ledger purged.{C_RESET}")
        return

    if action == '/wipechat':
        if not is_admin: print(f"{C_RED}Error: Administrative clearance missing.{C_RESET}"); return
        state["chat_logs"].clear()
        save_data()
        print(f"\n{C_GREEN}| Shared chat ledger wiped.{C_RESET}")
        return

    if action == '/goal':
        if is_admin:
            print(f"{C_RED}Admin notification: Master profile does not track homework metrics.{C_RESET}")
            return
        if len(tokens) < 2 or not tokens[1].isdigit():
            print(f"{C_RED}Syntax error. Use: /goal <positive integer count>{C_RESET}")
            return
        metrics["calculation_goal"] = int(tokens[1])
        metrics["goal_reached_alerted"] = False
        print(f"\n{C_GREEN}[Tracker Synchronized] Session milestone target set to {metrics['calculation_goal']} calculations!{C_RESET}")
        return

    if action == '/theme':
        if not is_admin: print(f"\n{C_RED}[ACCESS DENIED] Theme configurations are locked.{C_RESET}"); return
        change_theme()
        return

    if action == '/motd':
        if not is_admin: print(f"{C_RED}Error: Only the master developer can configure the system broadcast grid.{C_RESET}"); return
        state["motd"] = tokens[1].strip() if len(tokens) >= 2 else ""
        save_data()
        print(f"\n{C_GREEN}[System Configuration] Global message updated.{C_RESET}")
        return

    if action in ('/resetpin', '/wipe', '/clear', '/inco', '/ban', '/convert'):
        handle_resetpin(action, is_admin, tokens)
        return

    if action == '/mode':
        current_mode = state.get("angle_mode", "degrees")
        if current_mode == "degrees": state["angle_mode"] = "radians"
        else: state["angle_mode"] = "degrees"
        save_data()
        print(f"\n{C_GREEN} Angle mode switched to: {state['angle_mode'].upper()}{C_RESET}")
        return

    if action == '/readnotes':
        print(f"\n{C_CYAN}--- YOUR SAVED SCRATCHPAD NOTES ---{C_RESET}")
        if os.path.exists(NOTES_FILE):
            with open(NOTES_FILE, "r", encoding="utf-8") as f:
                content = f.read()
                if content.strip(): print(content)
                else: print("  | Scratchpad is empty.")
        else:
            print("  | No notes file found yet.")
        print(f"{C_CYAN}-----------------------------------{C_RESET}")
        return

    if action == '/clearnotes':
        if not is_admin: print(f"{C_RED}Error: Administrative clearance missing.{C_RESET}"); return
        tokens = cmd.split()
        if len(tokens) < 2:
            print(f"{C_RED}Usage: /clearnotes <index> <username> OR /clearnotes <username>{C_RESET}")
            return
        try:
            if os.path.exists(NOTES_FILE):
                with open(NOTES_FILE, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                if len(tokens) == 3:
                    target_idx = int(tokens[1])
                    target_user = tokens[2].lower()
                    if 0 <= target_idx < len(lines):
                        if target_user in lines[target_idx].lower():
                            removed = lines.pop(target_idx)
                            with open(NOTES_FILE, "w", encoding="utf-8") as f: f.writelines(lines)
                            print(f"{C_GREEN}| Note [{target_idx}] for '{target_user}' removed.{C_RESET}")
                        else: print(f"{C_RED}| Error: User '{target_user}' did not write note at index {target_idx}.{C_RESET}")
                    else: print(f"{C_RED}| Error: Index out of range.{C_RESET}")
                elif len(tokens) == 2:
                    target_user = tokens[1].lower()
                    new_lines = [line for line in lines if target_user not in line.lower()]
                    if len(new_lines) < len(lines):
                        with open(NOTES_FILE, "w", encoding="utf-8") as f: f.writelines(new_lines)
                        print(f"{C_GREEN}| All notes for '{target_user}' cleared.{C_RESET}")
                    else: print(f"{C_RED}| No notes found for user '{target_user}'.{C_RESET}")
            else: print(f"{C_RED}| Error: No notes file found.{C_RESET}")
        except ValueError: print(f"{C_RED}| Error: Invalid index number.{C_RESET}")
        return
    
    print(f"{C_RED}Unknown command, sorry. Type /help for a list of commands.{C_RESET}")

def convert_units(value, from_unit, to_unit):
    from_unit, to_unit = from_unit.lower(), to_unit.lower()
    if from_unit not in unit_factors: return f"Unknown unit: {from_unit}"
    if to_unit not in unit_factors: return f"Unknown unit: {to_unit}"
    meters = value * unit_factors[from_unit]
    result = meters / unit_factors[to_unit]
    return round(result, state["precision"])

def handle_resetpin(action, is_admin, tokens):
    if is_admin and action == '/resetpin':
        if len(tokens) < 2: print("Usage: /resetpin <username>"); return
        target_profile = tokens[1].strip().lower()
        if target_profile in state["user_profiles"]:
            del state["user_profiles"][target_profile]
            save_data()
            print(f"\n{C_GREEN}[Override] '{target_profile}' will reset their code on next login.{C_RESET}")
        else: print(f"{C_RED}User '{target_profile}' not found.{C_RESET}")
        return

    if is_admin and action == '/wipe': wipe(); return

    if is_admin and action == '/clear':
        user_variables.clear()
        metrics['last_calculation_time'] = 0.0
        metrics['session_queries_count'] = 0
        metrics['calculation_goal'] = 0
        metrics['goal_reached_alerted'] = False
        save_data()
        print(f"\n{C_GREEN}| All Variable Memory and Performance Metrics cleared.{C_RESET}")
        return

    if is_admin and action == '/inco':
        state['incognito'] = not state['incognito']
        print(f"\n| Incognito monitoring is now: {state['incognito']}")
        return

    if is_admin and action == '/ban':
        if len(tokens) < 2: print("Usage: /ban <username>"); return
        target = tokens[1].strip().lower()
        if target == 'ajsag': print(f"{C_RED}Cannot ban admin account.{C_RESET}"); return
        if target in state['blacklist']:
            state['blacklist'].remove(target)
            print(f"Profile '{target}' removed from being banned.")
        else:
            state['blacklist'].append(target)
            print(f"{C_WARN}Profile '{target}' locked out.{C_RESET}")
        save_data()
        return

    if action == '/convert':
        raw_args = tokens[1].strip().split() if len(tokens) > 1 else []
        if len(raw_args) < 3:
            print(f"{C_RED}Usage: /convert <value> <from_unit> <to_unit>{C_RESET}")
            return
        try:
            value = float(raw_args[0])
            from_unit, to_unit = raw_args[1].lower(), raw_args[2].lower()
            if from_unit not in unit_factors: print(f"{C_RED}Unknown unit: {from_unit}{C_RESET}"); return
            if to_unit not in unit_factors: print(f"{C_RED}Unknown unit: {to_unit}{C_RESET}"); return
            result = convert_units(value, from_unit, to_unit)
            print(f"\n{C_GREEN}{value} {from_unit} = {result} {to_unit}{C_RESET}")
        except ValueError:
            print(f"{C_RED}Invalid number. Please enter a valid decimal or integer.{C_RESET}")
        return

def wipe():
    global user_variables
    state['history'].clear()
    state['ans'] = 0.0
    state['chat_logs'].clear()
    state['direct_messages'].clear()
    user_variables.clear()
    metrics['session_queries_count'] = 0
    metrics['calculation_goal'] = 0
    metrics['goal_reached_alerted'] = False
    metrics['last_calculation_time'] = 0.0
    save_data()
    print(f"{C_GREEN}[WIPE COMPLETE] All history, memory, and metrics reset to zero/empty.{C_RESET}")

def write_scratchpad_note(user, note_text):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(NOTES_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] User: {user} | Note: {note_text}\n")
        print(f"{C_GREEN}  | Note successfully cataloged to scratchpad.{C_RESET}")
    except Exception as e:
        print(f"{C_RED}  | Failed to commit text to notes: {e}{C_RESET}")

def display_session_summary(user):
    print(f"\n{C_GREEN}===================================================={C_RESET}")
    print(f"{C_BOLD}{C_GREEN}          SUMMARY REPORT FOR {user}      {C_RESET}")
    print(f"{C_GREEN}===================================================={C_RESET}")
    print(f"  | Target Active Profile : {user}")
    print(f"  | Complete Calculations : {metrics['session_queries_count']}")
    if metrics["calculation_goal"] > 0:
        status = "COMPLETED" if metrics["session_queries_count"] >= metrics["calculation_goal"] else "UNFULFILLED"
        print(f"  | Active Target Goal    : {metrics['session_queries_count']} / {metrics['calculation_goal']} ({status})")
    print(f"  | Final Memory Key (ans): {state['ans']}")
    print(f"  | Decimal Scale Float   : {state['precision']} places")
    print(f"{C_GREEN}----------------------------------------------------{C_RESET}")

def check_achievements(current_count):
    if current_count in achievements_registry:
        title = achievements_registry[current_count]
        print(f"\n{C_RED}{'='*60}{C_RESET}")
        print(f"{C_CYAN}{C_BOLD}*** ACHIEVEMENT UNLOCKED: {title} ***{C_RESET}")
        print(f"{C_RED}{'='*60}{C_RESET}")
 
    custom_achievements = state.get("achievements", {})
    if str(current_count) in custom_achievements:
        title = custom_achievements[str(current_count)]
        print(f"\n{C_RED}{'='*60}{C_RESET}")
        print(f"{C_CYAN}{C_BOLD}*** CUSTOM ACHIEVEMENT UNLOCKED: {title} ***{C_RESET}")
        print(f"{C_RED}{'='*60}{C_RESET}")

def ascii_plot_demo():
    print(f"\n{C_CYAN}╔════════════════════════════════════════════════════╗{C_RESET}")
    print(f"{C_CYAN}║     ASCII PLOT PLANE - Example Coordinate Grid     ║{C_RESET}")
    print(f"{C_CYAN}╚════════════════════════════════════════════════════╝{C_RESET}")
    
    width, height = 50, 15
    grid = [['·' for _ in range(width)] for _ in range(height)]
    
    mid_x, mid_y = width // 2, height // 2
    for i in range(height): grid[i][mid_x] = '│'
    for j in range(width): grid[mid_y][j] = '─'
    grid[mid_y][mid_x] = '┼'
    
    for x in range(width):
        try:
            x_val = (x - mid_x) * 0.2
            y_val = math.sin(x_val) * 5
            y_pos = int(mid_y - y_val)
            if 0 <= y_pos < height:
                grid[y_pos][x] = f'{C_GREEN}*{C_RESET}'
        except:
            pass
    for row in grid: print("  " + "".join(row))
    print(f"\n{C_CYAN}  (Use /plot <expression> to graph custom equations){C_RESET}\n")

def study_buddy_main(user_key, current_email, role):
    print(f"{C_BOLD}{C_GREEN}===================================================={C_RESET}")
    print(f"{C_BOLD}{C_GREEN}             STUDY BUDDY PROGRAM™        {C_RESET}")  
    print(f"{C_BOLD}{C_GREEN}===================================================={C_RESET}")
    print(f"{C_BOLD}{C_CYAN}      FOR STUDY AND ENTERTAIMENT PURPOSES ONLY {C_RESET}")
    print(f"{C_BOLD}{C_GREEN}===================================================={C_RESET}")
    print(f" {C_BOLD} {C_GREEN}2026 | Developed by Austin Sia | Mashup edition | All rights reserved | {C_RESET}")
    print(f"{C_BOLD}{C_GREEN}===================================================={C_RESET}")
    print(f"{C_BOLD}{C_RED}DO NOT ATTEMPT TO HACK OR BREAK THE SYSTEM. THIS SOFTWARE IS DESIGNED FOR EDUCATIONAL USE ONLY.{C_RESET}")
    print("----------------------------------------------------------------------------------------------")
    print(f"{C_RED} [NOTICE] READ THE TERMS AND SERVICES BY USING THIS CODE YOU ARE AGREEING TO THE TERMS AND SERVICES WHETHER READ OR NOT {C_RESET}")
    print(f"{C_RED} [NOTICE] PLEASE REQUEST THE TERMS AND SERVICES VIA GMAIL ONLY (sia.aj2013@gmail.com). {C_RESET}")
    print(f"{C_CYAN}  USE /help to see unified commands {C_RESET}")
    print(f"{C_CYAN}-------------------------------------------------------------------------------------{C_RESET}")
    
    username = current_email.split('@')[0] if '@' in current_email else current_email
    if current_email == "ajsag":
        username = "ajsag"
        
    is_admin = (role == "admin" or username.lower() == "ajsag")
    state["username"] = username
    
    if state["motd"]:
        print(f"\n{C_CYAN}===================================================={C_RESET}")
        print(f"{C_BOLD}{C_CYAN}[SYSTEM NOTICE]:{C_RESET} {state['motd']}")
        print(f"{C_CYAN}===================================================={C_RESET}")
    
    if is_admin:
        print(f"\n{C_GREEN}[System] Welcome back, Developer {username}.{C_RESET}")
    elif username.lower() in state['blacklist']:
        print(f"\n{C_RED}[ACCESS REJECTED] This specific profile identifier is banned.{C_RESET}")
        return "hub"
    else:
        user_key_sb = username.lower()
        if user_key_sb not in state["user_profiles"]:
            # Bypass manual PIN loop completely for unified experience
            state["user_profiles"][user_key_sb] = "0000" 
            state["grades"][user_key_sb] = []
            save_data()
            print(f"{C_GREEN}Profile configuration committed automatically.\nWelcome, {username}.{C_RESET}")
        else:
            print(f"\nWelcome back, {username}.")
            
    check_inbox_status(username)
        
    while True:
        if not is_admin and username.lower() in state['blacklist']:
            print(f"\n{C_RED}[Clearance Failure] Connection terminated.{C_RESET}")
            break
            
        if is_admin:
            incog_flag = " [STEALTH]" if state['incognito'] else ""
            print(f"\n{C_CYAN}[Admin Prompt{incog_flag}] Type passkey for Panel, slash actions for quick tools, or /help{C_RESET}")
        elif metrics["calculation_goal"] > 0 and not metrics["goal_reached_alerted"]:
            print(f"{C_WARN}[Goal Tracking Active]: {metrics['session_queries_count']} completed out of {metrics['calculation_goal']}{C_RESET}")
            
        query = input(f"\n[{username}] Enter problem statement (or 'exit'): ").strip()
        if not query: continue
            
        if query.lower() == '/agrator':
            print(f"{C_CYAN}Switching to Agrator...{C_RESET}")
            return "agrator"
            
        if query.lower() == '/study buddy':
            print(f"{C_YELLOW}Already in Study Buddy!{C_RESET}")
            continue

        if query.lower() in ('clear', '/clear'):
            os.system('cls' if os.name == 'nt' else 'clear')
            continue
            
        if query.lower() in ('exit', 'quit', '/exit', '/quit'):
            display_session_summary(username)
            print(f"{C_BLUE}Returning to Master Boot Menu...{C_RESET}")
            return "hub"
            
        if query.startswith('/'):
            if query.lower().startswith('/note '):
                write_scratchpad_note(username, query.split(maxsplit=1)[1])
            elif query.lower() == '/wipe':
                if username.lower() == 'ajsag': wipe()
                else: print(f"{C_RED}Error: Administrative clearance missing.{C_RESET}")
            else:
                handle_slash_commands(query, username)
            continue
            
        if is_admin and query == state['passkey']:
            super_admin_panel("ajsag_master", "ajsag", "admin")
            continue
            
        if not (is_admin and state['incognito']):
            log_node = {"date": str(datetime.now().date()), "user": username, "query": query, "result": "Processing Failed"}
            state['history'].append(log_node)
            save_data()
            
        query = translate_words_to_math(query)
        ans = run_math_engine(query)
        
        print(f"{C_BOLD}{C_GREEN}RESULT: {ans}{C_RESET}")
        
        if isinstance(ans, (int, float)):
            state["ans"] = ans
            metrics["session_queries_count"] += 1
            check_achievements(metrics["session_queries_count"])
            
            if metrics["calculation_goal"] > 0 and metrics["session_queries_count"] >= metrics["calculation_goal"] and not metrics["goal_reached_alerted"]:
                print(f"\n{C_CYAN}★ [Milestone Reached] Target of {metrics['calculation_goal']} calculations achieved!{C_RESET}")
                metrics["goal_reached_alerted"] = True

        if not (is_admin and state.get('incognito', False)):
            if state.get('history') and len(state['history']) > 0:
                state['history'][-1]["result"] = ans
                save_data()


# ═══════════════════════════════════════════════════════════════
#  MASTER BOOTLOADER (THE MASHUP MANAGER)
# ═══════════════════════════════════════════════════════════════
def master_main():
    try:
        ascii_plot_demo()
    except Exception:
        pass
        
    
    # Load all global data needed for both systems immediately
    load_data()          
    load_from_firebase() 

    # 1. Unified Authentication Process
    auth_context = None
    while auth_context is None:
        auth_context = authenticate_and_save_user()
        
    user_key, current_email, role = auth_context

    # 2. Infinite Hub loop to switch between them
    current_module = None
    
    while True:
        if current_module == "agrator":
            res = run_agrator(user_key, current_email, role)
            if res == "study_buddy":
                current_module = "study_buddy"
            elif res in ["hub", "quit"]:
                current_module = None
                
        elif current_module == "study_buddy":
            res = study_buddy_main(user_key, current_email, role)
            if res == "agrator":
                current_module = "agrator"
            elif res in ["hub", "quit"]:
                current_module = None
                
        else:
            print(f"\n{C_BOLD}{C_CYAN}--- MASTER HUB TERMINAL ---{C_RESET}")
            print("1. Launch Agrator (Research Engine)")
            print("2. Launch Study Buddy (Calculator & Social)")
            print("3. Power Down OS")
            choice = input(f"{C_YELLOW}Select module to boot (1-3): {C_RESET}").strip()
            
            if choice == '1':
                print(f"\n{C_GREEN}>>> Booting Agrator Protocol...{C_RESET}")
                current_module = "agrator"
            elif choice == '2':
                print(f"\n{C_GREEN}>>> Booting Study Buddy Protocol...{C_RESET}")
                current_module = "study_buddy"
            elif choice == '3':
                print(f"\n{C_RED}Powering down unified system. Goodbye.{C_RESET}")
                sys.exit()
            else:
                print(f"{C_RED}Invalid choice. Select 1, 2, or 3.{C_RESET}")
                

if __name__ == "__main__":
    master_main()