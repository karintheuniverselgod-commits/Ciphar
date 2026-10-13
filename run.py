"""Launcher that adds /authorize and /deauthorize WITHOUT touching bot.py.

Run this instead of bot.py:   python run.py
It imports bot.py as-is, fills bot.ALLOWED (the list bot.py's own gatekeeper checks)
and registers the extra commands right before polling starts.
"""
import json, logging, os, tempfile
import bot
from telegram.ext import CommandHandler

OWNERS = {7684310072, 7466035628}
DATA_DIR = os.environ.get("DATA_DIR", bot.HERE)
AUTH_FILE = os.path.join(DATA_DIR, "authorized.json")
log = logging.getLogger("posterbot.auth")


def load():
    try:
        with open(AUTH_FILE, encoding="utf-8") as f:
            return {int(x) for x in json.load(f)}
    except (FileNotFoundError, ValueError):
        return set()


def save(ids):
    os.makedirs(DATA_DIR, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=DATA_DIR)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(sorted(ids), f)
    os.replace(tmp, AUTH_FILE)


AUTHORIZED = load()
bot.ALLOWED.update(OWNERS | AUTHORIZED)      # bot.py's gatekeeper now lets owners + authorized users in


def target_id(update, ctx):
    """User ID from `/authorize 123456` or from replying to the person's message."""
    if ctx.args:
        a = ctx.args[0].lstrip("@")
        return int(a) if a.lstrip("-").isdigit() else None
    r = update.message.reply_to_message
    return r.from_user.id if r and r.from_user else None


async def authorize(update, ctx):
    m = update.message
    if update.effective_user.id not in OWNERS:
        await m.reply_text("⛔ Only the main owners can do this."); return
    uid = target_id(update, ctx)
    if uid is None:
        await m.reply_text("Use: <code>/authorize 123456789</code>\nor reply to the person's message with /authorize", parse_mode="HTML"); return
    if uid in OWNERS or uid in AUTHORIZED:
        await m.reply_text("ℹ️ That user already has access."); return
    AUTHORIZED.add(uid); bot.ALLOWED.add(uid); save(AUTHORIZED)
    await m.reply_text(f"✅ <code>{uid}</code> is now authorized.", parse_mode="HTML")


async def deauthorize(update, ctx):
    m = update.message
    if update.effective_user.id not in OWNERS:
        await m.reply_text("⛔ Only the main owners can do this."); return
    uid = target_id(update, ctx)
    if uid is None:
        await m.reply_text("Use: <code>/deauthorize 123456789</code>\nor reply to the person's message with /deauthorize", parse_mode="HTML"); return
    if uid in OWNERS:
        await m.reply_text("⛔ Main owners cannot be removed."); return
    if uid not in AUTHORIZED:
        await m.reply_text("ℹ️ That user is not in the authorized list."); return
    AUTHORIZED.discard(uid); bot.ALLOWED.discard(uid); save(AUTHORIZED)
    await m.reply_text(f"🚫 <code>{uid}</code> is no longer authorized.", parse_mode="HTML")


async def authorized_list(update, ctx):
    if update.effective_user.id not in OWNERS:
        await update.message.reply_text("⛔ Only the main owners can do this."); return
    rows = ["👑 <b>Owners</b>"] + [f"<code>{i}</code>" for i in sorted(OWNERS)]
    rows += ["", "✅ <b>Authorized</b>"] + ([f"<code>{i}</code>" for i in sorted(AUTHORIZED)] or ["none"])
    await update.message.reply_text("\n".join(rows), parse_mode="HTML")


# bot.main() builds the app and calls run_polling(); we add our handlers just before it starts.
_orig_run_polling = bot.Application.run_polling


def run_polling_with_auth(self, *a, **kw):
    self.add_handler(CommandHandler("authorize", authorize))
    self.add_handler(CommandHandler("deauthorize", deauthorize))
    self.add_handler(CommandHandler("authorized", authorized_list))
    log.info("Owners: %s | Authorized: %s", sorted(OWNERS), sorted(AUTHORIZED))
    return _orig_run_polling(self, *a, **kw)


bot.Application.run_polling = run_polling_with_auth

if __name__ == "__main__":
    bot.main()
