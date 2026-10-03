import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# A reasonably broad skills vocabulary for a student project.
# Extend this list as needed for your target job domains.
SKILL_KEYWORDS = [
    "python", "java", "c++", "c#", "javascript", "typescript", "sql", "nosql",
    "html", "css", "react", "angular", "vue", "node.js", "express", "django",
    "flask", "fastapi", "spring", "docker", "kubernetes", "aws", "azure",
    "gcp", "git", "linux", "machine learning", "deep learning", "nlp",
    "tensorflow", "pytorch", "pandas", "numpy", "scikit-learn", "tableau",
    "power bi", "excel", "rest api", "graphql", "mongodb", "postgresql",
    "mysql", "redis", "ci/cd", "agile", "scrum", "data structures",
    "algorithms", "communication", "leadership", "project management",
]


def _clean_text(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9+#./\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compute_match_score(resume_text, job_text):
    """
    Returns a 0-100 similarity score between resume and job description
    using TF-IDF vectorization + cosine similarity.
    """
    resume_clean = _clean_text(resume_text)
    job_clean = _clean_text(job_text)

    if not resume_clean or not job_clean:
        return 0.0

    try:
        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf_matrix = vectorizer.fit_transform([resume_clean, job_clean])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return round(float(similarity) * 100, 2)
    except ValueError:
        # Happens if vocabulary is empty after stopword removal
        return 0.0


def skill_gap_analysis(resume_text, job_text):
    """
    Returns (matched_skills, missing_skills) by checking which known
    SKILL_KEYWORDS appear in the job text vs. the resume text.
    """
    resume_clean = _clean_text(resume_text)
    job_clean = _clean_text(job_text)

    required_skills = [
        skill for skill in SKILL_KEYWORDS if skill in job_clean
    ]

    matched = [skill for skill in required_skills if skill in resume_clean]
    missing = [skill for skill in required_skills if skill not in resume_clean]

    return matched, missing