import os

# Configuração para evitar erro do Playwright no executável (PyInstaller)
# Forçamos o caminho dos navegadores para a pasta local do usuário
_pw_path = os.path.join(os.getenv("LOCALAPPDATA", os.path.expanduser("~")), "ReadStitch", "playwright-browsers")
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = _pw_path

import multiprocessing

import sys
from console.launcher import launch

if __name__ == '__main__':
    # Required for multiprocessing on Windows
    multiprocessing.freeze_support()

    # Intercept waifu2x_cpu invocations if called as Python replacement
    for idx, arg in enumerate(sys.argv):
        if "waifu2x_cpu" in arg:
            from scripts.waifu2x_cpu import main as waifu_cpu_main
            sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
            waifu_cpu_main()
            raise SystemExit(0)

    launch()
