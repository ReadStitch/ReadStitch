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
    if app.startswith("internal:"):
        return app
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

        # If configured for the internal CPU engine or pointing to waifu2x_cpu, run in-process directly
        if (
            postprocess_app.startswith("internal:")
            or "waifu2x_cpu" in postprocess_app.lower()
            or "waifu2x_cpu" in postprocess_args.lower()
        ):
            return self._run_internal_waifu(
                input_path=workdirectory.output_path,
                output_path=workdirectory.postprocess_path,
                postprocess_args=postprocess_args,
                console_func=console_func,
            )

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

    def _run_internal_waifu(
        self,
        input_path: str,
        output_path: str,
        postprocess_args: str,
        console_func: Callable[[str], None],
    ) -> None:
        """Run native ONNX Runtime CPU engine in-process without spawning subprocesses."""
        console_func("\n[Waifu2X] Executando motor interno CPU (ONNX Runtime)...\n")
        try:
            from scripts.waifu2x_cpu import Waifu2xCpuEngine, ensure_model, process_path
        except Exception as e:
            console_func(f"[ERRO] Falha ao importar motor Waifu2X CPU: {e}\n")
            raise

        output_format = "jpg"
        parts = postprocess_args.split()
        for i, p in enumerate(parts):
            if p in ("-f", "--format") and i + 1 < len(parts):
                output_format = parts[i + 1]

        model_path = ensure_model(log_func=console_func)
        engine = Waifu2xCpuEngine(model_path)
        process_path(
            engine=engine,
            input_path=input_path,
            output_path=output_path,
            output_format=output_format,
            log_func=console_func,
        )
        console_func("Post process finished successfully!\n")

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
            # If so, try falling back to CPU engine (ONNX Runtime) or CPU executable.
            is_upscaler = any(any(x in part.lower() for x in ["waifu2x", "realesrgan", "esrgan"]) for part in command)
            if is_upscaler:
                exe_path = command[0]
                dir_name = os.path.dirname(exe_path)
                cpu_exe_name = "waifu2x-ncnn-cpu.exe"
                cpu_exe_path = os.path.join(dir_name, cpu_exe_name) if dir_name else shutil.which(cpu_exe_name)

                if "vulkan" in os.path.basename(exe_path).lower() and cpu_exe_path and os.path.isfile(cpu_exe_path):
                    console_func(
                        f"\n[Aviso] Falha de GPU/Vulkan detectada (código {return_code}). "
                        f"Alternando automaticamente para o executável CPU ({cpu_exe_name})...\n"
                    )
                    clean_args = []
                    skip_next = False
                    for arg in command[1:]:
                        if skip_next:
                            skip_next = False
                            continue
                        if arg == "-g":
                            skip_next = True
                            continue
                        if arg.startswith("-g"):
                            continue
                        clean_args.append(arg)

                    cpu_command = [cpu_exe_path, *clean_args]
                    return self._execute(processed_path, cpu_command, console_func)

                # Fallback to internal ONNX CPU engine
                console_func(
                    f"\n[Aviso] Falha de GPU/Vulkan detectada (código {return_code}). "
                    "Alternando automaticamente para o motor CPU nativo (ONNX Runtime)...\n"
                )
                in_path = None
                out_path = processed_path
                for idx, c in enumerate(command):
                    if c == "-i" and idx + 1 < len(command):
                        in_path = command[idx + 1]
                    elif c == "-o" and idx + 1 < len(command):
                        out_path = command[idx + 1]

                if in_path:
                    fmt = "jpg"
                    for idx, c in enumerate(command):
                        if c in ("-f", "--format") and idx + 1 < len(command):
                            fmt = command[idx + 1]
                    return self._run_internal_waifu(
                        input_path=in_path,
                        output_path=out_path,
                        postprocess_args=f"-f {fmt}",
                        console_func=console_func,
                    )

            raise subprocess.CalledProcessError(return_code, command)
