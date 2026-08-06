import os

# Configuração para evitar erro do Playwright no executável (PyInstaller)
# Forçamos o caminho dos navegadores para a pasta local do usuário
_pw_path = os.path.join(os.getenv("LOCALAPPDATA", os.path.expanduser("~")), "ReadStitch", "playwright-browsers")
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = _pw_path

import multiprocessing

from console.launcher import launch

if __name__ == '__main__':
    # Required for multiprocessing on Windows
    multiprocessing.freeze_support()
    launch()
