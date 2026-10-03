AI Recruitment Portal

A web app I built with Flask and SQLite where candidates upload their resumes and recruiters review the applicants. The portal reads each resume, scores it against the job, and shows which skills the candidate is missing.

What it does
Candidates and recruiters log in with separate accounts
Candidates upload resumes in PDF, DOCX or TXT format
Resume text is extracted automatically from each file
Each candidate is scored against the job requirements
Skill-gap analysis shows which required skills are missing from a resume
Recruiters can view all applicants in one place
Passwords are hashed, so they are never stored as plain text
How the scoring works

[Write 2-3 sentences here. For example: the job's required skills are compared with the skills found in the resume text, and the score is the percentage of required skills that match. Replace this with what your code actually does.]

Built with

Python, Flask, SQLite, HTML

[Add any other libraries you used for reading files, for example PyPDF2, python-docx or scikit-learn.]

Files
app.py is the main Flask app
[database file].db is the SQLite database
templates/ has the HTML pages
uploads/ stores the uploaded resumes

[Edit this list to match your repo.]

Run it yourself
pip install -r requirements.txt
python app.py

Then open http://127.0.0.1:5000 in your browser.

Screenshots

[Add 2-3 screenshots here: the login page, the candidate upload page, and the recruiter view with scores. Upload them to the repo and link them like this: ![Recruiter view](screenshots/recruiter.png)]

What I learned

How to handle file uploads in Flask, how to pull text out of PDF and DOCX files, how to store passwords safely with hashing, and how to turn resume text into a score.

Next steps
Better scoring using NLP
Export applicant lists to a file
Email notifications to candidates
Better page design

Made by Adithyatejas B Tejas
