#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║                     WHEREAMI v2.0 — ALL-IN-ONE              ║
║  Find every online presence tied to an email or phone       ║
║  Usage: python whereami.py -e user@example.com              ║
║         python whereami.py -p +14155551234                  ║
║         python whereami.py -e user@example.com --html       ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, re, json, hashlib, sys, time, urllib.parse, argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from typing import Dict, List, Optional, Any

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("[!] Install dependencies: pip install requests beautifulsoup4")
    sys.exit(1)

# Optional imports — tool works without them but loses some modules
HOLEHE_AVAILABLE = False
PHONEINFOGA_AVAILABLE = False
try:
    from holehe.core import launch_module
    from holehe.modules_registered import get_modules
    HOLEHE_AVAILABLE = True
except ImportError:
    pass

try:
    from phoneinfoga import PhoneInfoga
    PHONEINFOGA_AVAILABLE = True
except ImportError:
    pass

requests.packages.urllib3.disable_warnings()

BANNER = r"""
  ╔══════════════════════════════════════════════════════════╗
  ║                    ██╗    ██╗██╗  ██╗███████╗██████╗    ║
  ║                    ██║    ██║██║  ██║██╔════╝██╔══██╗   ║
  ║                    ██║ █╗ ██║███████║█████╗  ██████╔╝   ║
  ║                    ██║███╗██║╚════██║██╔══╝  ██╔══██╗   ║
  ║                    ╚███╔███╔╝     ██║███████╗██║  ██║   ║
  ║                     ╚══╝╚══╝      ╚═╝╚══════╝╚═╝  ╚═╝   ║
  ║                          ALL-IN-ONE v2.0                  ║
  ║         Email & Phone OSINT — Everywhere You Exist         ║
  ╚══════════════════════════════════════════════════════════════╝
"""


class WhereAmIAllInOne:
    """The complete identity pivot engine."""

    # ─── Known platforms for registration checks (fallback if holehe not avail) ───
    FALLBACK_REGISTRATION_SITES = [
        {"name": "Instagram", "url": "https://www.instagram.com/accounts/account_recovery_send_email/",
         "field": "email_or_username", "indicator": ["not found", "doesn't exist"],
         "method": "reset_status"},
        {"name": "Twitter/X", "url": "https://api.twitter.com/i/users/email_available.json",
         "field": "email", "indicator": ["taken"], "method": "api"},
        {"name": "Spotify", "url": "https://www.spotify.com/api/signup/checkemail",
         "field": "email", "indicator": ["true"], "method": "api"},
        {"name": "Adobe", "url": "https://auth.services.adobe.com/signup/v2/users/email",
         "field": "email", "indicator": ["already"], "method": "api"},
    ]

    # ─── Server/platform types for phone carrier detection ───
    KNOWN_CARRIER_PATTERNS = {
        "verizon": ["verizon", "vtext", "vzw"],
        "tmobile": ["tmobile", "tmomail", "t-mobile"],
        "att": ["att", "att.net", "mms.att"],
        "sprint": ["sprint", "messaging.sprint", "sprintpcs"],
        "google_fi": ["google.fi", "msg.fi"],
        "visible": ["visible.com"],
        "mint": ["mintmobile"],
    }

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "DNT": "1",
        "Connection": "keep-alive",
    }

    def __init__(self, identifier: str, quiet: bool = False, timeout: int = 10,
                 dehashed_key: Optional[str] = None, output_format: str = "json"):
        self.identifier = identifier.strip()
        self.quiet = quiet
        self.timeout = timeout
        self.dehashed_key = dehashed_key
        self.output_format = output_format
        self.type = self._identify_type()
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.results = {
            "identifier": self.identifier,
            "type": self.type,
            "scan_timestamp": datetime.now().isoformat(),
            "sections": {
                "direct_registrations": [],
                "social_profiles": [],
                "breaches_and_leaks": [],
                "phone_carrier_info": {},
                "associated_usernames": [],
                "google_dorks": [],
                "domain_whois": [],
                "code_repos": [],
                "raw_exposure": [],
            },
            "summary": {
                "total_platforms_found": 0,
                "total_breaches": 0,
                "risk_score": "unknown",
            }
        }

    def _log(self, msg: str):
        if not self.quiet:
            print(f"  [{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def _identify_type(self) -> str:
        if re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', self.identifier):
            return "email"
        cleaned = re.sub(r'[\s\-\+\(\)\.]', '', self.identifier)
        if cleaned.startswith('+') and cleaned[1:].isdigit():
            return "phone"
        if cleaned.isdigit() and 7 <= len(cleaned) <= 15:
            return "phone"
        return "unknown"

    def _normalize_phone(self) -> str:
        return re.sub(r'[\s\-\+\(\)\.]', '', self.identifier)

    def _derive_usernames(self) -> List[str]:
        """Derive potential usernames from email prefix."""
        if self.type != "email":
            return []
        local = self.identifier.split("@")[0].lower()
        usernames = {local}
        usernames.add(local.replace(".", ""))
        usernames.add(local.replace("_", ""))
        usernames.add(local.replace("-", ""))
        # Gmail normalizations
        local_no_dots = local.replace(".", "")
        usernames.add(local_no_dots)
        if "+" in local:
            base = local.split("+")[0]
            usernames.add(base)
            usernames.add(base.replace(".", ""))
        # Common patterns
        for base in list(usernames):
            usernames.add(base + "1")
            usernames.add(base + "123")
            usernames.add("_" + base)
        return list(usernames)

    # ═══════════════════════════════════════════════════════════
    #  MODULE 1: HOLEHE — 120+ Email Registration Checks
    # ═══════════════════════════════════════════════════════════

    def _holehe_check(self):
        """Run holehe's full module suite to check 120+ platforms."""
        if not HOLEHE_AVAILABLE:
            self._log("HOLEHE: Not installed — run 'pip install holehe' to enable 120+ checks")
            self._fallback_registration_check()
            return
        self._log("HOLEHE: Checking 120+ platforms (this takes ~60s)...")
        try:
            modules = get_modules()
            found = 0
            for module in modules:
                try:
                    result = launch_module(module, self.identifier, self.session)
                    if result and result.get("exists"):
                        entry = {
                            "platform": module.__name__.split(".")[-1].replace("_", " ").title(),
                            "exists": True,
                            "method": "registration_check",
                            "details": result.get("response", ""),
                            "source_module": module.__name__,
                        }
                        self.results["sections"]["direct_registrations"].append(entry)
                        found += 1
                except Exception:
                    continue
            self._log(f"HOLEHE: Found {found} registered platforms")
        except Exception as e:
            self._log(f"HOLEHE error: {e}")
            self._fallback_registration_check()

    def _fallback_registration_check(self):
        """Fallback if holehe not available — check known sites manually."""
        self._log("FALLBACK: Checking known platforms directly...")
        for site in self.FALLBACK_REGISTRATION_SITES:
            try:
                if site["method"] == "api":
                    data = {site["field"]: self.identifier}
                    r = self.session.post(site["url"], data=data, timeout=self.timeout,
                                         allow_redirects=False)
                    body = r.text.lower()
                    registered = any(ind.lower() in body for ind in site["indicator"])
                    self.results["sections"]["direct_registrations"].append({
                        "platform": site["name"],
                        "exists": registered,
                        "method": "api_check",
                        "http_status": r.status_code,
                    })
                elif site["method"] == "reset_status":
                    data = {site["field"]: self.identifier}
                    r = self.session.post(site["url"], data=data, timeout=self.timeout)
                    body = r.text.lower()
                    # If "not found" NOT in response — account likely exists
                    registered = not any(ind.lower() in body for ind in site["indicator"])
                    self.results["sections"]["direct_registrations"].append({
                        "platform": site["name"],
                        "exists": registered,
                        "method": "reset_guess",
                        "http_status": r.status_code,
                    })
                time.sleep(0.3)
            except Exception as e:
                self._log(f"FALLBACK {site['name']} error: {e}")

    # ═══════════════════════════════════════════════════════════
    #  MODULE 2: PHONEINFOGA — Phone Number OSINT
    # ═══════════════════════════════════════════════════════════

    def _phone_scanner(self):
        """Phone number intelligence: carrier, VoIP, social, footprints."""
        if self.type != "phone":
            return

        phone = self._normalize_phone()
        self._log("PHONE: Running carrier detection, VoIP check, and social scans...")

        # Carrier detection via free APIs
        carrier_urls = [
            f"https://carrierlookup.com/api/carrier/{phone}",
            f"https://www.carrierlookup.com/lookup/{phone}",
        ]
        for url in carrier_urls:
            try:
                r = self.session.get(url, timeout=self.timeout)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, 'html.parser')
                    text = soup.get_text().lower()
                    for carrier, patterns in self.KNOWN_CARRIER_PATTERNS.items():
                        if any(p in text for p in patterns):
                            self.results["sections"]["phone_carrier_info"]["carrier"] = carrier
                            self._log(f"PHONE: Carrier detected as {carrier}")
                            break
            except Exception:
                continue

        # VoIP / burner detection via numverify (free tier)
        try:
            # Using free numverify API (no key = limited)
            r = self.session.get(
                f"http://apilayer.net/api/validate?number={phone}&country_code=US&format=1",
                timeout=self.timeout
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("success"):
                    self.results["sections"]["phone_carrier_info"].update({
                        "country": data.get("country_name"),
                        "country_code": data.get("country_code"),
                        "location": data.get("location"),
                        "carrier": data.get("carrier"),
                        "line_type": data.get("line_type"),
                        "valid": data.get("valid"),
                    })
                    self._log(f"PHONE: Valid={data.get('valid')}, Type={data.get('line_type')}, "
                             f"Carrier={data.get('carrier')}")
        except Exception:
            pass

        # Social platform checks
        platforms_phone = [
            ("WhatsApp", f"https://wa.me/{phone}"),
            ("Telegram", f"https://t.me/+{phone}"),
            ("Truecaller", f"https://www.truecaller.com/search/us/{phone}"),
        ]
        for name, url in platforms_phone:
            try:
                r = self.session.get(url, timeout=self.timeout, allow_redirects=True)
                if r.status_code != 404 and r.status_code != 302:
                    self.results["sections"]["social_profiles"].append({
                        "platform": name,
                        "url": url,
                        "found": True,
                        "http_status": r.status_code,
                    })
                    self._log(f"PHONE: Possible {name} profile linked")
            except Exception:
                continue

        # PhoneInfoga integration if available
        if PHONEINFOGA_AVAILABLE:
            try:
                scanner = PhoneInfoga()
                result = scanner.scan(f"+{phone}")
                if result and isinstance(result, dict):
                    for key, val in result.items():
                        if isinstance(val, dict) and val.get("found"):
                            self.results["sections"]["social_profiles"].append({
                                "platform": key,
                                "url": val.get("url", ""),
                                "found": True,
                                "details": val.get("details", ""),
                            })
                    self._log("PHONE: PhoneInfoga results merged")
            except Exception as e:
                self._log(f"PHONE: PhoneInfoga error: {e}")

    # ═══════════════════════════════════════════════════════════
    #  MODULE 3: GRAVATAR
    # ═══════════════════════════════════════════════════════════

    def _gravatar_check(self):
        if self.type != "email":
            return
        email_hash = hashlib.md5(self.identifier.lower().strip().encode()).hexdigest()
        url = f"https://www.gravatar.com/{email_hash}.json"
        try:
            r = self.session.get(url, timeout=self.timeout)
            if r.status_code == 200:
                data = r.json()
                if data.get("entry"):
                    profile = data["entry"][0]
                    entry = {
                        "platform": "Gravatar",
                        "profile_url": f"https://www.gravatar.com/{email_hash}",
                        "avatar": f"https://www.gravatar.com/avatar/{email_hash}?s=200",
                        "display_name": profile.get("displayName"),
                        "username": profile.get("preferredUsername"),
                        "about": profile.get("aboutMe", "")[:300],
                        "location": profile.get("currentLocation"),
                        "urls": profile.get("urls", []),
                    }
                    self.results["sections"]["social_profiles"].append(entry)
                    self._log(f"GRAVATAR: Profile found — {entry['display_name'] or 'No name'}")
        except Exception:
            self._log("GRAVATAR: No profile")

    # ═══════════════════════════════════════════════════════════
    #  MODULE 4: GITHUB
    # ═══════════════════════════════════════════════════════════

    def _github_check(self):
        if self.type != "email":
            return
        url = f"https://api.github.com/search/commits?q={urllib.parse.quote(self.identifier)}&sort=author-date&per_page=5"
        try:
            r = self.session.get(url, timeout=self.timeout,
                                headers={**self.HEADERS, "Accept": "application/vnd.github.cloak+json"})
            if r.status_code == 200:
                data = r.json()
                if data["total_count"] > 0:
                    commits = []
                    for item in data["items"][:5]:
                        commits.append({
                            "repo": item["repository"]["full_name"],
                            "author": item["commit"]["author"]["name"],
                            "date": item["commit"]["author"]["date"][:10],
                            "url": f"https://github.com/{item['repository']['full_name']}/commit/{item['sha'][:7]}",
                        })
                    self.results["sections"]["code_repos"].append({
                        "platform": "GitHub",
                        "total_commits": data["total_count"],
                        "commits": commits,
                    })
                    self._log(f"GITHUB: {data['total_count']} commits found")
            else:
                self._log(f"GITHUB: API returned {r.status_code} (rate-limited?)")
        except Exception as e:
            self._log(f"GITHUB error: {e}")

    # ═══════════════════════════════════════════════════════════
    #  MODULE 5: HIBP (k-anonymity)
    # ═══════════════════════════════════════════════════════════

    def _hibp_check(self):
        if self.type != "email":
            return
        sha1 = hashlib.sha1(self.identifier.encode()).hexdigest().upper()
        prefix = sha1[:5]
        suffix = sha1[5:]
        try:
            r = self.session.get(
                f"https://api.pwnedpasswords.com/range/{prefix}",
                timeout=self.timeout,
                headers={"hibp-api-key": ""}  # No key needed for range
            )
            if r.status_code == 200:
                for line in r.text.splitlines():
                    if line.startswith(suffix):
                        count = int(line.split(":")[1].strip())
                        self.results["sections"]["breaches_and_leaks"].append({
                            "source": "HIBP (k-anonymity)",
                            "details": f"Password appears in {count} breach(es)",
                            "severity": "high" if count > 5 else "medium",
                        })
                        self._log(f"HIBP: Password in {count} breaches!")
                        return
                self._log("HIBP: Password not found in breaches")
        except Exception as e:
            self._log(f"HIBP error: {e}")

    # ═══════════════════════════════════════════════════════════
    #  MODULE 6: PASTEBIN / LEAK SITES
    # ═══════════════════════════════════════════════════════════

    def _paste_scanner(self):
        """Scrape multiple paste/leak sites for the identifier."""
        encoded = urllib.parse.quote(self.identifier)
        sources = [
            (f"https://psbdmp.ws/api/search/{encoded}", "Pastebin Dumps (psbdmp)", "json"),
            (f"https://leakcheck.io/api/public?key=&check={encoded}", "LeakCheck", "json"),
        ]
        for url, name, fmt in sources:
            try:
                r = self.session.get(url, timeout=self.timeout)
                if r.status_code == 200:
                    if fmt == "json":
                        data = r.json()
                        count = data.get("count", 0) if name == "Pastebin Dumps (psbdmp)" else len(data.get("result", []))
                        if count > 0:
                            self.results["sections"]["breaches_and_leaks"].append({
                                "source": name,
                                "count": count,
                                "url": url,
                            })
                            self._log(f"PASTE: {count} results from {name}")
            except Exception:
                continue

    # ═══════════════════════════════════════════════════════════
    #  MODULE 7: SHERLOCK-STYLE USERNAME LOOKUP
    # ═══════════════════════════════════════════════════════════

    def _username_search(self):
        """Derive usernames from email and check platforms."""
        usernames = self._derive_usernames()
        if not usernames:
            return
        self._log(f"USERNAME: Derived {len(usernames)} potential usernames from email prefix")
        self.results["sections"]["associated_usernames"] = usernames

        # Check a few major platforms for each username
        platform_urls = {
            "GitHub": lambda u: f"https://api.github.com/users/{u}",
            "Twitter/X": lambda u: f"https://api.twitter.com/2/users/by/username/{u}",
            "Reddit": lambda u: f"https://www.reddit.com/user/{u}/about.json",
            "Instagram": lambda u: f"https://www.instagram.com/{u}/",
            "Keybase": lambda u: f"https://keybase.io/{u}",
            "Mastodon.social": lambda u: f"https://mastodon.social/@{u}",
        }

        # Test the most likely username (the original local part)
        primary = usernames[0]
        for platform, url_builder in platform_urls.items():
            try:
                url = url_builder(primary)
                r = self.session.get(url, timeout=self.timeout, allow_redirects=True)
                if r.status_code == 200 and r.status_code != 404:
                    self.results["sections"]["social_profiles"].append({
                        "platform": platform,
                        "username": primary,
                        "url": url,
                        "found": True,
                        "confidence": "derived_from_email",
                    })
                    self._log(f"USERNAME: {primary} found on {platform}")
                time.sleep(0.2)
            except Exception:
                continue

    # ═══════════════════════════════════════════════════════════
    #  MODULE 8: GOOGLE DORKS
    # ═══════════════════════════════════════════════════════════

    def _generate_dorks(self):
        """Generate comprehensive Google dorks for manual investigation."""
        dorks = []
        if self.type == "email":
            patterns = [
                f'"{self.identifier}"',
                f'intext:"{self.identifier}" "password"',
                f'intext:"{self.identifier}" "username"',
                f'intitle:"{self.identifier}"',
                f'"{self.identifier}" filetype:pdf OR filetype:csv OR filetype:xlsx',
                f'"{self.identifier}" site:linkedin.com',
                f'"{self.identifier}" site:facebook.com',
                f'"{self.identifier}" site:github.com',
                f'"{self.identifier}" site:pastebin.com',
                f'"{self.identifier}" site:reddit.com',
            ]
        else:
            phone = self._normalize_phone()
            patterns = [
                f'"{phone}"',
                f'"{phone}" site:facebook.com',
                f'"{phone}" site:linkedin.com',
                f'"{phone}" site:whitepages.com',
                f'"{phone}" site:truecaller.com',
                f'"{phone}" filetype:pdf',
                f'"+{phone}" OR "{phone}"',
            ]
        for pattern in patterns:
            dorks.append({
                "query": pattern,
                "url": f"https://www.google.com/search?q={urllib.parse.quote(pattern)}"
            })
        self.results["sections"]["google_dorks"] = dorks
        self._log(f"DORKS: {len(dorks)} Google search queries generated")

    # ═══════════════════════════════════════════════════════════
    #  MODULE 9: WHOIS DOMAIN CHECK
    # ═══════════════════════════════════════════════════════════

    def _whois_check(self):
        if self.type != "email":
            return
        domain = self.identifier.split("@")[1]
        try:
            url = f"https://www.whois.com/whois/{domain}"
            r = self.session.get(url, timeout=self.timeout)
            if r.status_code == 200 and self.identifier.lower() in r.text.lower():
                self.results["sections"]["domain_whois"].append({
                    "domain": domain,
                    "email_present": True,
                    "whois_url": url,
                })
                self._log(f"WHOIS: Email found in {domain} registration records")
            else:
                self._log(f"WHOIS: Email not found (WHOIS privacy likely enabled)")
        except Exception as e:
            self._log(f"WHOIS error: {e}")

    # ═══════════════════════════════════════════════════════════
    #  MODULE 10: DEHASHED (if API key provided)
    # ═══════════════════════════════════════════════════════════

    def _dehashed_check(self):
        if not self.dehashed_key:
            return
        self._log("DEHASHED: Checking paid breach database...")
        try:
            email_encoded = urllib.parse.quote(self.identifier)
            r = requests.get(
                f"https://api.dehashed.com/search?query={email_encoded}",
                auth=requests.auth.HTTPBasicAuth(self.dehashed_key, ""),
                timeout=self.timeout,
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("entries"):
                    self.results["sections"]["breaches_and_leaks"].append({
                        "source": "DeHashed",
                        "total_entries": data.get("total", len(data["entries"])),
                        "balance": data.get("balance", "unknown"),
                        "sample_entries": [
                            {
                                "email": e.get("email", ""),
                                "username": e.get("username", ""),
                                "password": e.get("password", "")[:20] + "..." if e.get("password") else "",
                                "hashed_password": e.get("hashed_password", ""),
                                "ip_address": e.get("ip_address", ""),
                                "name": e.get("name", ""),
                                "source": e.get("source", ""),
                            }
                            for e in data["entries"][:10]
                        ],
                    })
                    self._log(f"DEHASHED: {data.get('total', 0)} entries found")
        except Exception as e:
            self._log(f"DEHASHED error: {e}")

    # ═══════════════════════════════════════════════════════════
    #  RUN ALL MODULES
    # ═══════════════════════════════════════════════════════════

    def run(self) -> Dict[str, Any]:
        print(BANNER)
        print(f"  Target:    {self.identifier}")
        print(f"  Type:      {self.type}")
        print(f"  Started:   {self.results['scan_timestamp']}")
        print(f"  Modules:   " + ", ".join([
            "Holehe" if HOLEHE_AVAILABLE else "RegistrationCheck",
            "PhoneInfoga" if PHONEINFOGA_AVAILABLE else "PhoneScanner",
            "Gravatar", "GitHub", "HIBP", "PasteScraper", "UsernameSearch",
            "DorkGenerator", "WHOIS", "DeHashed" if self.dehashed_key else ""
        ]).strip(", "))
        print("─" * 72)

        # ─── Dispatch all checks in parallel ───
        checks = {
            "holehe": self._holehe_check,
            "phone_scanner": self._phone_scanner,
            "gravatar": self._gravatar_check,
            "github": self._github_check,
            "hibp": self._hibp_check,
            "paste_scanner": self._paste_scanner,
            "username_search": self._username_search,
            "dorks": self._generate_dorks,
            "whois": self._whois_check,
            "dehashed": self._dehashed_check,
        }

        with ThreadPoolExecutor(max_workers=6) as executor:
            future_map = {
                executor.submit(func): name
                for name, func in checks.items()
                if name != "dehashed" or self.dehashed_key
            }
            for future in as_completed(future_map):
                try:
                    future.result(timeout=60)
                except TimeoutError:
                    self._log(f"Module {future_map[future]} timed out")
                except Exception as e:
                    self._log(f"Module {future_map[future]} failed: {e}")

        # ─── Compile summary ───
        total_platforms = (len(self.results["sections"]["direct_registrations"]) +
                          len(self.results["sections"]["social_profiles"]))
        total_breaches = len(self.results["sections"]["breaches_and_leaks"])

        self.results["summary"] = {
            "total_platforms_found": total_platforms,
            "total_breaches": total_breaches,
            "risk_score": "high" if total_breaches > 0 and total_platforms > 5 else "medium" if total_platforms > 2 else "low",
            "phone_carrier": self.results["sections"]["phone_carrier_info"].get("carrier", "N/A"),
        }

        print("─" * 72)
        print(f"  ✅ Scan complete — Found {total_platforms} platform hits, {total_breaches} breach sources")
        return self.results

    # ═══════════════════════════════════════════════════════════
    #  REPORTING
    # ═══════════════════════════════════════════════════════════

    def report(self, output_file: Optional[str] = None):
        r = self.results
        s = r["sections"]

        print("\n")
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║                     REPORT — WHERE AM I?                    ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        print(f"  Identifier: {r['identifier']} ({r['type']})")
        print(f"  Risk Score: {r['summary']['risk_score'].upper()}")
        print(f"  Platforms:  {r['summary']['total_platforms_found']}")
        print(f"  Breaches:   {r['summary']['total_breaches']}")
        if r['summary'].get('phone_carrier') and r['summary']['phone_carrier'] != 'N/A':
            print(f"  Carrier:    {r['summary']['phone_carrier']}")
        print()

        # Registration hits
        if s["direct_registrations"]:
            print("  📍 PLATFORMS WHERE ACCOUNT EXISTS")
            print("  " + "─" * 50)
            for hit in s["direct_registrations"]:
                status = "✅ EXISTS" if hit.get("exists", True) else "❌ Not found"
                print(f"  • {hit['platform']:<30s} {status}")
            print()

        # Social profiles
        if s["social_profiles"]:
            print("  👤 SOCIAL PROFILES FOUND")
            print("  " + "─" * 50)
            for prof in s["social_profiles"]:
                name = prof.get("display_name") or prof.get("username") or ""
                print(f"  • {prof['platform']:<20s} {name}")
                if prof.get("profile_url"):
                    print(f"    └─ {prof['profile_url']}")
            print()

        # Breaches
        if s["breaches_and_leaks"]:
            print("  🔓 BREACHES & LEAKS")
            print("  " + "─" * 50)
            for breach in s["breaches_and_leaks"]:
                count_str = f" ({breach.get('count', '')})" if breach.get('count') else ""
                print(f"  • {breach['source']}{count_str}")
                if breach.get("details"):
                    print(f"    └─ {breach['details']}")
                if breach.get("sample_entries"):
                    print(f"    └─ Sample: {breach['total_entries']} total entries")
            print()

        # Usernames
        if s["associated_usernames"]:
            print("  🔑 DERIVED USERNAMES")
            print("  " + "─" * 50)
            print(f"  {', '.join(s['associated_usernames'][:10])}")
            if len(s["associated_usernames"]) > 10:
                print(f"  ... and {len(s['associated_usernames']) - 10} more")
            print()

        # Google dorks
        if s["google_dorks"]:
            print("  🔍 GOOGLE DORKS — Open these in your browser")
            print("  " + "─" * 50)
            for dork in s["google_dorks"][:8]:
                print(f"  • {dork['query']}")
            if len(s["google_dorks"]) > 8:
                print(f"  ... and {len(s['google_dorks']) - 8} more")
            print()

        # Phone carrier info
        if s["phone_carrier_info"]:
            print("  📱 PHONE CARRIER INFO")
            print("  " + "─" * 50)
            for key, val in s["phone_carrier_info"].items():
                if val:
                    print(f"  • {key.replace('_', ' ').title()}: {val}")
            print()

        # Code repos
        if s["code_repos"]:
            print("  💻 CODE REPOSITORIES")
            print("  " + "─" * 50)
            for repo in s["code_repos"]:
                print(f"  • {repo['platform']}: {repo['total_commits']} commits")
                for commit in repo.get("commits", [])[:3]:
                    print(f"    ├─ {commit['repo']} ({commit['date']})")
                    print(f"    └─ {commit['url']}")
            print()

        # Save output
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(r, f, indent=2, default=str)
            print(f"  💾 Full report saved to: {output_file}")

        # HTML report
        if self.output_format == "html":
            self._html_report(output_file or "whereami_report.html")

        return r

    def _html_report(self, filename: str):
        """Generate a self-contained HTML report."""
        r = self.results
        s = r["sections"]

        html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>WhereAmI Report — {r['identifier']}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          max-width: 1000px; margin: 20px auto; padding: 20px; background: #0d1117; color: #c9d1d9; }}
  h1 {{ color: #58a6ff; border-bottom: 2px solid #30363d; padding-bottom: 10px; }}
  h2 {{ color: #58a6ff; margin-top: 30px; }}
  .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 15px; margin: 10px 0; }}
  .exists {{ color: #3fb950; }} .not-found {{ color: #f85149; }} .warning {{ color: #d29922; }}
  .dork {{ font-family: monospace; color: #79c0ff; }}
  table {{ width: 100%; border-collapse: collapse; }}
  td, th {{ padding: 8px; text-align: left; border-bottom: 1px solid #30363d; }}
  .meta {{ color: #8b949e; font-size: 0.9em; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.8em;
           background: #21262d; margin: 2px; }}
  .high {{ background: #da3633; color: white; }}
  .medium {{ background: #d29922; color: black; }}
  .low {{ background: #3fb950; color: white; }}
</style></head><body>
<h1>📋 WhereAmI Report</h1>
<p><strong>Identifier:</strong> {r['identifier']}<br>
<strong>Type:</strong> {r['type']}<br>
<strong>Scan Time:</strong> {r['scan_timestamp']}<br>
<strong>Risk:</strong> <span class="badge {r['summary']['risk_score']}">{r['summary']['risk_score'].upper()}</span>
<span class="badge">{r['summary']['total_platforms_found']} platforms</span>
<span class="badge">{r['summary']['total_breaches']} breaches</span></p>
"""
        # Registration hits
        if s["direct_registrations"]:
            html += "<h2>📍 Platform Registrations</h2><div class='card'><table>"
            html += "<tr><th>Platform</th><th>Status</th></tr>"
            for hit in s["direct_registrations"]:
                status = "✅ Found" if hit.get("exists", True) else "❌ Not Found"
                html += f"<tr><td>{hit['platform']}</td><td>{status}</td></tr>"
            html += "</table></div>"

        # Social profiles
        if s["social_profiles"]:
            html += "<h2>👤 Social Profiles</h2><div class='card'>"
            for prof in s["social_profiles"]:
                html += f"<p><strong>{prof['platform']}</strong> — "
                html += f"{prof.get('display_name', '') or prof.get('username', '')}</p>"
                if prof.get("profile_url"):
                    url = prof["profile_url"]
                    html += f'<p class="meta"><a href="{url}" target="_blank">{url}</a></p>'
                if prof.get("about"):
                    html += f'<p class="meta">{prof["about"][:200]}</p>'
            html += "</div>"

        # Breaches
        if s["breaches_and_leaks"]:
            html += "<h2>🔓 Breaches & Leaks</h2><div class='card'>"
            for breach in s["breaches_and_leaks"]:
                html += f"<p><strong>{breach['source']}</strong>"
                if breach.get("count"):
                    html += f" — {breach['count']} entries"
                if breach.get("details"):
                    html += f": {breach['details']}</p>"
                if breach.get("sample_entries"):
                    html += "<table><tr><th>Source</th><th>Email</th><th>Username</th><th>Password</th></tr>"
                    for e in breach["sample_entries"][:5]:
                        html += f"<tr><td>{e.get('source','')}</td><td>{e.get('email','')}</td>"
                        html += f"<td>{e.get('username','')}</td><td>{e.get('password','')}</td></tr>"
                    html += "</table>"
            html += "</div>"

        # Google Dorks
        if s["google_dorks"]:
            html += "<h2>🔍 Google Dorks</h2><div class='card'><ol>"
            for dork in s["google_dorks"][:10]:
                html += f'<li><a href="{dork["url"]}" target="_blank" class="dork">{dork["query"]}</a></li>'
            html += "</ol></div>"

        # Phone carrier
        if s["phone_carrier_info"]:
            html += "<h2>📱 Phone Intelligence</h2><div class='card'>"
            for k, v in s["phone_carrier_info"].items():
                if v:
                    html += f"<p><strong>{k.replace('_',' ').title()}:</strong> {v}</p>"
            html += "</div>"

        # Usernames
        if s["associated_usernames"]:
            html += "<h2>🔑 Derived Usernames</h2><div class='card'>"
            for uname in s["associated_usernames"][:10]:
                html += f'<span class="badge">{uname}</span> '
            html += "</div>"

        html += "</body></html>"
        with open(filename, 'w') as f:
            f.write(html)
        self._log(f"📄 HTML report: {os.path.abspath(filename)}")


def main():
    parser = argparse.ArgumentParser(
        description="WhereAmI v2 — All-in-One Email & Phone OSINT Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python whereami.py -e user@example.com
  python whereami.py -p +14155551234
  python whereami.py -e user@example.com --html -o report
  python whereami.py -p +33612345678 --dehashed-key YOUR_API_KEY -q
        """
    )
    parser.add_argument("-e", "--email", help="Email address to scan")
    parser.add_argument("-p", "--phone", help="Phone number to scan (E.164 format)")
    parser.add_argument("-o", "--output", help="Output file path (default: whereami_report.json)")
    parser.add_argument("--html", action="store_true", help="Generate HTML report")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress live output")
    parser.add_argument("--dehashed-key", help="DeHashed API key for paid breach lookup")
    parser.add_argument("--timeout", type=int, default=10, help="Request timeout in seconds")
    args = parser.parse_args()

    if not args.email and not args.phone:
        parser.print_help()
        print("\n  [!] Provide either --email or --phone")
        sys.exit(1)

    identifier = args.email if args.email else args.phone
    output_format = "html" if args.html else "json"
    output_file = args.output or f"whereami_{identifier.replace('@','_at_').replace('+','plus_')}.json"

    scanner = WhereAmIAllInOne(
        identifier=identifier,
        quiet=args.quiet,
        timeout=args.timeout,
        dehashed_key=args.dehashed_key,
        output_format=output_format,
    )

    results = scanner.run()
    scanner.report(output_file=output_file if output_format == "json" else None)

    if args.html:
        html_file = (args.output or f"whereami_{identifier.replace('@','_at_').replace('+','plus_')}") + ".html"
        scanner._html_report(html_file)


if __name__ == "__main__":
    main()