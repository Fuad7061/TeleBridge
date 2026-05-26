from app.workers.telegram import TelegramWorker

worker: TelegramWorker | None = None
_pending_auth: dict = {}


def get_worker() -> TelegramWorker | None:
    return worker


def set_worker(w: TelegramWorker | None):
    global worker
    worker = w
