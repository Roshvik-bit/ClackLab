"""
Single-instance controller using Qt local Unix domain socket IPC.
Ensures only one instance of the ClackLab background runtime runs at any time,
and signals the existing instance to reveal its window when launched again.
"""

import logging
from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

logger = logging.getLogger(__name__)

DEFAULT_SERVER_NAME = "clacklab_runtime_single_instance"


class SingleInstanceController(QObject):
    """
    Prevents duplicate instances of ClackLab.
    If an existing instance is active, passes an activation signal and allows
    the newly launched process to exit gracefully.
    """

    show_window_requested = Signal()

    def __init__(self, server_name: str = DEFAULT_SERVER_NAME, parent: QObject = None):
        super().__init__(parent)
        self.server_name = server_name
        self.server: QLocalServer = None
        self._is_primary = False

    @property
    def is_primary(self) -> bool:
        return self._is_primary

    def acquire_lock(self, timeout_ms: int = 800) -> bool:
        """
        Attempts to acquire single-instance ownership.
        Returns True if this is the primary instance.
        Returns False if another instance is already running (and was signaled).
        """
        # Test connection to potential running instance
        socket = QLocalSocket()
        socket.connectToServer(self.server_name)

        if socket.waitForConnected(timeout_ms):
            logger.info("Existing ClackLab instance detected. Signaling it to bring window to front.")
            try:
                socket.write(b"ACTIVATE_WINDOW\n")
                socket.flush()
                socket.waitForBytesWritten(timeout_ms)
            except Exception as e:
                logger.warning(f"Error signaling existing instance: {e}")
            finally:
                socket.disconnectFromServer()
                socket.close()

            self._is_primary = False
            return False

        # No active instance responded. Cleanup stale socket file if any and listen.
        QLocalServer.removeServer(self.server_name)

        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._handle_new_connection)

        if not self.server.listen(self.server_name):
            logger.warning(f"Could not bind QLocalServer '{self.server_name}': {self.server.errorString()}")
            # Still proceed as primary if server bind failed due to filesystem permissions
            self._is_primary = True
            return True

        logger.info(f"SingleInstanceController locked primary runtime on '{self.server_name}'.")
        self._is_primary = True
        return True

    def _handle_new_connection(self):
        """Processes IPC activation request from secondary launch."""
        if not self.server:
            return

        client_socket = self.server.nextPendingConnection()
        if not client_socket:
            return

        def read_command():
            try:
                data = client_socket.readAll().data().decode("utf-8", errors="ignore").strip()
                if "ACTIVATE_WINDOW" in data or "SHOW_WINDOW" in data:
                    logger.info("Received activation command from secondary instance launch.")
                    self.show_window_requested.emit()
            finally:
                client_socket.disconnectFromServer()
                client_socket.deleteLater()

        client_socket.readyRead.connect(read_command)

    def release_lock(self):
        """Releases the single-instance IPC server."""
        if self.server:
            try:
                self.server.close()
                QLocalServer.removeServer(self.server_name)
            except Exception as e:
                logger.debug(f"Error releasing server lock: {e}")
            self.server = None
        self._is_primary = False
