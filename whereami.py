#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║                        WHERE AM I? v3.0                             ║
║              Interactive OSINT — Email & Phone Scanner                ║
║                                                                      ║
║  Just run the tool, enter your target, and get results.               ║
║  Auto-installs dependencies on first run.                             ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import subprocess
import importlib
import json
import re
import hashlib
import time
import urllib.parse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ──────────────────────────────────────────────────────────────────────────
# AUTO-INSTALL DEPENDENCIES
# ──────────────────────────────────────────────────────────────────────────

REQUIRED_PACKAGES = {
    "requests": "requests",
    "bs4": "beautifulsoup4",
}

OPTIONAL_PACKAGES = {
    "holehe": "holehe",
    "phoneinfoga": "phoneinfoga",
}

def check_and_install(package_name, pip_name, required=True):
    """Check if a package is installed, install if not."""
    try:
        importlib.import_module(package_name)
        return True
    except ImportError:
        pass
    
    label = "[REQUIRED]" if required else "[OPTIONAL]"
    msg = f"{label} Installing {pip_name}..."
    
    # Color handling
    try:
        print(f"\033[93m{msg}\033[0m")
    except:
        print(msg)
    
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", pip_name, "-q"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=60
        )
        print(f"  ✅ {pip_name} installed successfully")
        return True
    except Exception as e:
        if required:
            print(f"  ❌ Failed to install {pip_name}: {e}")
            print(f"  Try: pip install {pip_name}")
            sys.exit(1)
        else:
            print(f"  ⚠️  Could not install {pip_name} (optional, skipping)")
            return False

def auto_install():
    """Auto-install all required and optional dependencies."""
    print("\n" + "=" * 60)
    print("  🔧 Checking & installing dependencies...")
    print("=" * 60)
    
    # Required
    for mod, pkg in REQUIRED_PACKAGES.items():
        check_and_install(mod, pkg, required=True)
    
    # Optional
    for mod, pkg in OPTIONAL_PACKAGES.items():
        check_and_install(mod, pkg, required=False)
    
    print("=" * 60 + "\n")

# Now safe to import (they'll be installed first)
import requests
from bs4 import BeautifulSoup

# ──────────────────────────────────────────────────────────────────────────
# UI COLORS & HELPERS
# ──────────────────────────────────────────────────────────────────────────

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    CLEAR = '\033[2J\033[H'

def c(text, color):
    """Colorize text if terminal supports it."""
    try:
        return f"{color}{text}{Colors.END}"
    except:
        return text

def print_banner():
    """Print the tool banner."""
    os.system('clear' if os.name == 'posix' else 'cls')
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
  ╔══════════════════════════════════════════════════════════════╗
  ║                                                              ║
  ║     ██╗    ██╗██╗  ██╗███████╗██████╗  █████╗ ███╗   ███╗   ║
  ║     ██║    ██║██║  ██║██╔════╝██╔══██╗██╔══██╗████╗ ████║   ║
  ║     ██║ █╗ ██║███████║█████╗  ██████╔╝███████║██╔████╔██║   ║
  ║     ██║███╗██║╚════██║██╔══╝  ██╔══██╗██╔══██║██║╚██╔╝██║   ║
  ║     ╚███╔███╔╝     ██║███████╗██║  ██║██║  ██║██║ ╚═╝ ██║   ║
  ║      ╚══╝╚══╝      ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝   ║
  ║                                                              ║
  ║            {Colors.YELLOW}INTERACTIVE OSINT SCANNER v3.0{Colors.CYAN}              ║
  ║     Find where your email or phone is connected online       ║
  ║                                                              ║
  ╚══════════════════════════════════════════════════════════════╝{Colors.END}

  {Colors.GREEN}Authorized use only. Target your own assets first.{Colors.END}
"""
    print(banner)

def print_menu():
    """Print the main menu."""
    menu = f"""
{Colors.BOLD}{Colors.BLUE}  ┌─────────────────────────────────────────────────────────┐
  │                     MAIN MENU                        │
  ├─────────────────────────────────────────────────────────┤
  │                                                         │
  │  {Colors.GREEN}[1]{Colors.END}  Scan an Email Address                                │
  │  {Colors.GREEN}[2]{Colors.END}  Scan a Phone Number                                 │
  │  {Colors.GREEN}[3]{Colors.END}  Generate Google Dorks Only                           │
  │  {Colors.GREEN}[4]{Colors.END}  View Last Report                                     │
  │  {Colors.GREEN}[5]{Colors.END}  Settings & API Keys                                  │
  │  {Colors.GREEN}[6]{Colors.END}  About & Help                                         │
  │  {Colors.GREEN}[0]{Colors.END}  Exit                                                 │
  │                                                         │
  └─────────────────────────────────────────────────────────┘{Colors.END}
"""
    print(menu)

def print_box(title, content, color=Colors.BLUE):
    """Print content inside a colored box."""
    width = 70
    print(f"\n{color}  ┌─{'─' * (width - 4)}─┐{Colors.END}")
    print(f"{color}  │ {Colors.BOLD}{title:^66}{color} │{Colors.END}")
    print(f"{color}  ├─{'─' * (width - 4)}─┤{Colors.END}")
    for line in content.split('\n'):
        if len(line) > 64:
            # Wrap long lines
            while len(line) > 64:
                print(f"{color}  │ {Colors.END}{line[:64]:<64}{color} │{Colors.END}")
                line = line[64:]
        print(f"{color}  │ {Colors.END}{line:<64}{color} │{Colors.END}")
    print(f"{color}  └─{'─' * (width - 4)}─┘{Colors.END}\n")

def loading_animation(seconds, message="Scanning"):
    """Show a simple loading animation."""
    import itertools
    spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
    end_time = time.time() + seconds
    while time.time() < end_time:
        sys.stdout.write(f'\r  {next(spinner)} {message}... ')
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write(f'\r  ✅ {message} complete.     \n')

# ──────────────────────────────────────────────────────────────────────────
# CORE SCANNER ENGINE
# ──────────────────────────────────────────────────────────────────────────

class WhereAmIScanner:
    """Interactive scanner for email and phone OSINT."""
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/json,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    KNOWN_CARRIERS = {
        "verizon": ["verizon", "vtext", "vzw"],
        "tmobile": ["tmobile", "tmomail", "t-mobile"],
        "att": ["att", "att.net", "mms.att"],
        "sprint": ["sprint", "messaging.sprint"],
        "google_fi": ["google.fi", "msg.fi"],
        "visible": ["visible.com"],
        "mint": ["mintmobile"],
        "cricket": ["cricket"],
        "boost": ["boostmobile"],
        "metropcs": ["metropcs"],
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.results = {}
        self.config = self.load_config()
    
    def load_config(self):
        """Load configuration from file or return defaults."""
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "whereami_config.json")
        defaults = {
            "dehashed_key": "",
            "hibp_key": "",
            "emailrep_key": "",
            "timeout": 10,
            "save_reports": True,
            "show_passwords": False,
            "last_report": "",
        }
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    saved = json.load(f)
                    defaults.update(saved)
        except:
            pass
        return defaults
    
    def save_config(self):
        """Save current configuration."""
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "whereami_config.json")
        try:
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except:
            pass
    
    def identify_type(self, identifier):
        """Determine if input is email or phone."""
        identifier = identifier.strip()
        if re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', identifier):
            return "email"
        cleaned = re.sub(r'[\s\-\+\(\)\.]', '', identifier)
        if cleaned.startswith('+') and cleaned[1:].isdigit():
            return "phone"
        if cleaned.isdigit() and 7 <= len(cleaned) <= 15:
            return "phone"
        return "unknown"
    
    def normalize_phone(self, phone):
        return re.sub(r'[\s\-\+\(\)\.]', '', phone)
    
    def derive_usernames(self, email):
        """Derive potential usernames from email prefix."""
        local = email.split("@")[0].lower()
        usernames = {local}
        usernames.add(local.replace(".", ""))
        usernames.add(local.replace("_", ""))
        usernames.add(local.replace("-", ""))
        local_no_dots = local.replace(".", "")
        usernames.add(local_no_dots)
        if "+" in local:
            base = local.split("+")[0]
            usernames.add(base)
            usernames.add(base.replace(".", ""))
        for base in list(usernames)[:5]:
            usernames.add(base + "1")
            usernames.add("_" + base)
        return list(usernames)[:10]
    
    # ── MODULES ──
    
    def check_gravatar(self, email):
        """Check Gravatar for profile."""
        email_hash = hashlib.md5(email.lower().strip().encode()).hexdigest()
        try:
            r = self.session.get(
                f"https://www.gravatar.com/{email_hash}.json",
                timeout=self.config["timeout"]
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("entry"):
                    p = data["entry"][0]
                    return {
                        "found": True,
                        "display_name": p.get("displayName", "N/A"),
                        "username": p.get("preferredUsername", "N/A"),
                        "about": (p.get("aboutMe", "") or "")[:200],
                        "location": p.get("currentLocation", "N/A"),
                        "avatar": f"https://www.gravatar.com/avatar/{email_hash}?s=200",
                        "profile_url": f"https://www.gravatar.com/{email_hash}",
                    }
        except:
            pass
        return {"found": False}
    
    def check_github(self, email):
        """Search GitHub commits for email."""
        try:
            url = f"https://api.github.com/search/commits?q={urllib.parse.quote(email)}&sort=author-date&per_page=3"
            r = self.session.get(
                url,
                timeout=self.config["timeout"],
                headers={**self.HEADERS, "Accept": "application/vnd.github.cloak+json"}
            )
            if r.status_code == 200:
                data = r.json()
                if data["total_count"] > 0:
                    commits = []
                    for item in data["items"][:3]:
                        commits.append({
                            "repo": item["repository"]["full_name"],
                            "author": item["commit"]["author"]["name"],
                            "date": item["commit"]["author"]["date"][:10],
                            "url": f"https://github.com/{item['repository']['full_name']}/commit/{item['sha'][:7]}"
                        })
                    return {"found": True, "count": data["total_count"], "commits": commits}
        except:
            pass
        return {"found": False}
    
    def check_hibp(self, email):
        """Check HIBP with k-anonymity."""
        sha1 = hashlib.sha1(email.encode()).hexdigest().upper()
        prefix = sha1[:5]
        suffix = sha1[5:]
        try:
            r = self.session.get(
                f"https://api.pwnedpasswords.com/range/{prefix}",
                timeout=self.config["timeout"]
            )
            if r.status_code == 200:
                for line in r.text.splitlines():
                    if line.startswith(suffix):
                        count = int(line.split(":")[1].strip())
                        return {"found": True, "breach_count": count}
        except:
            pass
        return {"found": False}
    
    def check_pastebin(self, identifier):
        """Search paste sites."""
        encoded = urllib.parse.quote(identifier)
        try:
            r = self.session.get(
                f"https://psbdmp.ws/api/search/{encoded}",
                timeout=self.config["timeout"]
            )
            if r.status_code == 200:
                data = r.json()
                count = data.get("count", 0)
                if count > 0:
                    pastes = []
                    for d in data.get("data", [])[:5]:
                        pastes.append({
                            "id": d.get("id"),
                            "title": d.get("title", "Untitled"),
                            "url": f"https://pastebin.com/{d.get('id')}"
                        })
                    return {"found": True, "count": count, "pastes": pastes}
        except:
            pass
        return {"found": False}
    
    def check_phone_carrier(self, phone):
        """Detect phone carrier and line type."""
        normalized = self.normalize_phone(phone)
        result = {"carrier": "Unknown", "line_type": "Unknown", "country": "Unknown", "valid": False}
        
        # Try numverify
        try:
            r = self.session.get(
                f"http://apilayer.net/api/validate?number={normalized}&country_code=US&format=1",
                timeout=self.config["timeout"]
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("success"):
                    result["carrier"] = data.get("carrier", "Unknown")
                    result["line_type"] = data.get("line_type", "Unknown")
                    result["country"] = data.get("country_name", "Unknown")
                    result["location"] = data.get("location", "Unknown")
                    result["valid"] = data.get("valid", False)
        except:
            pass
        
        # If no carrier from API, try pattern matching on the number
        if result["carrier"] == "Unknown":
            # This is a simplified check — real carrier detection needs an API
            self.session.get(
                f"https://www.carrierlookup.com/lookup/{normalized}",
                timeout=self.config["timeout"]
            )
        
        return result
    
    def check_phone_social(self, phone):
        """Check phone on social platforms."""
        normalized = self.normalize_phone(phone)
        results = []
        platforms = [
            ("WhatsApp", f"https://wa.me/{normalized}"),
            ("Telegram", f"https://t.me/+{normalized}"),
            ("Truecaller", f"https://www.truecaller.com/search/us/{normalized}"),
        ]
        for name, url in platforms:
            try:
                r = self.session.get(url, timeout=self.config["timeout"], allow_redirects=True)
                if r.status_code != 404:
                    results.append({"platform": name, "url": url, "status": r.status_code})
            except:
                pass
        return results
    
    def check_whois(self, email):
        """Check WHOIS for email in domain records."""
        domain = email.split("@")[1]
        try:
            r = self.session.get(
                f"https://www.whois.com/whois/{domain}",
                timeout=self.config["timeout"]
            )
            if r.status_code == 200 and email.lower() in r.text.lower():
                return {"found": True, "domain": domain}
        except:
            pass
        return {"found": False}
    
    def scan_email(self, email):
        """Run all email modules."""
        print_box("SCANNING EMAIL", f"Target: {email}", Colors.CYAN)
        
        results = {
            "type": "email",
            "identifier": email,
            "timestamp": datetime.now().isoformat(),
            "gravatar": {},
            "github": {},
            "hibp": {},
            "pastebin": {},
            "whois": {},
            "usernames": [],
            "google_dorks": [],
            "holehe_results": [],
        }
        
        # Run checks
        print(f"\n  {Colors.YELLOW}[1/6]{Colors.END} Checking Gravatar...")
        results["gravatar"] = self.check_gravatar(email)
        if results["gravatar"].get("found"):
            print(f"    ✅ Profile found: {results['gravatar'].get('display_name', 'N/A')}")
        else:
            print(f"    ❌ No profile")
        
        print(f"\n  {Colors.YELLOW}[2/6]{Colors.END} Searching GitHub commits...")
        results["github"] = self.check_github(email)
        if results["github"].get("found"):
            print(f"    ✅ {results['github']['count']} commits found")
        else:
            print(f"    ❌ No commits found")
        
        print(f"\n  {Colors.YELLOW}[3/6]{Colors.END} Checking breach databases (HIBP)...")
        results["hibp"] = self.check_hibp(email)
        if results["hibp"].get("found"):
            print(f"    ⚠️  Password found in {results['hibp']['breach_count']} breaches!")
        else:
            print(f"    ✅ Password not found in breaches")
        
        print(f"\n  {Colors.YELLOW}[4/6]{Colors.END} Scanning paste sites...")
        results["pastebin"] = self.check_pastebin(email)
        if results["pastebin"].get("found"):
            print(f"    ⚠️  Found in {results['pastebin']['count']} pastes")
        else:
            print(f"    ✅ No pastes found")
        
        print(f"\n  {Colors.YELLOW}[5/6]{Colors.END} Checking WHOIS records...")
        results["whois"] = self.check_whois(email)
        if results["whois"].get("found"):
            print(f"    ✅ Email found in WHOIS for {results['whois']['domain']}")
        else:
            print(f"    ❌ Not found in WHOIS (privacy likely enabled)")
        
        print(f"\n  {Colors.YELLOW}[6/6]{Colors.END} Deriving usernames & generating dorks...")
        results["usernames"] = self.derive_usernames(email)
        
        # Generate Google dorks
        patterns = [
            f'"{email}"',
            f'"{email}" site:linkedin.com',
            f'"{email}" site:facebook.com',
            f'"{email}" site:github.com',
            f'"{email}" site:pastebin.com',
            f'"{email}" filetype:pdf',
        ]
        results["google_dorks"] = [
            {"query": p, "url": f"https://www.google.com/search?q={urllib.parse.quote(p)}"}
            for p in patterns
        ]
        
        # Try holehe if available
        try:
            import holehe
            print(f"\n  {Colors.YELLOW}[+]{Colors.END} Running holehe (120+ platform check)...")
            print(f"      This may take 30-60 seconds...")
            results["holehe_results"] = self.run_holehe(email)
        except ImportError:
            pass
        
        return results
    
    def run_holehe(self, email):
        """Run holehe module if available."""
        results = []
        try:
            from holehe.core import launch_module
            from holehe.modules_registered import get_modules
            modules = get_modules()
            found_count = 0
            for module in modules:
                try:
                    result = launch_module(module, email, self.session)
                    if result and result.get("exists"):
                        results.append({
                            "platform": module.__name__.split(".")[-1].replace("_", " ").title(),
                            "exists": True,
                        })
                        found_count += 1
                        # Print as we go (without overwhelming)
                        module_name = module.__name__.split(".")[-1].replace("_", " ").title()
                        if found_count <= 10:
                            print(f"      ✅ {module_name}")
                except:
                    continue
            print(f"      Total: {found_count} platforms found")
        except Exception as e:
            print(f"      ⚠️  holehe error: {e}")
        return results
    
    def scan_phone(self, phone):
        """Run all phone modules."""
        print_box("SCANNING PHONE", f"Target: {phone}", Colors.CYAN)
        
        results = {
            "type": "phone",
            "identifier": phone,
            "timestamp": datetime.now().isoformat(),
            "carrier_info": {},
            "social_platforms": [],
            "pastebin": {},
            "google_dorks": [],
        }
        
        normalized = self.normalize_phone(phone)
        
        print(f"\n  {Colors.YELLOW}[1/4]{Colors.END} Detecting carrier & line type...")
        results["carrier_info"] = self.check_phone_carrier(phone)
        ci = results["carrier_info"]
        print(f"    Carrier: {ci.get('carrier', 'Unknown')}")
        print(f"    Line Type: {ci.get('line_type', 'Unknown')}")
        print(f"    Country: {ci.get('country', 'Unknown')}")
        
        print(f"\n  {Colors.YELLOW}[2/4]{Colors.END} Checking social platforms...")
        results["social_platforms"] = self.check_phone_social(phone)
        for plat in results["social_platforms"]:
            print(f"    🔗 {plat['platform']}: {plat['url']}")
        if not results["social_platforms"]:
            print(f"    ❌ No platforms found")
        
        print(f"\n  {Colors.YELLOW}[3/4]{Colors.END} Scanning paste & leak sites...")
        results["pastebin"] = self.check_pastebin(normalized)
        if results["pastebin"].get("found"):
            print(f"    ⚠️  Found in {results['pastebin']['count']} pastes")
        else:
            print(f"    ✅ No pastes found")
        
        print(f"\n  {Colors.YELLOW}[4/4]{Colors.END} Generating Google dorks...")
        patterns = [
            f'"{normalized}"',
            f'"+{normalized}"',
            f'"{normalized}" site:facebook.com',
            f'"{normalized}" site:whitepages.com',
            f'"{normalized}" site:truecaller.com',
        ]
        results["google_dorks"] = [
            {"query": p, "url": f"https://www.google.com/search?q={urllib.parse.quote(p)}"}
            for p in patterns
        ]
        
        return results
    
    def display_results_email(self, results):
        """Display email scan results."""
        print(f"\n{Colors.BOLD}{Colors.GREEN}  ═══════════════════════════════════════════════════{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}   📋 SCAN RESULTS — {results['identifier']}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}  ═══════════════════════════════════════════════════{Colors.END}\n")
        
        # Summary bar
        hits = []
        if results["gravatar"].get("found"): hits.append("Gravatar")
        if results["github"].get("found"): hits.append("GitHub")
        if results["hibp"].get("found"): hits.append("Breaches")
        if results["pastebin"].get("found"): hits.append("Leaks")
        if results["whois"].get("found"): hits.append("WHOIS")
        if results.get("holehe_results"): hits.append(f"{len(results['holehe_results'])} Platforms")
        
        print(f"  {Colors.BOLD}Summary:{Colors.END} {len(hits)} data sources found")
        if hits:
            print(f"  {Colors.BOLD}Found in:{Colors.END} {', '.join(hits)}")
        print()
        
        # Gravatar
        if results["gravatar"].get("found"):
            g = results["gravatar"]
            print(f"  {Colors.CYAN}📸 Gravatar Profile{Colors.END}")
            print(f"     Name: {g.get('display_name', 'N/A')}")
            print(f"     Username: {g.get('username', 'N/A')}")
            if g.get("about"):
                print(f"     About: {g['about'][:150]}")
            if g.get("location"):
                print(f"     Location: {g['location']}")
            print(f"     Avatar: {g.get('avatar', 'N/A')}")
            print(f"     Profile: {g.get('profile_url', 'N/A')}")
            print()
        
        # GitHub
        if results["github"].get("found"):
            g = results["github"]
            print(f"  {Colors.CYAN}💻 GitHub Commits ({g['count']} total){Colors.END}")
            for commit in g["commits"]:
                print(f"     ├─ {commit['repo']} ({commit['date']})")
                print(f"     └─ {commit['url']}")
            print()
        
        # Breaches
        if results["hibp"].get("found"):
            print(f"  {Colors.RED}🔓 BREACH ALERT{Colors.END}")
            print(f"     Password appears in {results['hibp']['breach_count']} known breaches!")
            print(f"     Change this password immediately if still in use.")
            print()
        
        # Pastebin
        if results["pastebin"].get("found"):
            p = results["pastebin"]
            print(f"  {Colors.YELLOW}📋 Pastebin/Leak Mentions ({p['count']} total){Colors.END}")
            for paste in p["pastes"]:
                print(f"     ├─ {paste.get('title', 'Untitled')}")
                print(f"     └─ {paste['url']}")
            print()
        
        # WHOIS
        if results["whois"].get("found"):
            print(f"  {Colors.CYAN}🌐 WHOIS Record{Colors.END}")
            print(f"     Email found in WHOIS for domain: {results['whois']['domain']}")
            print()
        
        # Holehe results
        if results.get("holehe_results"):
            print(f"  {Colors.GREEN}📱 Platform Accounts Found ({len(results['holehe_results'])}){Colors.END}")
            # Show in columns
            platforms = [h["platform"] for h in results["holehe_results"]]
            # Display in rows of 4
            for i in range(0, len(platforms), 4):
                row = platforms[i:i+4]
                print(f"     {'  |  '.join(f'{p:<20}' for p in row)}")
            print(f"     Total: {len(platforms)} platforms where account exists")
            print()
        
        # Usernames
        if results.get("usernames"):
            print(f"  {Colors.CYAN}🔑 Derived Usernames{Colors.END}")
            print(f"     {', '.join(results['usernames'])}")
            print()
        
        # Google dorks
        if results.get("google_dorks"):
            print(f"  {Colors.YELLOW}🔍 Google Dorks (click to search){Colors.END}")
            for dork in results["google_dorks"][:5]:
                print(f"     • {dork['query']}")
            print()
    
    def display_results_phone(self, results):
        """Display phone scan results."""
        print(f"\n{Colors.BOLD}{Colors.GREEN}  ═══════════════════════════════════════════════════{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}   📋 SCAN RESULTS — {results['identifier']}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}  ═══════════════════════════════════════════════════{Colors.END}\n")
        
        # Carrier info
        ci = results["carrier_info"]
        print(f"  {Colors.CYAN}📱 Phone Intelligence{Colors.END}")
        print(f"     Valid: {'✅' if ci.get('valid') else '❌'} ")
        print(f"     Carrier: {ci.get('carrier', 'Unknown')}")
        print(f"     Line Type: {ci.get('line_type', 'Unknown')}")
        print(f"     Country: {ci.get('country', 'Unknown')}")
        if ci.get("location"):
            print(f"     Location: {ci['location']}")
        print()
        
        # Social platforms
        if results["social_platforms"]:
            print(f"  {Colors.CYAN}🔗 Social Platform Links{Colors.END}")
            for plat in results["social_platforms"]:
                print(f"     • {plat['platform']}: {plat['url']}")
            print()
        
        # Pastebin
        if results["pastebin"].get("found"):
            p = results["pastebin"]
            print(f"  {Colors.YELLOW}📋 Leak Mentions ({p['count']} total){Colors.END}")
            for paste in p["pastes"]:
                print(f"     ├─ {paste.get('title', 'Untitled')}")
                print(f"     └─ {paste['url']}")
            print()
        
        # Google dorks
        if results.get("google_dorks"):
            print(f"  {Colors.YELLOW}🔍 Google Dorks (click to search){Colors.END}")
            for dork in results["google_dorks"]:
                print(f"     • {dork['query']}")
            print()
    
    def save_report(self, results):
        """Save results to JSON file."""
        if not self.config["save_reports"]:
            return None
        
        identifier = results["identifier"]
        safe_id = identifier.replace("@", "_at_").replace("+", "plus_").replace(".", "_")
        filename = f"whereami_{safe_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            self.config["last_report"] = os.path.abspath(filename)
            self.save_config()
            return filename
        except:
            return None

# ──────────────────────────────────────────────────────────────────────────
# MAIN INTERACTIVE LOOP
# ──────────────────────────────────────────────────────────────────────────

def interactive_menu():
    """Main interactive menu loop."""
    scanner = WhereAmIScanner()
    
    while True:
        print_banner()
        print_menu()
        
        choice = input(f"  {Colors.GREEN}Select option [0-6]:{Colors.END} ").strip()
        
        if choice == "1":
            # Scan email
            print_banner()
            print_box("EMAIL SCAN", "Enter the email address to scan", Colors.CYAN)
            email = input(f"\n  {Colors.GREEN}Email:{Colors.END} ").strip()
            
            if not email or "@" not in email:
                print(f"\n  {Colors.RED}❌ Invalid email address.{Colors.END}")
                input(f"\n  Press Enter to continue...")
                continue
            
            results = scanner.scan_email(email)
            
            # Save report
            filename = scanner.save_report(results)
            
            # Display results
            scanner.display_results_email(results)
            
            if filename:
                print(f"\n  {Colors.GREEN}💾 Report saved: {filename}{Colors.END}")
            
            input(f"\n  Press Enter to return to menu...")
        
        elif choice == "2":
            # Scan phone
            print_banner()
            print_box("PHONE SCAN", "Enter the phone number to scan (E.164 format: +14155551234)", Colors.CYAN)
            phone = input(f"\n  {Colors.GREEN}Phone:{Colors.END} ").strip()
            
            if not phone:
                print(f"\n  {Colors.RED}❌ Invalid phone number.{Colors.END}")
                input(f"\n  Press Enter to continue...")
                continue
            
            results = scanner.scan_phone(phone)
            
            # Save report
            filename = scanner.save_report(results)
            
            # Display results
            scanner.display_results_phone(results)
            
            if filename:
                print(f"\n  {Colors.GREEN}💾 Report saved: {filename}{Colors.END}")
            
            input(f"\n  Press Enter to return to menu...")
        
        elif choice == "3":
            # Generate Google dorks only
            print_banner()
            print_box("GOOGLE DORKS", "Generate search queries for manual research", Colors.CYAN)
            target = input(f"\n  {Colors.GREEN}Enter email or phone:{Colors.END} ").strip()
            
            if not target:
                continue
            
            id_type = scanner.identify_type(target)
            print(f"\n  {Colors.YELLOW}🔍 Google Dorks for: {target}{Colors.END}\n")
            
            if id_type == "email":
                patterns = [
                    f'"{target}"',
                    f'"{target}" site:linkedin.com',
                    f'"{target}" site:facebook.com',
                    f'"{target}" site:github.com',
                    f'"{target}" site:pastebin.com',
                    f'"{target}" "password" OR "credentials"',
                    f'"{target}" filetype:pdf OR filetype:csv',
                    f'"{target}" "username" OR "login"',
                ]
            else:
                normalized = re.sub(r'[\s\-\+\(\)\.]', '', target)
                patterns = [
                    f'"{normalized}"',
                    f'"+{normalized}"',
                    f'"{normalized}" site:facebook.com',
                    f'"{normalized}" site:whitepages.com',
                    f'"{normalized}" site:truecaller.com',
                    f'"{normalized}" filetype:pdf',
                ]
            
            for p in patterns:
                url = f"https://www.google.com/search?q={urllib.parse.quote(p)}"
                print(f"  • {p}")
                print(f"    {url}\n")
            
            input(f"\n  Press Enter to return to menu...")
        
        elif choice == "4":
            # View last report
            last = scanner.config.get("last_report", "")
            if last and os.path.exists(last):
                print_banner()
                print_box("LAST REPORT", f"File: {last}", Colors.CYAN)
                try:
                    with open(last, 'r') as f:
                        data = json.load(f)
                    
                    if data.get("type") == "email":
                        scanner.display_results_email(data)
                    else:
                        scanner.display_results_phone(data)
                except:
                    print(f"\n  {Colors.RED}❌ Could not read report file.{Colors.END}")
            else:
                print(f"\n  {Colors.YELLOW}⚠️  No previous report found.{Colors.END}")
            
            input(f"\n  Press Enter to return to menu...")
        
        elif choice == "5":
            # Settings
            print_banner()
            print_box("SETTINGS", "Configure API keys and options", Colors.YELLOW)
            
            print(f"  {Colors.CYAN}Current Settings:{Colors.END}\n")
            print(f"    DeHashed API Key: {'✅ Set' if scanner.config.get('dehashed_key') else '❌ Not set'}")
            print(f"    HIBP API Key:     {'✅ Set' if scanner.config.get('hibp_key') else '❌ Not set'}")
            print(f"    EmailRep API Key: {'✅ Set' if scanner.config.get('emailrep_key') else '❌ Not set'}")
            print(f"    Timeout:          {scanner.config.get('timeout', 10)}s")
            print(f"    Save Reports:     {'✅' if scanner.config.get('save_reports', True) else '❌'}")
            
            print(f"\n  {Colors.YELLOW}Options:{Colors.END}")
            print(f"    [1] Set DeHashed API Key")
            print(f"    [2] Set HIBP API Key")
            print(f"    [3] Set EmailRep API Key")
            print(f"    [4] Toggle Save Reports")
            print(f"    [5] Change Timeout")
            print(f"    [0] Back")
            
            sub_choice = input(f"\n  {Colors.GREEN}Select:{Colors.END} ").strip()
            
            if sub_choice == "1":
                key = input("  Enter DeHashed API Key: ").strip()
                scanner.config["dehashed_key"] = key
                scanner.save_config()
                print(f"  ✅ Key saved")
            elif sub_choice == "2":
                key = input("  Enter HIBP API Key: ").strip()
                scanner.config["hibp_key"] = key
                scanner.save_config()
                print(f"  ✅ Key saved")
            elif sub_choice == "3":
                key = input("  Enter EmailRep API Key: ").strip()
                scanner.config["emailrep_key"] = key
                scanner.save_config()
                print(f"  ✅ Key saved")
            elif sub_choice == "4":
                scanner.config["save_reports"] = not scanner.config.get("save_reports", True)
                scanner.save_config()
                print(f"  ✅ Save Reports: {scanner.config['save_reports']}")
            elif sub_choice == "5":
                try:
                    t = int(input("  Timeout in seconds (5-30): ").strip())
                    if 5 <= t <= 30:
                        scanner.config["timeout"] = t
                        scanner.save_config()
                        print(f"  ✅ Timeout set to {t}s")
                except:
                    print(f"  ❌ Invalid value")
            
            if sub_choice not in ["0", ""]:
                input(f"\n  Press Enter to continue...")
        
        elif choice == "6":
            # Help
            print_banner()
            help_text = f"""
{Colors.BOLD}WHERE AM I? v3.0 — Interactive OSINT Scanner{Colors.END}

{Colors.CYAN}What it does:{Colors.END}
  Scans email addresses and phone numbers to find where they're
  registered online, leaked in breaches, or publicly exposed.

{Colors.CYAN}Features:{Colors.END}
  • Gravatar profile lookup
  • GitHub commit search
  • Have I Been Pwned breach check (no API key needed)
  • Pastebin & leak site scanning
  • WHOIS record checking
  • 120+ platform registration check (via holehe)
  • Phone carrier & line type detection
  • WhatsApp, Telegram, Truecaller check
  • Google dork generation
  • Derived username generation

{Colors.CYAN}Tips:{Colors.END}
  • For best results with email, run: pip install holehe
  • For phone scanning, use E.164 format: +14155551234
  • Install API keys in Settings for premium data
  • Reports are saved as JSON files automatically

{Colors.YELLOW}⚠️  Authorized use only. Only scan your own assets or
   targets you have explicit permission to test.{Colors.END}
"""
            print(help_text)
            input(f"\n  Press Enter to return to menu...")
        
        elif choice == "0":
            print(f"\n  {Colors.GREEN}Goodbye! Stay safe.{Colors.END}\n")
            sys.exit(0)
        
        else:
            print(f"\n  {Colors.RED}❌ Invalid option. Please try again.{Colors.END}")
            time.sleep(1)


# ──────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Step 1: Auto-install dependencies
    auto_install()
    
    # Step 2: Handle optional arguments for direct CLI usage
    if len(sys.argv) > 1:
        # CLI mode for scripting
        if "-e" in sys.argv:
            idx = sys.argv.index("-e") + 1
            if idx < len(sys.argv):
                email = sys.argv[idx]
                scanner = WhereAmIScanner()
                results = scanner.scan_email(email)
                scanner.save_report(results)
                scanner.display_results_email(results)
                sys.exit(0)
        elif "-p" in sys.argv:
            idx = sys.argv.index("-p") + 1
            if idx < len(sys.argv):
                phone = sys.argv[idx]
                scanner = WhereAmIScanner()
                results = scanner.scan_phone(phone)
                scanner.save_report(results)
                scanner.display_results_phone(results)
                sys.exit(0)
        elif "--help" in sys.argv or "-h" in sys.argv:
            print("""
Usage: python whereami.py           # Interactive mode
       python whereami.py -e email  # Direct email scan
       python whereami.py -p phone  # Direct phone scan
       python whereami.py --help    # This help
            """)
            sys.exit(0)
    
    # Step 3: Launch interactive menu
    try:
        interactive_menu()
    except KeyboardInterrupt:
        print(f"\n\n  {Colors.YELLOW}Interrupted. Exiting...{Colors.END}\n")
        sys.exit(0)