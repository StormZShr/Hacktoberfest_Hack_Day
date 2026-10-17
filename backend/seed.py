"""Demo data: two demo sellers and five sample projects.

Deterministic and offline: the canned reviews below are what A2 would produce,
so the browse page and the demo path work without waiting on the model.

Run from the backend/ directory:
    python seed.py
"""

from sqlmodel import Session, select

import auth
from db import create_db_and_tables, engine
from models import Project, User

DEMO_PASSWORD = "launchpad123"

SELLERS = [
    ("ananya@example.com", "Ananya Sharma"),
    ("rahul@example.com", "Rahul Verma"),
]

REVIEW_GOOD = {
    "score": 82,
    "summary": "The listing explains the project and the setup steps clearly. A licence note and a screenshot would remove the last doubts for a buyer.",
    "missing_items": ["no licence file", "no screenshot of the app"],
    "risk_flags": ["claims work on a network but does not say the database is not securely configured. Check whether the target device supports the platform."],
    "suggestions": [
        "Add an MIT licence line to the README.",
        "Paste one screenshot above the setup section.",
        "Add a sentence that a campus network is required.",
    ],
}

REVIEW_ROUGH = {
    "score": 54,
    "summary": "The idea comes through, but a buyer cannot run this from the listing alone. Setup steps, dependency versions, and a licence are missing.",
    "missing_items": ["no setup steps", "no dependency list", "no licence"],
    "risk_flags": ["no statement that it runs end to end", "no licence, so the buyer's rights are unclear"],
    "suggestions": [
        "Add a numbered setup section with the exact commands.",
        "Say which Python and Node versions you tested.",
        "Add a licence line to the README.",
    ],
}

PROJECTS: list[dict] = [
    {
        "seller": "ananya@example.com",
        "title": "StudyBuddy: flashcards from your notes",
        "tagline": "Turns your lecture notes into question-answer flashcards you can revise from.",
        "description": (
            "StudyBuddy reads a text file of lecture notes and produces question-answer pairs you can "
            "grade yourself on. It keeps a score per topic so you can see what you keep forgetting.\n\n"
            "The backend is FastAPI with SQLite and one local model call per note file. The flashcards "
            "are stored as JSON, and the review screen re-asks only the cards you got wrong twice."
        ),
        "tech_stack": ["Python", "FastAPI", "SQLite", "Ollama", "HTML", "CSS"],
        "category": "ml-ai",
        "difficulty": "intermediate",
        "what_you_get": [
            "Full Python source with comments",
            "SQLite schema and a seed script",
            "Step-by-step setup in the README",
            "Sample lecture notes to test with",
        ],
        "demo_points": [
            "I paste a page of notes and the app builds flashcards in about ten seconds.",
            "Wrong answers come back in the next round, right ones do not.",
            "The per-topic score shows which chapter to revise first.",
        ],
        "price_inr": 499,
        "demo_url": "https://github.com/example/studybuddy-demo",
        "readme_text": (
            "# StudyBuddy\n\nGenerate flashcards from plain-text lecture notes.\n\n"
            "## Setup\n1. python -m venv .venv\n2. pip install -r requirements.txt\n3. python seed.py\n"
            "4. uvicorn main:app --reload\n\nWorks offline. Needs Python 3.10 or newer. No tests, no licence yet.\n"
        ),
        "ai_score": 82,
        "ai_review": REVIEW_GOOD,
        "status": "published",
    },
    {
        "seller": "ananya@example.com",
        "title": "MessMate: hostel menu and mess bill splitter",
        "tagline": "Shows this week's mess menu and splits the monthly bill by how many meals each person ate.",
        "description": (
            "MessMate is a small web app for hostel messes. Students tick the meals they ate, and the app "
            "calculates each person's share of the monthly bill from the mess rate.\n\n"
            "It runs on Flask with SQLite and plain HTML templates. The bill maths sits in one module with "
            "the rates in a config file, so a different hostel can change the rate without touching the code."
        ),
        "tech_stack": ["Python", "Flask", "SQLite", "HTML", "Bootstrap"],
        "category": "web-app",
        "difficulty": "beginner",
        "what_you_get": [
            "Flask app with templates and CSS",
            "SQLite database with two weeks of sample meals",
            "README with the bill formula explained",
        ],
        "demo_points": [
            "Students tick meals for the week and the app saves each choice.",
            "The bill screen splits the month by meals actually eaten.",
            "Changing the mess rate in the config updates every bill.",
        ],
        "price_inr": 199,
        "demo_url": "https://github.com/example/messmate-demo",
        "readme_text": (
            "# MessMate\n\n## How to run\npython -m venv .venv && pip install -r requirements.txt\n"
            "flask --app app run\n\n## Bill formula\nbill = meals_eaten * rate_per_meal\n"
            "Rate is in config.py. Tested on Python 3.11. Licence: none yet.\n"
        ),
        "ai_score": 54,
        "ai_review": REVIEW_ROUGH,
        "status": "published",
    },
    {
        "seller": "rahul@example.com",
        "title": "Attendance Tracker with QR codes",
        "tagline": "Lecturer shows a QR code, students scan it, attendance lands in a spreadsheet.",
        "description": (
            "A replacement for calling out roll numbers. The lecturer opens a page that shows a QR code "
            "which changes every thirty seconds, so a student cannot share a screenshot after class.\n\n"
            "The scanner is a small mobile web page, so there is nothing to install. Attendance rows are "
            "written to SQLite and can be exported as CSV for the department."
        ),
        "tech_stack": ["Python", "FastAPI", "SQLite", "JavaScript", "qrcode"],
        "category": "web-app",
        "difficulty": "intermediate",
        "what_you_get": [
            "Backend with the rotating-token logic written out",
            "Mobile scan page",
            "CSV export script",
            "README with a local-network setup guide",
        ],
        "demo_points": [
            "The lecturer page shows a QR code that refreshes every thirty seconds.",
            "I scan it and my name appears in the attendance table.",
            "One click exports the whole class as a CSV for the department.",
        ],
        "price_inr": 749,
        "demo_url": "https://github.com/example/qr-attendance-demo",
        "readme_text": (
            "# QR Attendance\n\n## Setup\npip install -r requirements.txt\nuvicorn main:app --host 0.0.0.0\n\n"
            "Students open http://<lecturer-ip>:8000/scan on the campus network.\n"
            "Tested on Python 3.11 and Android Chrome. No licence file included.\n"
        ),
        "ai_score": 78,
        "ai_review": REVIEW_GOOD,
        "status": "published",
    },
    {
        "seller": "rahul@example.com",
        "title": "PlacementPulse: DSA tracker for placement season",
        "tagline": "Tracks which DSA topics you solved, your streak, and what to revise before an interview.",
        "description": (
            "PlacementPulse is a command-line tracker for placement preparation. You log a problem, its "
            "topic, and your confidence, and it prints what to revise today based on the last time you saw "
            "each topic.\n\n"
            "It stores everything in one CSV so the data stays yours, and the revision list is plain rules, "
            "not machine learning. There is a small report command that shows your weakest three topics."
        ),
        "tech_stack": ["Python", "pandas", "CSV", "Rich"],
        "category": "cli-tool",
        "difficulty": "beginner",
        "what_you_get": [
            "CLI source with docstrings on every command",
            "Two sample CSV logs from a real placement season",
            "README with example sessions",
        ],
        "demo_points": [
            "I log today's three problems in one command.",
            "The revise command lists the topics I have not touched in ten days.",
            "The report shows my three weakest topics before a mock interview.",
        ],
        "price_inr": 149,
        "demo_url": "https://github.com/example/placementpulse-demo",
        "readme_text": (
            "# PlacementPulse\n\npip install -r requirements.txt\npython pulse.py log --topic dp --level 2\n"
            "python pulse.py revise\n\nData lives in data/log.csv. Python 3.10+. MIT licence.\n"
        ),
        "ai_score": 88,
        "ai_review": {
            "score": 88,
            "summary": "The listing is honest and the setup is copy-pasteable. A sample report output in the README would make the value obvious at a glance.",
            "missing_items": ["no sample output in the README"],
            "risk_flags": [],
            "suggestions": ["Paste one report output under the example commands."],
        },
        "status": "published",
    },
    {
        "seller": "ananya@example.com",
        "title": "Campus Rideshare",
        "tagline": "Draft in progress: match students going home on the same weekend.",
        "description": "Draft listing. Not published yet.",
        "tech_stack": ["Node.js", "React"],
        "category": "web-app",
        "difficulty": "intermediate",
        "what_you_get": [],
        "demo_points": [],
        "price_inr": 0,
        "demo_url": "",
        "readme_text": "# Campus Rideshare\n\nWork in progress. Setup steps not written yet.\n",
        "ai_score": None,
        "ai_review": None,
        "status": "draft",
    },
]


def seed() -> None:
    create_db_and_tables()
    with Session(engine) as session:
        if session.exec(select(Project)).first() is not None:
            print("seed: projects already exist, nothing to do")
            return

        users: dict[str, User] = {}
        for email, name in SELLERS:
            user = session.exec(select(User).where(User.email == email)).first()
            if user is None:
                user = User(email=email, name=name, password_hash=auth.hash_password(DEMO_PASSWORD))
                session.add(user)
                session.commit()
                session.refresh(user)
            users[email] = user

        for row in PROJECTS:
            data = dict(row)
            seller_email = data.pop("seller")
            session.add(Project(seller_id=users[seller_email].id, **data))
        session.commit()

    print(f"seed: {len(SELLERS)} sellers, {len(PROJECTS)} projects")
    print(f"seed: login with any seller email above and password '{DEMO_PASSWORD}'")


if __name__ == "__main__":
    seed()
