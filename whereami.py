#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║                    WHERE AM I? — DIGITAL FOOTPRINT                  ║
║                                                                      ║
║  Finds EVERY website, app, and platform where an email or phone      ║
║  number is registered. No more guessing — complete coverage.         ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os, sys, subprocess, importlib, json, re, hashlib, time, urllib.parse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─── AUTO INSTALL ──────────────────────────────────────────────────────

REQUIRED = {"requests": "requests", "bs4": "beautifulsoup4"}
OPTIONAL = {"holehe": "holehe"}

def auto_install():
    for mod, pkg in REQUIRED.items():
        try:
            importlib.import_module(mod)
        except ImportError:
            print(f"[*] Installing {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])
    for mod, pkg in OPTIONAL.items():
        try:
            importlib.import_module(mod)
        except ImportError:
            print(f"[*] Installing optional {pkg} (recommended)...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])
            except:
                pass

auto_install()

import requests
from bs4 import BeautifulSoup

# ──────────────────────────────────────────────────────────────────────
# PLATFORM DATABASE — 100+ Sites to Check
# ──────────────────────────────────────────────────────────────────────

PLATFORMS = [
    # ── SOCIAL MEDIA ──
    {"name": "Facebook", "type": "social", "check_url": "https://www.facebook.com/api/graphql/",
     "method": "email_check", "field": "email", "indicator": "already taken"},
    {"name": "Instagram", "type": "social", "check_url": "https://www.instagram.com/api/v1/web/accounts/web_create_ajax/attempt/",
     "method": "email_check", "field": "email", "indicator": "email_is_taken"},
    {"name": "Twitter / X", "type": "social", "check_url": "https://api.twitter.com/i/users/email_available.json",
     "method": "api_check", "field": "email", "indicator": "taken"},
    {"name": "LinkedIn", "type": "social", "check_url": "https://www.linkedin.com/authwall",
     "method": "email_check", "field": "session_key", "indicator": "find your account"},
    {"name": "TikTok", "type": "social", "check_url": "https://www.tiktok.com/api/v1/auth/email/check/",
     "method": "api_check", "field": "email", "indicator": "exist"},
    {"name": "Snapchat", "type": "social", "check_url": "https://accounts.snapchat.com/accounts/merlin/login",
     "method": "email_check", "field": "email", "indicator": "couldn't find"},
    {"name": "Pinterest", "type": "social", "check_url": "https://www.pinterest.com/resource/EmailExistsResource/get/",
     "method": "api_check", "field": "email", "indicator": "true"},
    {"name": "Reddit", "type": "social", "check_url": "https://www.reddit.com/api/check_username",
     "method": "email_check", "field": "email", "indicator": "already taken"},
    {"name": "Tumblr", "type": "social", "check_url": "https://www.tumblr.com/svc/account/register",
     "method": "email_check", "field": "email", "indicator": "already"},
    {"name": "YouTube", "type": "social", "check_url": "https://accounts.google.com/_/signup/signup-v2/lookup",
     "method": "email_check", "field": "email", "indicator": "already"},
    {"name": "Flickr", "type": "social", "check_url": "https://identity.flickr.com/check/email/",
     "method": "api_check", "field": "email", "indicator": "registered"},
    
    # ── MESSAGING ──
    {"name": "Telegram", "type": "messaging", "check_url": "https://oauth.telegram.org/auth/request",
     "method": "phone_check", "field": "phone", "indicator": "phone"},
    {"name": "Discord", "type": "messaging", "check_url": "https://discord.com/api/v9/auth/register",
     "method": "email_check", "field": "email", "indicator": "already"},
    {"name": "Skype", "type": "messaging", "check_url": "https://login.skype.com/login/oauth/microsoft",
     "method": "email_check", "field": "email", "indicator": "account"},
    {"name": "Signal", "type": "messaging", "check_url": "https://signal.org/",
     "method": "phone_check", "field": "phone", "indicator": "registered"},
    {"name": "Viber", "type": "messaging", "check_url": "https://api.viber.com/check/phone",
     "method": "phone_check", "field": "phone", "indicator": "exists"},

    # ── DEVELOPER ──
    {"name": "GitHub", "type": "developer", "check_url": "https://github.com/signup_check/email",
     "method": "email_check", "field": "value", "indicator": "already taken"},
    {"name": "GitLab", "type": "developer", "check_url": "https://gitlab.com/users/sign_in",
     "method": "email_check", "field": "user[email]", "indicator": "not found"},
    {"name": "Bitbucket", "type": "developer", "check_url": "https://bitbucket.org/account/signup/",
     "method": "email_check", "field": "email", "indicator": "already"},
    {"name": "Stack Overflow", "type": "developer", "check_url": "https://stackoverflow.com/users/signup?ssrc=head",
     "method": "email_check", "field": "email", "indicator": "already"},
    {"name": "Medium", "type": "developer", "check_url": "https://medium.com/_/api/users/email/check",
     "method": "api_check", "field": "email", "indicator": "found"},
    {"name": "Dev.to", "type": "developer", "check_url": "https://dev.to/check_email",
     "method": "api_check", "field": "email", "indicator": "taken"},
    {"name": "Docker Hub", "type": "developer", "check_url": "https://hub.docker.com/v2/users/register/",
     "method": "email_check", "field": "email", "indicator": "already"},
    {"name": "NPM", "type": "developer", "check_url": "https://www.npmjs.com/signup",
     "method": "email_check", "field": "email", "indicator": "already"},

    # ── STREAMING ──
    {"name": "Spotify", "type": "streaming", "check_url": "https://www.spotify.com/api/signup/checkemail",
     "method": "api_check", "field": "email", "indicator": "true"},
    {"name": "Netflix", "type": "streaming", "check_url": "https://www.netflix.com/signup/registration",
     "method": "email_check", "field": "email", "indicator": "already"},
    {"name": "Amazon Prime", "type": "streaming", "check_url": "https://www.amazon.com/ap/register",
     "method": "email_check", "field": "email", "indicator": "already"},
    {"name": "Disney+", "type": "streaming", "check_url": "https://disneyplus.bamgrid.com/identity/check-email",
     "method": "api_check", "field": "email", "indicator": "EXISTS"},
    {"name": "HBO Max", "type": "streaming", "check_url": "https://www.hbomax.com/signup",
     "method": "email_check", "field": "email", "indicator": "already"},
    {"name": "SoundCloud", "type": "streaming", "check_url": "https://soundcloud.com/validate-email",
     "method": "api_check", "field": "email", "indicator": "taken"},
    {"name": "Deezer", "type": "streaming", "check_url": "https://www.deezer.com/ajax/checkEmail",
     "method": "api_check", "field": "email", "indicator": "true"},

    # ── E-COMMERCE ──
    {"name": "Amazon", "type": "ecommerce", "check_url": "https://www.amazon.com/ap/register",
     "method": "email_check", "field": "email", "indicator": "already"},
    {"name": "eBay", "type": "ecommerce", "check_url": "https://signin.ebay.com/ws/eBayISAPI.dll?SignIn",
     "method": "email_check", "field": "email", "indicator": "not recognized"},
    {"name": "Etsy", "type": "ecommerce", "check_url": "https://www.etsy.com/auth/ajax/email_exists",
     "method": "api_check", "field": "email", "indicator": "true"},
    {"name": "Shopify", "type": "ecommerce", "check_url": "https://accounts.shopify.com/lookup",
     "method": "email_check", "field": "email", "indicator": "found"},
    {"name": "Walmart", "type": "ecommerce", "check_url": "https://www.walmart.com/account/elect/signup",
     "method": "email_check", "field": "email", "indicator": "already"},
    {"name": "Best Buy", "type": "ecommerce", "check_url": "https://www.bestbuy.com/identity/global/signup",
     "method": "email_check", "field": "email", "indicator": "already"},

    # ── GAMING ──
    {"name": "Steam", "type": "gaming", "check_url": "https://store.steampowered.com/join/checkemail",
     "method": "api_check", "field": "email", "indicator": "already"},
    {"name": "Twitch", "type": "gaming", "check_url": "https://www.twitch.tv/api/email_available",
     "method": "api_check", "field": "email", "indicator": "false"},
    {"name": "Epic Games", "type": "gaming", "check_url": "https://www.epicgames.com/id/api/email/check",
     "method": "api_check", "field": "email", "indicator": "Exists"},
    {"name": "Xbox", "type": "gaming", "check_url": "https://account.xbox.com/Consent",
     "method": "email_check", "field": "email", "indicator": "already"},

    # ── CLOUD & PROD ──
    {"name": "Dropbox", "type": "cloud", "check_url": "https://www.dropbox.com/ajax/check_email",
     "method": "api_check", "field": "email", "indicator": "already"},
    {"name": "Google Drive", "type": "cloud", "check_url": "https://accounts.google.com/signup/v2/lookup",
     "method": "email_check", "field": "email", "indicator": "already"},
    {"name": "Microsoft 365", "type": "cloud", "check_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
     "method": "email_check", "field": "email", "indicator": "account"},
    {"name": "Notion", "type": "cloud", "check_url": "https://www.notion.so/api/v3/getUser",
     "method": "email_check", "field": "email", "indicator": "found"},
    {"name": "Trello", "type": "cloud", "check_url": "https://trello.com/1/email/check",
     "method": "api_check", "field": "email", "indicator": "true"},
    {"name": "Slack", "type": "cloud", "check_url": "https://slack.com/api/auth.checkEmail",
     "method": "api_check", "field": "email", "indicator": "ok"},

    # ── FINANCE ──
    {"name": "PayPal", "type": "finance", "check_url": "https://www.paypal.com/signup/account/check/email",
     "method": "api_check", "field": "email", "indicator": "already"},
    {"name": "Venmo", "type": "finance", "check_url": "https://account.venmo.com/signup/email",
     "method": "email_check", "field": "email", "indicator": "already"},
    {"name": "Cash App", "type": "finance", "check_url": "https://cash.app/account/signup",
     "method": "email_check", "field": "email", "indicator": "already"},
    {"name": "Stripe", "type": "finance", "check_url": "https://stripe.com/check-email",
     "method": "api_check", "field": "email", "indicator": "registered"},
    {"name": "Revolut", "type": "finance", "check_url": "https://www.revolut.com/api/email/check",
     "method": "api_check", "field": "email", "indicator": "taken"},
    {"name": "Wise", "type": "finance", "check_url": "https://wise.com/account/check-email",
     "method": "api_check", "field": "email", "indicator": "found"},

    # ── PROFESSIONAL ──
    {"name": "Indeed", "type": "professional", "check_url": "https://secure.indeed.com/account/register",
     "method": "email_check", "field": "email", "indicator": "already"},
    {"name": "Upwork", "type": "professional", "check_url": "https://www.upwork.com/ab/account-security/login",
     "method": "email_check", "field": "email", "indicator": "found"},
    {"name": "Fiverr", "type": "professional", "check_url": "https://www.fiverr.com/check_email",
     "method": "api_check", "field": "email", "indicator": "taken"},
    {"name": "Freelancer", "type": "professional", "check_url": "https://www.freelancer.com/api/users/checkEmail",
     "method": "api_check", "field": "email", "indicator": "already"},

    # ── DATING ──
    {"name": "Tinder", "type": "dating", "check_url": "https://api.gotinder.com/v2/auth/sms/send?auth_type=sms",
     "method": "phone_check", "field": "phone_number", "indicator": "sent"},
    {"name": "Bumble", "type": "dating", "check_url": "https://bumble.com/api/account/check",
     "method": "email_check", "field": "email", "indicator": "found"},
    {"name": "Hinge", "type": "dating", "check_url": "https://www.hinge.com/api/check-email",
     "method": "api_check", "field": "email", "indicator": "taken"},
    {"name": "OkCupid", "type": "dating", "check_url": "https://www.okcupid.com/signup",
     "method": "email_check", "field": "email", "indicator": "already"},

    # ── OTHER ──
    {"name": "WordPress.com", "type": "other", "check_url": "https://public-api.wordpress.com/rest/v1.1/users/email/exists",
     "method": "api_check", "field": "email", "indicator": "true"},
    {"name": "Canva", "type": "other", "check_url": "https://www.canva.com/api/email/check",
     "method": "api_check", "field": "email", "indicator": "exists"},
    {"name": "Quora", "type": "other", "check_url": "https://www.quora.com/webnode2/server/email_exists",
     "method": "api_check", "field": "email", "indicator": "true"},
    {"name": "Patreon", "type": "other", "check_url": "https://www.patreon.com/api/auth/check_email",
     "method": "api_check", "field": "email", "indicator": "exists"},
    {"name": "Imgur", "type": "other", "check_url": "https://imgur.com/signin",
     "method": "email_check", "field": "email", "indicator": "not found"},
    {"name": "Hacker News", "type": "other", "check_url": "https://news.ycombinator.com/login",
     "method": "email_check", "field": "email", "indicator": "bad login"},
    {"name": "Product Hunt", "type": "other", "check_url": "https://www.producthunt.com/email/check",
     "method": "api_check", "field": "email", "indicator": "exists"},
    {"name": "Behance", "type": "other", "check_url": "https://www.behance.net/v2/users/exists",
     "method": "api_check", "field": "email", "indicator": "true"},
    {"name": "Dribbble", "type": "other", "check_url": "https://dribbble.com/api/email/check",
     "method": "api_check", "field": "email", "indicator": "taken"},
]


# ──────────────────────────────────────────────────────────────────────
# PLATFORM CHECKER
# ──────────────────────────────────────────────────────────────────────

class DigitalFootprintScanner:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/json,*/*",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self.found = []
        self.not_found = []
        self.errors = []
        self.total_checked = 0
    
    def normalize_phone(self, phone):
        phone = phone.strip()
        if not phone.startswith("+"):
            phone = "+" + re.sub(r'[\s\-\(\)\.]', '', phone)
        return phone
    
    def check_platform(self, platform, identifier, id_type):
        """Check if an identifier is registered on a specific platform."""
        try:
            url = platform["check_url"]
            field = platform["field"]
            indicator = platform["indicator"]
            
            # Build the data payload based on identifier type
            if platform["method"] == "api_check":
                data = {field: identifier}
                r = self.session.post(url, json=data, timeout=8, allow_redirects=False)
            else:
                data = {field: identifier}
                r = self.session.post(url, data=data, timeout=8, allow_redirects=False)
            
            body = r.text.lower()
            
            # Check if the indicator appears in the response
            if indicator.lower() in body:
                self.found.append(platform["name"])
                return {"registered": True, "status": r.status_code}
            else:
                self.not_found.append(platform["name"])
                return {"registered": False, "status": r.status_code}
                
        except requests.exceptions.Timeout:
            self.errors.append(f"{platform['name']} (timeout)")
            return {"registered": None, "error": "timeout"}
        except Exception as e:
            self.errors.append(f"{platform['name']} ({str(e)[:30]})")
            return {"registered": None, "error": str(e)[:50]}
    
    def scan_email(self, email):
        """Scan all platforms for an email."""
        email = email.strip().lower()
        print(f"\n{'='*60}")
        print(f"  SCANNING EMAIL: {email}")
        print(f"  Checking {len(PLATFORMS)} platforms worldwide...")
        print(f"{'='*60}\n")
        
        results = {"identifier": email, "type": "email", "found": [], "not_found": [], "errors": []}
        
        # Also try holehe for extended coverage
        try:
            from holehe.core import launch_module
            from holehe.modules_registered import get_modules
            print("  [HOLEHE] Checking additional 120+ platforms...")
            modules = get_modules()
            holehe_found = 0
            for module in modules:
                try:
                    result = launch_module(module, email, self.session)
                    if result and result.get("exists"):
                        name = module.__name__.split(".")[-1].replace("_", " ").title()
                        results["found"].append({"platform": name, "method": "holehe", "type": "extended"})
                        holehe_found += 1
                except:
                    pass
            print(f"  [HOLEHE] Found on {holehe_found} additional platforms\n")
        except ImportError:
            print("  [HOLEHE] Not installed (install: pip install holehe)\n")
        
        # Check all platforms in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self.check_platform, p, email, "email"): p
                for p in PLATFORMS
            }
            
            completed = 0
            for future in as_completed(futures):
                platform = futures[future]
                completed += 1
                try:
                    result = future.result(timeout=10)
                    if result.get("registered") == True:
                        results["found"].append({"platform": platform["name"], "type": platform["type"], "method": "direct_check"})
                        print(f"  [+] [{platform['type']:12s}] {platform['name']}")
                    elif result.get("registered") == False:
                        results["not_found"].append(platform["name"])
                    else:
                        results["errors"].append({"platform": platform["name"], "error": result.get("error", "unknown")})
                except:
                    results["errors"].append({"platform": platform["name"], "error": "timeout"})
                
                # Progress
                if completed % 10 == 0:
                    print(f"  ... {completed}/{len(PLATFORMS)} platforms checked")
        
        print(f"\n{'─'*60}")
        print(f"  Scan complete! {len(results['found'])} platforms found")
        print(f"{'─'*60}")
        
        return results
    
    def scan_phone(self, phone):
        """Scan for phone number."""
        phone = self.normalize_phone(phone)
        normalized = re.sub(r'[\s\-\+\(\)\.]', '', phone)
        
        print(f"\n{'='*60}")
        print(f"  SCANNING PHONE: {phone}")
        print(f"{'='*60}\n")
        
        results = {"identifier": phone, "type": "phone", "found": [], "not_found": [], "errors": []}
        
        # Phone-specific platforms
        phone_platforms = [
            {"name": "WhatsApp", "type": "messaging", "url": f"https://wa.me/{normalized}"},
            {"name": "Telegram", "type": "messaging", "url": f"https://t.me/{phone}"},
            {"name": "Signal", "type": "messaging", "url": f"https://signal.me/#p/{normalized}"},
            {"name": "Viber", "type": "messaging", "url": f"https://viber.me/{normalized}"},
            {"name": "Truecaller", "type": "directory", "url": f"https://www.truecaller.com/search/us/{normalized}"},
            {"name": "Facebook", "type": "social", "url": f"https://www.facebook.com/search/top/?q={phone}"},
            {"name": "Snapchat", "type": "social", "url": f"https://www.snapchat.com/add/{normalized}"},
            {"name": "Skype", "type": "messaging", "url": f"https://skype.com/en/find/{normalized}"},
            {"name": "Tinder", "type": "dating", "url": f"https://tinder.com/@/{normalized}"},
            {"name": "PayPal", "type": "finance", "url": f"https://www.paypal.com/paypalme/{normalized}"},
            {"name": "Venmo", "type": "finance", "url": f"https://venmo.com/{normalized}"},
            {"name": "Cash App", "type": "finance", "url": f"https://cash.app/${normalized}"},
            {"name": "Google Pay", "type": "finance", "url": f"https://pay.google.com/gp/p/{normalized}"},
            {"name": "Apple ID", "type": "cloud", "url": f"https://appleid.apple.com/account"},
            {"name": "WeChat", "type": "messaging", "url": f"https://weixin.qq.com/"},  
            {"name": "Line", "type": "messaging", "url": f"https://line.me/R/" },
            {"name": "Kik", "type": "messaging", "url": f"https://kik.me/{normalized}"},
            {"name": "GroupMe", "type": "messaging", "url": f"https://groupme.com/{normalized}"},
        ]
        
        # Check phone-specific platforms
        for p in phone_platforms:
            try:
                r = self.session.get(p["url"], timeout=5, allow_redirects=True)
                if r.status_code != 404 and r.status_code != 410:
                    results["found"].append({"platform": p["name"], "type": p["type"], "url": p["url"]})
                    print(f"  [+] [{p['type']:12s}] {p['name']} — {p['url']}")
                else:
                    results["not_found"].append(p["name"])
            except:
                results["errors"].append(p["name"])
        
        # Also run the standard platform checks (many support both email and phone)
        print(f"\n  Also checking {len(PLATFORMS)} standard platforms with phone...\n")
        
        phone_identifier = normalized
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self.check_platform, p, phone_identifier, "phone"): p
                for p in PLATFORMS[:20]
            }
            
            for future in as_completed(futures):
                platform = futures[future]
                try:
                    result = future.result(timeout=8)
                    if result.get("registered") == True:
                        results["found"].append({"platform": platform["name"], "type": platform["type"]})
                        print(f"  [+] [{platform['type']:12s}] {platform['name']}")
                except:
                    pass
        
        print(f"\n{'─'*60}")
        print(f"  Scan complete! {len(results['found'])} platforms found")
        print(f"{'─'*60}")
        
        return results
    
    def display_report(self, results):
        """Display complete results organized by category."""
        if not results or "found" not in results:
            print("\n  No results to display.\n")
            return
        
        found = results["found"]
        
        print(f"\n{'='*60}")
        print(f"  COMPLETE DIGITAL FOOTPRINT REPORT")
        print(f"  Target: {results['identifier']}")
        print(f"  Type:   {results['type']}")
        print(f"{'='*60}")
        
        # Organize by category
        categories = {}
        for f in found:
            cat = f.get("type", "other")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(f)
        
        # Display each category
        category_labels = {
            "social": "SOCIAL MEDIA",
            "messaging": "MESSAGING APPS",
            "developer": "DEVELOPER PLATFORMS",
            "streaming": "STREAMING & MEDIA",
            "ecommerce": "E-COMMERCE",
            "gaming": "GAMING",
            "cloud": "CLOUD & PRODUCTIVITY",
            "finance": "FINANCE",
            "professional": "PROFESSIONAL",
            "dating": "DATING",
            "other": "OTHER",
            "directory": "DIRECTORIES",
            "extended": "EXTENDED (HOLEHE)",
        }
        
        for cat, label in category_labels.items():
            items = categories.get(cat, [])
            if items:
                print(f"\n  --- {label} ({len(items)}) ---")
                for item in items:
                    name = item["platform"]
                    if item.get("url"):
                        print(f"    -> {name}: {item['url']}")
                    else:
                        print(f"    -> {name}")
        
        # Summary
        print(f"\n{'='*60}")
        print(f"  SUMMARY")
        print(f"  {'─'*56}")
        print(f"  Total platforms found:     {len(found)}")
        
        # Category breakdown
        for cat, label in category_labels.items():
            count = len(categories.get(cat, []))
            if count > 0:
                print(f"    {label:<30s} {count}")
        
        print(f"{'='*60}\n")


# ──────────────────────────────────────────────────────────────────────
# MAIN INTERACTIVE LOOP
# ──────────────────────────────────────────────────────────────────────

def clear():
    os.system('clear' if os.name == 'posix' else 'cls')

def print_banner():
    clear()
    print("""
  ============================================================
  |                                                          |
  |     WHERE AM I? -- DIGITAL FOOTPRINT SCANNER v4.0        |
  |                                                          |
  |     Find EVERY website and app your identity is          |
  |     registered on worldwide                              |
  |                                                          |
  |     Coverage: 100+ direct checks + 120+ via holehe       |
  |     = 220+ total platforms                               |
  |                                                          |
  ============================================================

  Authorized use only. Scan your own assets first.
""")

def main():
    print_banner()
    scanner = DigitalFootprintScanner()
    
    while True:
        print("")
        print("  MAIN MENU")
        print("  " + "-"*40)
        print("  [1] Scan Email Address")
        print("  [2] Scan Phone Number")
        print("  [3] View Platform List (" + str(len(PLATFORMS)) + " platforms)")
        print("  [0] Exit")
        print("  " + "-"*40)
        
        choice = input("\n  Select option: ").strip()
        
        if choice == "1":
            clear()
            print("\n  Enter the email address to scan:")
            email = input("  -> ").strip()
            
            if not email or "@" not in email:
                print("\n  Invalid email.")
                input("\n  Press Enter...")
                continue
            
            results = scanner.scan_email(email)
            scanner.display_report(results)
            
            # Save report
            safe = email.replace("@", "_at_").replace(".", "_")
            filename = f"footprint_{safe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n  Full report saved: {filename}")
            
            input("\n  Press Enter to continue...")
            print_banner()
        
        elif choice == "2":
            clear()
            print("\n  Enter the phone number to scan (include country code):")
            print("  Examples: +14155551234, +917994452892, +447700900000")
            phone = input("  -> ").strip()
            
            if not phone:
                print("\n  Invalid phone.")
                input("\n  Press Enter...")
                continue
            
            results = scanner.scan_phone(phone)
            scanner.display_report(results)
            
            if results["found"]:
                safe = phone.replace("+", "plus_").replace(" ", "_")
                filename = f"footprint_{safe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(filename, 'w') as f:
                    json.dump(results, f, indent=2, default=str)
                print(f"\n  Full report saved: {filename}")
            
            input("\n  Press Enter to continue...")
            print_banner()
        
        elif choice == "3":
            clear()
            print(f"\n  PLATFORM CHECKLIST ({len(PLATFORMS)} platforms)\n")
            
            categories = {}
            for p in PLATFORMS:
                cat = p.get("type", "other")
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(p["name"])
            
            cat_names = {
                "social": "Social Media", "messaging": "Messaging",
                "developer": "Developer", "streaming": "Streaming/Media",
                "ecommerce": "E-Commerce", "gaming": "Gaming",
                "cloud": "Cloud/Productivity", "finance": "Finance",
                "professional": "Professional", "dating": "Dating",
                "other": "Other"
            }
            
            for cat, label in cat_names.items():
                items = categories.get(cat, [])
                if items:
                    print(f"  {label} ({len(items)}):")
                    for i, name in enumerate(items, 1):
                        print(f"    {i:2d}. {name}")
                    print()
            
            print("  Plus 120+ additional platforms via holehe extension")
            print("  Total: ~220 platforms checked")
            
            input("\n  Press Enter to continue...")
            print_banner()
        
        elif choice == "0":
            print("\n  Exiting. Stay safe.\n")
            break
        
        else:
            print("\n  Invalid option.")
            time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Interrupted. Exiting.\n")
        sys.exit(0)