"""Learning roadmap generation (deterministic). Hours are estimates, resources are
official-documentation homepages from the taxonomy, never invented URLs."""
from __future__ import annotations

from .skills.taxonomy import Taxonomy

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

EXPLAIN = {
    "Python": "A general-purpose programming language that reads almost like English. It is the main language for AI, data work and many back ends.",
    "SQL": "The language used to ask questions of a database: find, add, change and combine rows of data.",
    "Git": "A tool that saves the history of your code so you can undo mistakes and work with others.",
    "Docker": "Packs an app and everything it needs into a container so it runs the same on any computer.",
    "Kubernetes": "Runs and manages many containers across many machines. Learn Docker first.",
    "Machine Learning": "Teaching programs to find patterns in data and make predictions instead of writing every rule by hand.",
    "Deep Learning": "Machine learning with many-layered neural networks, used for images, speech and language.",
    "React": "A JavaScript library for building user interfaces out of small reusable components.",
    "REST APIs": "A common way for programs to talk over the web using URLs and HTTP methods such as GET and POST.",
    "RAG": "Retrieval-augmented generation: look up relevant documents first, then give them to a language model so its answer is grounded in them.",
    "Large Language Models": "AI models trained on huge amounts of text that can write, summarise and answer questions.",
    "Natural Language Processing": "Teaching computers to work with human language: classify, search, translate and summarise text.",
    "FastAPI": "A modern Python framework for building web APIs quickly, with automatic documentation.",
    "PostgreSQL": "A powerful free relational database that stores data in tables.",
    "Data Structures": "Ways of organising data (lists, trees, hash maps) so programs run fast and stay simple.",
    "CI/CD": "Automatically testing and deploying your code every time you push a change.",
}
CATEGORY_EXPLAIN = {
    "programming_language": "A programming language: a way to give instructions to a computer.",
    "framework": "A ready-made toolkit that handles common parts of building an application so you write less code.",
    "database": "Software that stores data safely and lets you search and update it efficiently.",
    "ai_ml": "A technique or tool for building systems that learn from data.",
    "genai_nlp": "A tool or technique for working with language models and text.",
    "cloud_devops": "A tool or practice for running, deploying and maintaining software reliably.",
    "tools": "A tool developers use every day to build, track or share their work.",
    "data": "A tool or technique for cleaning, analysing and presenting data.",
    "concept": "A core engineering idea that shows up in many projects and interviews at work.",
    "soft_skill": "A working skill shown through how you collaborate and explain your work.",
}
EXERCISES = {
    "programming_language": ["Finish the official beginner tutorial and type out every example.", "Solve 10 small problems (strings, lists, loops) without looking at solutions.", "Write a small command-line tool that solves a problem you have."],
    "framework": ["Follow the official getting-started guide end to end.", "Rebuild the tutorial app from memory with one change of your own.", "Add tests and one feature (for example search or login)."],
    "database": ["Install it locally and create two related tables.", "Write 10 queries: filter, sort, join, group.", "Connect it to a small app and add, read, update and delete records."],
    "ai_ml": ["Work through the official beginner tutorial.", "Train a model on a small public dataset and record its accuracy.", "Write down in plain words where your model fails and why."],
    "genai_nlp": ["Run a small open-source model locally and send it 10 different prompts.", "Build a script that sends text to the model and checks the answer's format.", "Note three cases where the output was wrong and how you would detect them."],
    "cloud_devops": ["Follow the official quick-start and deploy a hello-world.", "Write down every command you used so you can repeat it.", "Break something on purpose and practise fixing it."],
    "tools": ["Read the official getting-started page.", "Use it daily for one week in a real project.", "Write a one-page cheat sheet in your own words."],
    "data": ["Load a public dataset and describe it (size, missing values, ranges).", "Answer 5 questions about the data with code or formulas.", "Make 3 clear charts and write one sentence of insight each."],
    "concept": ["Read an introductory chapter or the official guide.", "Implement a small example from scratch.", "Explain the idea out loud in two minutes without notes."],
    "soft_skill": ["Write a short STAR-style account (Situation, Task, Action, Result) of a real moment where you used it.", "Ask a friend or mentor for feedback on one example.", "Add one honest, specific bullet about it to your resume."],
}
PROJECTS = {
    "programming_language": "Build a small tool in {s} (a to-do CLI, expense tracker or text analyser) and publish it on GitHub with a README.",
    "framework": "Build a small app with {s} that has login, a database and 3 pages, and deploy it on a free tier.",
    "database": "Design the database for a library or expense app using {s}, with at least 4 related tables and 10 documented queries.",
    "ai_ml": "Train and evaluate a model using {s} on a public dataset, and write a short report on accuracy and limitations.",
    "genai_nlp": "Build a small document Q&A tool using {s} that answers only from your own notes and shows its sources.",
    "cloud_devops": "Containerise or deploy one of your existing projects using {s} and document the steps.",
    "tools": "Use {s} on your next project and describe in the README how it improved your workflow.",
    "data": "Analyse a public dataset with {s} and publish a short notebook or dashboard with 3 findings.",
    "concept": "Refactor one of your existing projects to apply {s} and describe the before and after.",
    "soft_skill": "Write a case study of a team project: your role, a problem you solved, and what you learned.",
}


def build_roadmap(priorities: list[dict], items: list[dict], taxonomy: Taxonomy, max_items: int = 15) -> list[dict]:
    """priorities: from comparison['priorities']; items: comparison['items'] (to add 'strengthen evidence' tasks)."""
    chosen: list[dict] = list(priorities)
    have = {p["skill"] for p in chosen}
    for i in items:
        if i["status"] == "listed" and i["level"] == "required" and i["skill"] not in have:
            chosen.append({"skill": i["skill"], "priority": "medium",
                           "why": "Required by the posting. It is listed in your skills but not yet shown in a project or experience."})
    chosen.sort(key=lambda p: PRIORITY_ORDER[p["priority"]])
    chosen = chosen[:max_items]
    names = [c["skill"] for c in chosen]
    out: list[dict] = []
    for p in chosen:
        sk = taxonomy.get(p["skill"])
        cat = sk.category if sk else "concept"
        lo, hi = (sk.effort_hours if sk else (10, 20))
        prereqs = [x for x in (sk.prerequisites if sk else [])]
        res = []
        if sk and sk.resource_url:
            res.append({"title": f"{p['skill']} official documentation / learning home", "url": sk.resource_url,
                        "note": "Official source. Check that the link is still current before relying on it."})
        else:
            res.append({"title": f"Search the official documentation for {p['skill']}", "url": None,
                        "note": "No verified link is stored for this skill; prefer the official site or a university course."})
        out.append({
            "skill": p["skill"], "category": cat, "priority": p["priority"], "why": p["why"],
            "prerequisites": prereqs,
            "explanation": EXPLAIN.get(p["skill"], CATEGORY_EXPLAIN.get(cat, "")),
            "exercises": [e for e in EXERCISES.get(cat, EXERCISES["concept"])],
            "project_idea": PROJECTS.get(cat, PROJECTS["concept"]).format(s=p["skill"]),
            "estimated_hours_min": lo, "estimated_hours_max": hi,
            "effort_note": "Rough estimate for a beginner; your pace will differ.",
            "resources": res,
            "status": "not_started",
            "learn_after": [n for n in prereqs if n in names],
        })
    # Put skills that others depend on before their dependants, keeping priority order otherwise
    placed: list[dict] = []
    pending = list(out)
    while pending:
        for it in list(pending):
            if all(d in {x["skill"] for x in placed} for d in it["learn_after"]):
                placed.append(it); pending.remove(it); break
        else:
            placed.extend(pending); break
    return placed
