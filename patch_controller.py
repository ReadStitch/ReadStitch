import re

with open('gui/controller.py', 'r', encoding='utf-8') as f:
    code = f.read()

# patch on_login_site_changed
code = code.replace(
    'elif text == "Comikey":\n            _main_window.loginEmailInput.setText(_settings.load("comikey_email"))\n            _main_window.loginPassInput.setText(_settings.load("comikey_password"))',
    'elif text == "Comikey":\n            _main_window.loginEmailInput.setText(_settings.load("comikey_email"))\n            _main_window.loginPassInput.setText(_settings.load("comikey_password"))\n        elif text == "Blackout Comics":\n            _main_window.loginEmailInput.setText(_settings.load("blackout_email"))\n            _main_window.loginPassInput.setText(_settings.load("blackout_password"))'
)

# patch on_login_email_changed
code = code.replace(
    'elif site == "Comikey":\n            _settings.save("comikey_email", text)',
    'elif site == "Comikey":\n            _settings.save("comikey_email", text)\n        elif site == "Blackout Comics":\n            _settings.save("blackout_email", text)'
)

# patch on_login_pass_changed
code = code.replace(
    'elif site == "Comikey":\n            _settings.save("comikey_password", text)',
    'elif site == "Comikey":\n            _settings.save("comikey_password", text)\n        elif site == "Blackout Comics":\n            _settings.save("blackout_password", text)'
)

with open('gui/controller.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Patched!")
