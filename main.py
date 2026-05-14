import tkinter as tk
from auth import keyauth_app, KeyAuthError, load_license_key, clear_license_key
from app import start_app, show_login

if __name__ == "__main__":
    root = tk.Tk()
    saved_key = load_license_key()
    if saved_key:
        try:
            if keyauth_app.license(saved_key):
                start_app(root)
            else:
                clear_license_key()
                show_login(root)
        except KeyAuthError:
            clear_license_key()
            show_login(root)
    else:
        show_login(root)
    root.mainloop()
