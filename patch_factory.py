with open('core/scrapers/factory.py', 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace(
    "elif 'elftoon.com' in url_lower or 'elftoon' in url_lower:",
    "elif 'blackoutcomics.com' in url_lower or 'blackoutcomics' in url_lower:\n        return BlackoutComicsScraper()\n    elif 'elftoon.com' in url_lower or 'elftoon' in url_lower:"
)

with open('core/scrapers/factory.py', 'w', encoding='utf-8') as f:
    f.write(code)
