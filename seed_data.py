# seed_data.py - SAMPLE (placeholder) articles so the site is not empty.
#
# IMPORTANT: these stories are NOT real news. I wrote them myself as practice
# data, using made-up company names (Contoso, Northwind, Fabrikam...).
# The source names are real news sites, but the links only go to their HOME
# pages, never to a fake article address.

THN = ("The Hacker News", "https://thehackernews.com/")
SW = ("SecurityWeek", "https://www.securityweek.com/")
BC = ("BleepingComputer", "https://www.bleepingcomputer.com/")
KREBS = ("Krebs on Security", "https://krebsonsecurity.com/")
CISA = ("CISA", "https://www.cisa.gov/")


def article(src, title, summary, content, category, date, featured=0):
    return {"source": src[0], "source_url": src[1], "title": title, "summary": summary,
            "content": content, "category": category, "published_date": date,
            "is_featured": featured}


SAMPLE_ARTICLES = [
    article(THN, "Critical flaw in popular VPN appliance lets attackers skip login",
            "A made-up example: a bug in the web portal of a VPN box lets an attacker reach admin pages without a password.",
            "This is sample text for my student project.\n\nIn this practice story, a vendor fixes a bug where the VPN login page did not check the session correctly. "
            "Lesson for defenders: patch internet-facing devices first, check logs for strange admin logins, and turn on multi-factor authentication.",
            "Vulnerabilities", "2026-10-22", featured=1),
    article(SW, "Ransomware gang hits fictional hospital group Northwind Clinics",
            "Practice story: appointment systems at a made-up hospital group go offline after a ransomware attack.",
            "This is sample text for my student project.\n\nNorthwind Clinics is not a real company. In the story, staff go back to paper forms while IT restores systems from offline backups. "
            "Lesson: keep tested offline backups and an incident response plan that everyone knows.",
            "Ransomware", "2026-10-21", featured=1),
    article(BC, "Fake invoice emails spread password-stealing malware",
            "Sample story: phishing emails pretending to be invoices carry a ZIP file with an info-stealer inside.",
            "This is sample text for my student project.\n\nThe emails say 'Invoice overdue' and push people to open an attachment. "
            "Lesson: check the sender, hover over links, never enable macros, and report the email to the security team.",
            "Phishing", "2026-10-20", featured=1),
    article(KREBS, "Data broker leak exposes millions of made-up customer records",
            "Practice story: an unprotected cloud database at fictional company Fabrikam Data was open to the internet.",
            "This is sample text for my student project.\n\nNo password protected the database, so anyone who found it could read names and emails. "
            "Lesson: never leave storage public, scan your cloud for open buckets, and collect only the data you really need.",
            "Data Breach", "2026-10-19"),
    article(CISA, "Advisory: patch known exploited bugs in office routers",
            "Sample advisory: defenders are asked to update small-office routers that attackers are actively scanning for.",
            "This is sample text for my student project.\n\nThe practice advisory lists steps: update firmware, change default passwords, turn off remote admin from the internet. "
            "Lesson: a simple router update can close a door attackers are already knocking on.",
            "Vulnerabilities", "2026-10-18"),
    article(THN, "Malicious browser extensions caught stealing session cookies",
            "Practice story: 'free PDF converter' extensions secretly send login cookies to an attacker server.",
            "This is sample text for my student project.\n\nWith a stolen session cookie, an attacker can act as the user without knowing the password. "
            "Lesson: only install extensions you really need, from trusted publishers, and review them regularly.",
            "Malware", "2026-10-17"),
    article(SW, "Misconfigured cloud storage at Contoso Retail leaks backups",
            "Sample story: a storage bucket with database backups was set to public by mistake.",
            "This is sample text for my student project.\n\nContoso Retail is a made-up company. The backups contained old customer orders. "
            "Lesson: use 'private by default', turn on cloud security alerts, and encrypt backups.",
            "Cloud Security", "2026-10-15"),
    article(BC, "New phishing kit can bypass weak multi-factor prompts",
            "Practice story: a phishing page sits between the user and the real site and steals the login session.",
            "This is sample text for my student project.\n\nThis is called an adversary-in-the-middle attack. "
            "Lesson: phishing-resistant MFA (like security keys or passkeys) is much stronger than SMS codes.",
            "Phishing", "2026-10-14"),
    article(KREBS, "Researchers map a botnet made of hacked smart cameras",
            "Sample research story: thousands of cheap cameras with default passwords are used to flood websites.",
            "This is sample text for my student project.\n\nThe cameras still used the factory password 'admin'. "
            "Lesson: change default passwords and keep IoT devices on a separate network.",
            "Research", "2026-10-12"),
    article(THN, "Supply chain attack: poisoned package found in public code registry",
            "Practice story: a library with a name very close to a popular one installs a backdoor.",
            "This is sample text for my student project.\n\nThis trick is called typosquatting. "
            "Lesson: double-check package names, pin versions in requirements.txt, and use dependency scanning.",
            "Malware", "2026-10-10"),
    article(CISA, "Back to basics: five steps every small business should take",
            "Sample guidance: MFA, updates, backups, staff training and an incident plan.",
            "This is sample text for my student project.\n\nNone of these steps are expensive, but together they stop most common attacks. "
            "Lesson: security is mostly good habits done every day.",
            "Advice", "2026-10-08"),
    article(SW, "Insider downloads customer list before leaving fictional firm",
            "Practice story: an employee copies a sales database to a personal USB drive on their last day.",
            "This is sample text for my student project.\n\nLogs showed a big download late at night. "
            "Lesson: least privilege, alerting on unusual downloads, and removing access fast when people leave.",
            "Data Breach", "2026-10-05"),
]
