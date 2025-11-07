# 🎓 EduTrack — Project Setup Guide

## 🧰 Prerequisites

Before you start, ensure you have the following installed:

* **Python** (latest stable version)
* **pip** (Python package manager)
* **Git** (for version control)
* **Virtual environment** module (`venv`)

> ⚠️ Commands may slightly vary on **macOS** or **Linux** — adjust accordingly.

---

## 🚀 Backend Setup (Django)

### 1. Clone the repository

```bash
git clone https://github.com/your-username/edutrack.git
cd edutrack
```

### 2. Create a virtual environment

```bash
py -m venv venv
```

or (depending on your OS)

```bash
python3 -m venv venv
```

### 3. Activate the virtual environment

* **Windows:**

  ```bash
  venv\Scripts\activate
  ```
* **macOS/Linux:**

  ```bash
  source venv/bin/activate
  ```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the development server

Navigate into the Django project folder (for example `edutrack/`) and run:

```bash
cd edutrack
py manage.py runserver
```

or

```bash
python manage.py runserver
```

Your backend should now be running at:
👉 [http://localhost:8000/](http://localhost:8000/)

---

## 🖥️ Frontend Developers — Important Note

* Ensure the **backend server** is running before testing frontend integration.
* You can visit **[http://localhost:8000/](http://localhost:8000/)** to view available API endpoints.
* Use **Postman** or any API client to test the endpoints — API documentation will guide you on usage and available routes.

---

## 🗂️ Django Project Structure

A typical Django project structure looks like this:

```
edutrack/
├── manage.py
├── requirements.txt
├── venv/
├── edutrack/                # Main project folder (settings, URLs, WSGI/ASGI)
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│
├── apps/                    # (optional) folder for all Django apps
│   ├── accounts/
│   │   ├── admin.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── ...
│   ├── scholarships/
│   └── ...
│
├── static/                  # CSS, JS, images
├── templates/               # HTML templates
└── README.md
```

---

## 🪄 Contribution Guidelines

* **Never push directly** to the `main` branch.
* Create a **separate branch** for your changes:

  ```bash
  git checkout -b your-branch-name
  ```
* After making changes, **commit and push** your branch:

  ```bash
  git add .
  git commit -m "Your message"
  git push origin your-branch-name
  ```
* Create a **Pull Request (PR)** on GitHub for review and merge.

---

## 🧩 Notes

* Always **pull the latest changes** from the main branch before starting new work:

  ```bash
  git pull origin main
  ```
* Keep your **virtual environment** activated while running or developing the project.
* If any module is missing, add it to `requirements.txt` and inform the team.
