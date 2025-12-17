import logging
import sys
from pathlib import Path
from typing import Literal, TextIO

import anyio
import anyio.lowlevel
from anyio.abc import Process
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from anyio.streams.text import TextReceiveStream
from pydantic import BaseModel, Field

import exp.types as types
from exp.os.posix.utilities import terminate_posix_process_tree
from exp.os.win32.utilities import (
    FallbackProcess,
    create_windows_process,
    get_windows_executable_command,
    terminate_windows_process_tree,
)
from exp.shared.message import SessionMessage

logger = logging.getLogger(__name__)


# Timeout for process termination before falling back to force kill
PROCESS_TERMINATION_TIMEOUT = 2.0


class StdioParameters(BaseModel):
    command: str
    """The executable to run to start the server."""

    args: list[str] = Field(default_factory=list)
    """Command line arguments to pass to the executable."""

    cwd: str | Path | None = None
    """The working directory to use when spawning the process."""

    encoding: str = "utf-8"
    """
    The text encoding used when sending/receiving messages to the server

    defaults to utf-8
    """

    encoding_error_handler: Literal["strict", "ignore", "replace"] = "strict"
    """
    The text encoding error handler.

    See https://docs.python.org/3/library/codecs.html#codec-base-classes for
    explanations of possible values
    """


class StdioClient:
    """Stdio transport protocol for MCP."""

    def __init__(
            self,
            server: StdioParameters):
        self.read_stream_writer, self.read_stream = anyio.create_memory_object_stream(
            0)
        self.write_stream, self.write_stream_reader = anyio.create_memory_object_stream(
            0)
        self._process = None
        self.errlog: TextIO = sys.stderr
        self.is_started = False
        self.server = server

    async def start(self) -> tuple[
        MemoryObjectReceiveStream[SessionMessage | Exception],
        MemoryObjectSendStream[SessionMessage]
    ]:
        """Start the stdio transport."""

        try:
            command = _get_executable_command(self.server.command)
            if self._process:
                raise RuntimeError("Stdio transport already started")

            # Open process with stderr piped for capture
            self._process = await _create_platform_compatible_process(
                command=command,
                args=self.server.args,
                errlog=self.errlog,
                cwd=self.server.cwd,
            )

        except OSError:
            self._process = None
            # Clean up streams if process creation fails
            await self.read_stream.aclose()
            await self.write_stream.aclose()
            await self.read_stream_writer.aclose()
            await self.write_stream_reader.aclose()
            raise

        task_group = anyio.create_task_group()
        self.task_group = task_group  # just written
        await task_group.__aenter__()
        task_group.start_soon(self.stdout_reader)
        task_group.start_soon(self.stdin_writer)
        self.is_started = True

        return self.read_stream, self.write_stream

    def get_streams(self):
        """Get the read and write streams for the transport."""
        if self._process is None:
            raise RuntimeError("Stdio transport not started")
        return self.read_stream, self.write_stream

    async def stop(self):

        if self._process is None:
            raise RuntimeError("Stdio transport not started")

        if self.task_group:
            self.task_group.cancel_scope.cancel()
            await self.task_group.__aexit__(None, None, None)
            # await self.task_group.__aexit__(None, None, None)  # just written

        if self._process.stdin:  # pragma: no branch
            try:
                await self._process.stdin.aclose()
            except Exception:  # pragma: no cover
                # stdin might already be closed, which is fine
                pass

        try:
            # Give the process time to exit gracefully after stdin closes
            with anyio.fail_after(PROCESS_TERMINATION_TIMEOUT):
                await self._process.wait()
        except TimeoutError:
            # Process didn't exit from stdin closure, use platform-specific termination
            # which handles SIGTERM -> SIGKILL escalation
            await _terminate_process_tree(self._process)
        except ProcessLookupError:  # pragma: no cover
            # Process already exited, which is fine
            pass

        await self.read_stream.aclose()
        await self.write_stream.aclose()
        await self.read_stream_writer.aclose()
        await self.write_stream_reader.aclose()
        self.is_started = False

    async def stdout_reader(self):
        assert self._process.stdout, "Opened process is missing stdout"

        try:
            async with self.read_stream_writer:
                buffer = ""
                async for chunk in TextReceiveStream(
                    self._process.stdout,
                    encoding=self.server.encoding,
                    errors=self.server.encoding_error_handler,
                ):
                    lines = (buffer + chunk).split("\n")
                    buffer = lines.pop()

                    for line in lines:
                        try:
                            print('message got from server:', line)
                            message = types.JSONRPCMessage.model_validate_json(
                                line)
                        except Exception as exc:  # pragma: no cover
                            logger.exception(
                                "Failed to parse JSONRPC message from server")
                            await self.read_stream_writer.send(exc)
                            continue

                        session_message = SessionMessage(message)
                        await self.read_stream_writer.send(session_message)
        except anyio.ClosedResourceError:  # pragma: no cover
            await anyio.lowlevel.checkpoint()

    async def stdin_writer(self):
        assert self._process.stdin, "Opened process is missing stdin"

        try:
            async with self.write_stream_reader:
                async for session_message in self.write_stream_reader:
                    json = session_message.message.model_dump_json(
                        by_alias=True, exclude_none=True)
                    await self._process.stdin.send(
                        (json + "\n").encode(
                            encoding=self.server.encoding,
                            errors=self.server.encoding_error_handler,
                        )
                    )
        except anyio.ClosedResourceError:  # pragma: no cover
            await anyio.lowlevel.checkpoint()


def _get_executable_command(command: str) -> str:
    """
    Get the correct executable command normalized for the current platform.

    Args:
        command: Base command (e.g., 'uvx', 'npx')

    Returns:
        str: Platform-appropriate command
    """
    if sys.platform == "win32":  # pragma: no cover

        return get_windows_executable_command(command)
    else:
        return command  # pragma: no cover


async def _create_platform_compatible_process(
    command: str,
    args: list[str],
    errlog: TextIO = sys.stderr,
    cwd: Path | str | None = None,
):
    """
    Creates a subprocess in a platform-compatible way.

    Unix: Creates process in a new session/process group for killpg support
    Windows: Creates process in a Job Object for reliable child termination
    """
    env = None
    if sys.platform == "win32":  # pragma: no cover
        process = await create_windows_process(command, args, env, errlog, cwd)
    else:
        process = await anyio.open_process(
            [command, *args],
            env=env,
            stderr=errlog,
            cwd=cwd,
            start_new_session=True,
        )  # pragma: no cover

    return process


async def _terminate_process_tree(process: Process | FallbackProcess, timeout_seconds: float = 2.0) -> None:
    """
    Terminate a process and all its children using platform-specific methods.

    Unix: Uses os.killpg() for atomic process group termination
    Windows: Uses Job Objects via pywin32 for reliable child process cleanup

    Args:
        process: The process to terminate
        timeout_seconds: Timeout in seconds before force killing (default: 2.0)
    """
    if sys.platform == "win32":  # pragma: no cover
        await terminate_windows_process_tree(process, timeout_seconds)
    else:  # pragma: no cover
        # FallbackProcess should only be used for Windows compatibility
        assert isinstance(process, Process)
        await terminate_posix_process_tree(process, timeout_seconds)
