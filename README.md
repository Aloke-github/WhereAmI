# WhereAmI

WhereAmI is an advanced OSINT identity pivot engine designed for cybersecurity researchers, SOC analysts, and bug bounty hunters.

It automates the discovery of digital footprints linked to:
- Email addresses
- Phone numbers
- Usernames
- Breached credentials
- Social profiles
- Public metadata

---

## Features

### Email Intelligence
- 120+ platform registration checks using Holehe
- Gravatar lookup
- GitHub account discovery
- Google dork automation
- MX/domain analysis

### Phone Number Intelligence
- Carrier detection
- VoIP identification
- Region/country analysis
- Social footprint enumeration
- PhoneInfoga integration

### Username Enumeration
- Sherlock-style username derivation
- Multi-platform account discovery
- Profile correlation

### Breach Intelligence
- HaveIBeenPwned integration
- Pastebin exposure detection
- Dehashed support (API optional)

### Reporting
- JSON export
- HTML report generation
- Structured OSINT evidence output

---

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/WhereAmI.git
cd WhereAmI

pip install -r requirements.txt
```

---

## Usage

### Email Investigation

```bash
python whereami.py --email target@example.com
```

### Phone Investigation

```bash
python whereami.py --phone +1234567890
```

### Username Investigation

```bash
python whereami.py --username johndoe
```

### Full Investigation

```bash
python whereami.py --email target@example.com --phone +1234567890 --username johndoe
```

---

## Output

Reports are generated in:
- JSON
- HTML

Example:
```bash
/output/report.html
/output/report.json
```

---

## Tech Stack

- Python
- Holehe
- PhoneInfoga
- Sherlock-inspired enumeration
- Requests
- BeautifulSoup
- OSINT APIs

---

## Legal Disclaimer

This project is intended strictly for:
- Educational purposes
- Authorized security research
- Defensive cybersecurity operations

Users are responsible for complying with all local laws and regulations.

---

## Author

Aloke Krishna T R

Cybersecurity Enthusiast | SOC Analyst Aspirant | OSINT Researcher
