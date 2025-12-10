🎓 EduTrack — Project Setup Guide
🧰 Prerequisites
Before you start, ensure you have the following installed:
 * Python (latest stable version)
 * pip (Python package manager)
 * Git (for version control)
 * Docker Desktop (for running Redis)
 * Virtual environment module (venv)
> ⚠️ Commands may slightly vary on macOS or Linux — adjust accordingly.
> 
🐳 Redis Setup (Using Docker)
We use Redis as a message broker for Celery background tasks. The easiest way to run it is via Docker.
 * Ensure Docker is running on your machine.
 * Pull and run the Redis container:
   docker run -d --name edutrack-redis -p 6379:6379 redis

 * Verify it's running:
   docker ps

🚀 Backend Setup (Django)
1. Clone the repository
git clone https://github.com/your-username/edutrack.git
cd edutrack

2. Create a virtual environment
py -m venv venv

or (depending on your OS)
python3 -m venv venv

3. Activate the virtual environment
 * Windows:
   venv\Scripts\activate

 * macOS/Linux:
   source venv/bin/activate

4. Install dependencies
pip install -r requirements.txt

5. Run Database Migrations
python manage.py migrate

6. Run the development server
Navigate into the Django project folder (e.g., edutrack/) and run:
python manage.py runserver

Your backend should now be running at:
👉 http://localhost:8000/
⚡ Celery Background Tasks
To process background jobs (like AI verification, scraping, emails), you need to run a Celery worker. Make sure Redis is running before starting Celery.
Open a new terminal window, activate your virtual environment, and run the command for your OS:
Windows
Windows does not natively support process forking, so we use the solo pool or eventlet.
celery -A edutrack worker --loglevel=info --pool=solo

Linux / macOS
celery -A edutrack worker --loglevel=info

> Note: Replace edutrack with the actual name of your project folder containing celery.py if it differs.
> 
🖥️ Frontend Developers — Important Note
 * Ensure the backend server AND Redis/Celery are running before testing features that require background processing.
 * You can visit http://localhost:8000/ to view available API endpoints.
 * Use Postman or any API client to test the endpoints.
🗂️ Django Project Structure
A typical Django project structure looks like this:
edutrack/
├── manage.py
├── requirements.txt
├── venv/
├── edutrack/                # Main project config
│   ├── __init__.py
│   ├── celery.py            # Celery Configuration
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│
├── apps/                    # Folder for all Django apps
│   ├── accounts/
│   ├── achievements/
│   └── ...
│
├── static/                  # CSS, JS, images
├── templates/               # HTML templates
└── README.md

👥 Meet the Team
| Name | Role |
|---|---|
| K. Naga Ruthvik | Backend Developer |
| D. Anvesh | Frontend Developer |
| Nandini | Full Stack Developer |
| Bharath Sai | AI Developer |
| Priya Chandana | Mobile Application Developer |
| Kaarthika | Presentation & Documentation |
🪄 Contribution Guidelines
 * Never push directly to the main branch.
 * Create a separate branch for your changes:
   git checkout -b your-branch-name

 * After making changes, commit and push your branch:
   git add .
git commit -m "Your message"
git push origin your-branch-name

 * Create a Pull Request (PR) on GitHub for review and merge.
🧩 Notes
 * Always pull the latest changes from the main branch before starting new work:
   git pull origin main

 * Keep your virtual environment activated while running or developing the project.
 * If any module is missing, add it to requirements.txt and inform the team.
