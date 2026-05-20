# Travel Planner

---

**Table of Contents**
1. [Project Overview](#project-overview)
2. [Project Structure](#project-structure)
3. [Database Description](#database-description)
4. [API Description](#api-description)
5. [How to Run the Project](#how-to-run-the-project)
   - [Prerequisites](#1-prerequisites)
   - [Local Installation](#2-local-installation)
   - [Running with Docker](#3-running-with-docker)
6. [Running Tests](#running-tests)
7. [Technologies](#technologies)

---

## Project Overview

Travel Planner is a RESTful API for managing travel projects and places. It allows authenticated users to create travel projects, populate them with artworks from the [Art Institute of Chicago API](https://api.artic.edu/docs/), attach notes, and track visited places.

The workflow includes:
1. Obtain a JWT access token via `/api/auth/token/`
2. Create a travel project (optionally with places in one request)
3. Add, view, and update places within a project
4. Mark places as visited — the project is automatically marked as completed when all places are visited
5. Delete projects that have no visited places

---

## Project Structure

```text
travel-planner/
|-- config/                        # Django project configuration
|   |-- settings.py                # Project settings (env-driven)
|   |-- urls.py                    # Root URL configuration
|   |-- asgi.py
|   |-- wsgi.py
|   `-- __init__.py
|-- travel_planner/                # Main Django application
|   |-- migrations/                # Database migrations
|   |-- admin.py
|   |-- apps.py
|   |-- filters.py                 # django-filter FilterSets
|   |-- models.py                  # TravelProject and ProjectPlace models
|   |-- serializers.py             # DRF serializers
|   |-- services.py                # Art Institute of Chicago API client
|   |-- tests.py                   # Test suite (61 tests)
|   |-- urls.py                    # Application URL routes
|   `-- views.py                   # ViewSets
|-- Dockerfile
|-- docker-compose.yml
|-- entrypoint.sh                  # Docker entrypoint (migrate + runserver)
|-- manage.py
|-- requirements.txt
|-- .env.example                   # Environment variable template
`-- .gitignore
```

---

## Database Description

The project uses SQLite and includes two models:

- **TravelProject**
  - `name` — project name (required)
  - `description` — optional text description
  - `start_date` — optional trip start date
  - `is_completed` — auto-set to `true` when all places are visited

- **ProjectPlace**
  - `project` — FK to `TravelProject`
  - `external_id` — artwork ID from the Art Institute of Chicago API
  - `name` — artwork title (fetched and stored from the API)
  - `notes` — optional traveller notes
  - `is_visited` — marks whether the place has been visited

Relationships:
- One `TravelProject` → 1–10 `ProjectPlace` records
- `(project, external_id)` is unique — the same artwork cannot be added twice to the same project

---

## API Description

All endpoints require `Authorization: Bearer <access_token>`.
Interactive documentation is available at `/api/docs/` (Swagger UI) and `/api/redoc/`.

### Authentication

| Method | URL | Description |
|--------|-----|-------------|
| `POST` | `/api/auth/token/` | Obtain access + refresh tokens |
| `POST` | `/api/auth/token/refresh/` | Refresh access token |

### Travel Projects

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/projects/` | List all projects |
| `POST` | `/api/projects/` | Create a project (optional `place_ids` array) |
| `GET` | `/api/projects/{id}/` | Retrieve a single project |
| `PATCH` | `/api/projects/{id}/` | Update name, description, start_date |
| `DELETE` | `/api/projects/{id}/` | Delete project (blocked if any place is visited) |

**Filters:** `is_completed`, `start_date_after`, `start_date_before`, `search`, `ordering`

### Project Places

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/projects/{id}/places/` | List places for a project |
| `POST` | `/api/projects/{id}/places/` | Add a place (validated against ArtIC API) |
| `GET` | `/api/projects/{id}/places/{id}/` | Retrieve a single place |
| `PATCH` | `/api/projects/{id}/places/{id}/` | Update notes or mark as visited |

**Filters:** `is_visited`, `ordering`

---

## How to Run the Project

### 1. Prerequisites

- Python 3.13+ **or** Docker + Docker Compose
- Git

---

### 2. Local Installation

2.1. Clone the repository:

```bash
git clone https://github.com/mishagitcode/travel-planner
cd travel-planner
```

2.2. Create and activate a virtual environment:

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

2.3. Install dependencies:

```bash
pip install -r requirements.txt
```

2.4. Create a `.env` file from the template:

```bash
cp .env.example .env
```

Edit `.env` and set your secret key:

```env
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

2.5. Apply migrations:

```bash
python manage.py migrate
```

2.6. Create a superuser (to obtain JWT tokens via `/api/auth/token/`):

```bash
python manage.py createsuperuser
```

2.7. Start the development server:

```bash
python manage.py runserver
```

Open in browser:

```
http://127.0.0.1:8000/api/docs/
```

---

### 3. Running with Docker

3.1. Make sure Docker Desktop is running.

3.2. Create a `.env` file from the template:

```bash
cp .env.example .env
```

3.3. Build and start the container:

```bash
docker-compose up --build
```

The server will be available at:

```
http://localhost:8000/api/docs/
```

The SQLite database is persisted in a named Docker volume (`sqlite_data`) and survives container restarts.

3.4. Create a superuser inside the running container:

```bash
docker-compose exec web python manage.py createsuperuser
```

---

## Running Tests

```bash
python manage.py test travel_planner --verbosity=2
```

The test suite covers 61 cases including: model logic, JWT authentication, all CRUD endpoints, filters, pagination, business rule enforcement, and external API mocking.

---

## Technologies

- **Python 3.13** — core language
- **Django 6.0** — web framework
- **Django REST Framework** — API layer
- **djangorestframework-simplejwt** — JWT authentication
- **django-filter** — query filtering
- **drf-spectacular** — OpenAPI 3.0 schema + Swagger UI
- **SQLite** — default database
- **requests** — Art Institute of Chicago API client
- **Docker / Docker Compose** — containerised local setup
- **python-dotenv** — environment variable loading

---

Developed by [mishagitcode](https://github.com/mishagitcode)
