"""Post-process runner for external applications."""
import os
import shlex
import shutil
import subprocess
from typing import Callable

from core.models.work_directory import WorkDirectory
from core.services.global_logger import logFunc


def _find_executable(app: str) -> str | None:
    """Find executable path, returns None if not found."""
    if not app:
        return None
    # Check if it's an absolute path that exists
    if os.path.isabs(app) and os.path.isfile(app):
        return app
    # Use shutil.which to find in PATH
    return shutil.which(app)


def _build_popen_kwargs() -> dict:
    """Return platform-specific kwargs to suppress console windows on Windows."""
    if os.name != "nt":
        return {}
    kwargs: dict = {}
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if creationflags:
        kwargs["creationflags"] = creationflags
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    kwargs["startupinfo"] = startupinfo
    return kwargs


class PostProcessRunner:
    """Executes external post-processing applications on output directories."""

    def run(
        self,
        workdirectory: WorkDirectory,
        *,
        postprocess_app: str = "",
        postprocess_args: str = "",
        console_func: Callable[[str], None] = print,
    ) -> None:
        if not postprocess_app:
            raise ValueError("Post process application is required but not configured.")

        # Validate executable exists before attempting to run
        executable_path = _find_executable(postprocess_app)
        if executable_path is None:
            raise FileNotFoundError(
                f"Post process application '{postprocess_app}' not found in system PATH or as absolute path. "
                f"Please verify the application is installed and accessible."
            )

        try:
            extra_args = shlex.split(postprocess_args, posix=False)
        except ValueError:
            extra_args = [postprocess_args] if postprocess_args else []

        token_map = {
            "[stitched]": workdirectory.output_path,
            "[processed]": workdirectory.postprocess_path,
        }

        resolved_args: list[str] = []
        for token in extra_args:
            if len(token) >= 2 and token[0] == token[-1] == '"':
                token = token[1:-1]
            resolved_args.append(token_map.get(token, token))

        command = [executable_path, *resolved_args]
        console_func(f"Executing post process: {' '.join(command)}\n")

        return self._execute(workdirectory.postprocess_path, command, console_func)

    @logFunc(inclass=True)
    def _execute(
        self,
        processed_path: str,
        command: list[str],
        console_func: Callable[[str], None],
    ) -> None:
        os.makedirs(processed_path, exist_ok=True)

        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
            universal_newlines=True,
            shell=False,
            **_build_popen_kwargs(),
        )
        console_func("Post process started!\n")
        stdout_pipe = proc.stdout
        if stdout_pipe is not None:
            for line in stdout_pipe:
                console_func(line)
        console_func("\nPost process finished successfully!\n")
        if stdout_pipe is not None:
            stdout_pipe.close()
        return_code = proc.wait()
        if return_code:
            # Check if upscaler failed due to Vulkan/GPU driver issues (often exit code 3221225477 or 4294967295)
            # If so, try falling back to CPU mode using '-g -1' if not already specified.
            is_upscaler = any(any(x in part.lower() for x in ["waifu2x", "realesrgan", "esrgan"]) for part in command)
            has_cpu_flag = "-g" in command or any(part.startswith("-g") for part in command)
            
            if is_upscaler and not has_cpu_flag:
                console_func("\n[Aviso] Falha de GPU/Vulkan detectada (código {}). Tentando novamente em modo CPU...\n".format(return_code))
                cpu_command = list(command)
                cpu_command.extend(["-g", "-1"])
                proc_cpu = subprocess.Popen(
                    cpu_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    encoding="utf-8",
                    errors="replace",
                    universal_newlines=True,
                    shell=False,
                    **_build_popen_kwargs(),
                )
                stdout_pipe_cpu = proc_cpu.stdout
                if stdout_pipe_cpu is not None:
                    for line in stdout_pipe_cpu:
                        console_func(line)
                    stdout_pipe_cpu.close()
                return_code_cpu = proc_cpu.wait()
                if not return_code_cpu:
                    console_func("\nPost process finished successfully using CPU!\n")
                    return
            raise subprocess.CalledProcessError(return_code, command)
