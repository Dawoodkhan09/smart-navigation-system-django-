# Deploying to PythonAnywhere (free tier)

PythonAnywhere's free plan is a good fit here because its filesystem is
**persistent** — the SQLite database survives restarts/redeploys (unlike
most other free PaaS hosts, whose free tier disks are wiped on every
restart). Trade-offs on the free plan: your URL will be
`https://<yourusername>.pythonanywhere.com` (no custom domain), and
outbound requests from the server are restricted to a whitelist — but this
app never makes outbound calls (Leaflet/Bootstrap/fonts load from the
*browser*, not the server), so that restriction doesn't affect it.

## 1. Push this project to GitHub

PythonAnywhere pulls your code via `git clone` in its Bash console. If you
haven't already:

```bash
cd "D:\projects\new navigation\campus-navigation-django"
git init
git add .
git commit -m "Initial commit"
```

Create a new (public or private) repo on GitHub and push to it.

## 2. Sign up

Create a free account at **pythonanywhere.com** (choose the "Beginner" free
plan).

## 3. Open a Bash console and clone the repo

From the PythonAnywhere dashboard: **Consoles → Bash**, then:

```bash
git clone https://github.com/<your-username>/<your-repo>.git campus-navigation-django
cd campus-navigation-django
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_campus
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

## 4. Create the web app

**Web → Add a new web app** → choose **Manual configuration** (not the
Django wizard) → pick the Python version matching your venv (3.10).

## 5. Configure the WSGI file

Open the WSGI file link shown on the Web tab (something like
`/var/www/<yourusername>_pythonanywhere_com_wsgi.py`), delete its contents,
and replace with:

```python
import os
import sys

path = '/home/<yourusername>/campus-navigation-django'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'campus_navigation.settings'
os.environ['DJANGO_DEBUG'] = 'False'
os.environ['DJANGO_ALLOWED_HOSTS'] = '<yourusername>.pythonanywhere.com'
os.environ['DJANGO_CSRF_TRUSTED_ORIGINS'] = 'https://<yourusername>.pythonanywhere.com'
os.environ['DJANGO_SECRET_KEY'] = '<paste a long random string here>'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

Generate a secret key locally first if you want a real one:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

## 6. Point the Web tab at your virtualenv and static files

On the **Web** tab:

- **Virtualenv**: `/home/<yourusername>/campus-navigation-django/venv`
- **Static files** table: add an entry
  - URL: `/static/`
  - Directory: `/home/<yourusername>/campus-navigation-django/staticfiles`

## 7. Reload

Click the green **Reload** button on the Web tab. Your app is live at
`https://<yourusername>.pythonanywhere.com/`, admin at `/admin/`.

## Updating later

```bash
cd ~/campus-navigation-django
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

Then hit **Reload** on the Web tab again.
