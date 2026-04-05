# Receiving Contact Form Emails

By default, contact form submissions are **saved in the database** (view in Django admin) but emails are only **printed in the terminal** where you run `python manage.py runserver` — they are not sent to your inbox.

To **receive contact form emails in your Gmail inbox**:

## 1. Turn on 2-Step Verification

- Go to [Google Account → Security](https://myaccount.google.com/security)
- Under "How you sign in to Google", turn on **2-Step Verification**

## 2. Create a Gmail App Password

- In Security, open **App passwords** (or search "App passwords" in your Google account)
- Select app: **Mail**, device: **Windows Computer** (or Other)
- Click **Generate**
- Copy the **16-character password** (no spaces)

## 3. Set the environment variable and run the server

**Windows (PowerShell):**

```powershell
$env:EMAIL_HOST_USER = "rauniyarbizzay@gmail.com"
$env:EMAIL_HOST_PASSWORD = "your-16-char-app-password"
python manage.py runserver
```

**Windows (Command Prompt):**

```cmd
set EMAIL_HOST_USER=rauniyarbizzay@gmail.com
set EMAIL_HOST_PASSWORD=your-16-char-app-password
python manage.py runserver
```

Replace `your-16-char-app-password` with the app password from step 2.

After this, when someone submits the Contact form, the email will be sent to **rauniyarbizzay@gmail.com** (or the address in `CONTACT_EMAIL_TO` if you set it).

---

**Note:** All submissions are always saved in the database. You can view them in Django admin under **Contact messages** even when email is not configured.
