# Running Ghar Ko Swad with Django

The site is connected to Django. Orders are saved in the database and shown in **My Orders**.

## Setup

1. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   venv\Scripts\activate    # Windows
   # or: source venv/bin/activate   # Mac/Linux
   ```

2. **Install Django:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

4. **Create a superuser (optional, for admin):**
   ```bash
   python manage.py createsuperuser
   ```

5. **Start the server:**
   ```bash
   python manage.py runserver
   ```

6. Open **http://127.0.0.1:8000/** in your browser.

## URLs

- **/** – Home
- **/order/** – Place order (form posts to Django, saves to DB)
- **/order/confirmation/<id>/** – Order confirmed (from DB)
- **/my-orders/** – Customer dashboard (orders from database)
- **/login/**, **/register/**, **/contact/**, **/chefs/**, **/food/**, **/chef-dashboard/** – Other pages
- **/admin/** – Django admin (after `createsuperuser`)

## Static files

`premium.css` and other files in the project folder are served at `/static/` when `DEBUG=True`.
