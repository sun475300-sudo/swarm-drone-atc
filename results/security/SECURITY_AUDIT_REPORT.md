# P719 Security Audit Report

Generated: 2026-05-31 20:07:44

- Packages scanned: **240**
- Vulnerable packages: **10**
- Total CVEs: **37**

## Vulnerable Packages

| Package | Version | CVEs | Fix Version | Action |
|---------|---------|------|-------------|--------|
| pypdf | 5.9.0 | 22 | 6.9.2 | pip install pypdf>=6.9.2 |
| pip | 24.0 | 4 | 26.1 | pip install pip>=26.1 |
| gitpython | 3.1.47 | 2 | 3.1.50 | pip install gitpython>=3.1.50 |
| setuptools | 70.2.0 | 2 | 78.1.1 | pip install setuptools>=78.1.1 |
| urllib3 | 2.6.3 | 2 | 2.7.0 | pip install urllib3>=2.7.0 |
| idna | 3.11 | 1 | 3.15 | pip install idna>=3.15 |
| lxml | 6.0.4 | 1 | 6.1.0 | pip install lxml>=6.1.0 |
| pytest | 8.4.2 | 1 | 9.0.3 | pip install pytest>=9.0.3 |
| python-multipart | 0.0.26 | 1 | 0.0.27 | pip install python-multipart>=0.0.27 |
| starlette | 1.0.0 | 1 | 1.0.1 | pip install starlette>=1.0.1 |

## CVE Details

### pypdf==5.9.0
- CVE-2025-55197
- CVE-2025-62707
- CVE-2025-62708
- CVE-2025-66019
- CVE-2026-22690
- CVE-2026-22691
- CVE-2026-24688
- CVE-2026-27026
- CVE-2026-27024
- CVE-2026-27025
- CVE-2026-27628
- CVE-2026-27888
- CVE-2026-28351
- CVE-2026-28804
- CVE-2026-31826
- CVE-2026-33123
- CVE-2026-33699
- CVE-2026-40260
- CVE-2026-41168
- CVE-2026-41313
- CVE-2026-41312
- CVE-2026-41314
- Fix: upgrade to >= 6.9.2

### pip==24.0
- CVE-2025-8869
- CVE-2026-1703
- CVE-2026-3219
- CVE-2026-6357
- Fix: upgrade to >= 26.1

### gitpython==3.1.47
- CVE-2026-44244
- GHSA-mv93-w799-cj2w
- Fix: upgrade to >= 3.1.50

### setuptools==70.2.0
- PYSEC-2025-49
- PYSEC-2025-49
- Fix: upgrade to >= 78.1.1

### urllib3==2.6.3
- PYSEC-2026-142
- PYSEC-2026-141
- Fix: upgrade to >= 2.7.0

### idna==3.11
- CVE-2026-45409
- Fix: upgrade to >= 3.15

### lxml==6.0.4
- PYSEC-2026-87
- Fix: upgrade to >= 6.1.0

### pytest==8.4.2
- CVE-2025-71176
- Fix: upgrade to >= 9.0.3

### python-multipart==0.0.26
- CVE-2026-42561
- Fix: upgrade to >= 0.0.27

### starlette==1.0.0
- PYSEC-2026-161
- Fix: upgrade to >= 1.0.1

## Summary: Risk Level = **HIGH**

Most vulnerabilities are in indirect dependencies (pypdf, tornado, gitpython).
None affect the core SDACS simulation engine directly.
Recommended: upgrade flagged packages in requirements.txt.
