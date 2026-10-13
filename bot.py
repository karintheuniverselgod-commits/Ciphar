import asyncio, html, io, logging, os, re, socket, traceback, datetime
import httpx
from PIL import Image
from telegram import InlineKeyboardButton as Btn, InlineKeyboardMarkup as Markup, Update
from telegram.error import NetworkError
from telegram.ext import (Application, ApplicationHandlerStop, CallbackQueryHandler, CommandHandler, ContextTypes,
                          MessageHandler, PicklePersistence, TypeHandler, filters)

HERE = os.path.dirname(os.path.abspath(__file__))
env_file = os.path.join(HERE, ".env")                      # optional: BOT_TOKEN=..., ALLOWED_IDS=... 
if os.path.exists(env_file):
    for line in open(env_file, encoding="utf-8"):
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.strip().split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

import poster
from palettes import BG_COLORS, GRADIENTS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("posterbot")
ALLOWED = {int(x) for x in os.environ.get("ALLOWED_IDS", "").replace(" ", "").split(",") if x}
MAX_FILE_MB = float(os.environ.get("MAX_FILE_MB", "25"))               # biggest poster file (Telegram allows up to 50)
SEM = asyncio.Semaphore(int(os.environ.get("MAX_PARALLEL", "4")))     # posters rendered at the same time

STEPS = ["type", "title", "synopsis", "size", "genres", "rating", "cover", "bg", "gradient"]
PER_PAGE = 20
RATINGS = [f"{v}%" for v in range(5, 101, 5)]                                  # 4 x 5 grid (you can also type any number, e.g. 74)
RETRY_KB = Markup([[Btn("🔁 Retry", callback_data="retry"), Btn("🆕 New poster", callback_data="new")]])


# ---------------------------------------------------------------- errors / reports
def is_network_error(err):
    return isinstance(err, (NetworkError, httpx.TransportError, ConnectionError, TimeoutError, socket.gaierror))


async def send_report(bot, chat_id, err):
    """Network problem -> short message. Anything else -> a full problem report. Both come with Retry / New buttons."""
    if is_network_error(err):
        log.warning("Network error: %s", err)
        text = "📡 <b>Network error</b>\nI could not reach Telegram or the internet. Tap <b>Retry</b> when your connection is back."
        targets = [chat_id]
    else:
        tb = "".join(traceback.format_exception(type(err), err, err.__traceback__))
        log.error("Problem:\n%s", tb)
        with open(os.path.join(HERE, "errors.log"), "a", encoding="utf-8") as f:
            f.write(f"\n=== {datetime.datetime.now():%Y-%m-%d %H:%M:%S} ===\n{tb}")
        last = traceback.extract_tb(err.__traceback__)[-1]
        short = "\n".join(tb.strip().splitlines()[-6:])
        text = (f"⚠️ <b>Problem report</b>\n"
                f"<b>Where:</b> <code>{html.escape(os.path.basename(last.filename))}:{last.lineno} in {html.escape(last.name)}()</code>\n"
                f"<b>Error:</b> <code>{html.escape(type(err).__name__)}: {html.escape(str(err))[:300]}</code>\n\n"
                f"<pre>{html.escape(short)[:1500]}</pre>\n"
                f"Saved in <code>errors.log</code>. Tap <b>Retry</b> or start a <b>New poster</b>.")
        targets = [chat_id]
    for t in targets:
        if t:
            try: await bot.send_message(t, text, parse_mode="HTML", reply_markup=RETRY_KB)
            except Exception: pass


async def on_error(update, ctx: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat if isinstance(update, Update) else None
    await send_report(ctx.bot, chat.id if chat else None, ctx.error)


async def gatekeeper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """If ALLOWED_IDS is set, only those Telegram user IDs can use the bot."""
    if not ALLOWED: return
    user = update.effective_user
    if not user or user.id not in ALLOWED:
        if update.effective_message: await update.effective_message.reply_text("🔒 This bot is private.")
        raise ApplicationHandlerStop


# ---------------------------------------------------------------- keyboards
def footer(step=None, sub=False):
    row = []
    if step and (STEPS.index(step) > 0 or sub): row.append(Btn("⬅️ Back", callback_data="back"))
    row.append(Btn("❌ Cancel", callback_data="cancel"))
    return row


def grid(buttons, per_row):
    return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]


def list_keyboard(kind, page):
    items = BG_COLORS if kind == "bg" else GRADIENTS
    pages = (len(items) + PER_PAGE - 1) // PER_PAGE
    chunk = items[page * PER_PAGE:(page + 1) * PER_PAGE]
    btns = [Btn(it[0], callback_data=f"{kind}pick:{page * PER_PAGE + i}") for i, it in enumerate(chunk)]
    rows = grid(btns, 2)
    rows.append([Btn("⬅️", callback_data=f"{kind}page:{(page - 1) % pages}"), Btn(f"{page + 1}/{pages}", callback_data="noop"),
                 Btn("➡️", callback_data=f"{kind}page:{(page + 1) % pages}")])
    rows.append([Btn("✍️ Custom HEX" if kind == "bg" else "✍️ Custom gradient", callback_data=f"{kind}custom")])
    rows.append(footer("bg" if kind == "bg" else "gradient"))
    return Markup(rows)


# ---------------------------------------------------------------- asking each step
async def ask(ctx, chat_id):
    ud = ctx.user_data; step = ud["step"]; n = STEPS.index(step) + 1; head = f"Step {n}/{len(STEPS)} — "; ud["await"] = None
    send = lambda text, kb: ctx.bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=kb)
    if step == "type":
        await send(head + "📚 Pick the <b>type</b>:", Markup([[Btn("Manhwa", callback_data="type:Manhwa"), Btn("Manhua", callback_data="type:Manhua")], footer(step)]))
    elif step == "title":
        await send(head + "🎬 Send the <b>title</b>.", Markup([footer(step)]))
    elif step == "synopsis":
        await send(head + "📝 Send the <b>synopsis</b> (all text at once; new lines are kept as paragraphs).", Markup([footer(step)]))
    elif step == "size":
        await send(head + "🔠 Choose the <b>text size</b> for the About text:", Markup([
            [Btn("Small", callback_data="size:small"), Btn("Medium", callback_data="size:medium"), Btn("Large", callback_data="size:large")], footer(step)]))
    elif step == "genres":
        await send(head + "🏷 Send all <b>5 genres</b>, separated by commas.\nExample: <code>Action, Drama, Comedy, Mystery, Crime</code>", Markup([footer(step)]))
    elif step == "rating":
        await send(head + "⭐ Choose the <b>rating</b> (or type a number from 0 to 100, like <code>74</code>):",
                   Markup(grid([Btn(r, callback_data=f"rate:{r}") for r in RATINGS], 4) + [[Btn("N/A", callback_data="rate:N/A")], footer(step)]))
    elif step == "cover":
        await send(head + "🖼 Send the <b>cover</b> image.\n(Send it as a <i>file</i> for best quality. I auto-upscale it to HD.)", Markup([footer(step)]))
    elif step == "bg":
        await send(head + "🖼 Pick the <b>background colour</b> (the glowing rays):", list_keyboard("bg", 0))
    elif step == "gradient":
        await send(head + "🌈 Pick the <b>gradient</b> for the title, bars, pills and left side:", list_keyboard("grad", 0))


async def goto(ctx, chat_id, step):
    ctx.user_data["step"] = step
    await ask(ctx, chat_id)


async def next_step(ctx, chat_id):
    await goto(ctx, chat_id, STEPS[STEPS.index(ctx.user_data["step"]) + 1])


# ---------------------------------------------------------------- commands
async def start(update, ctx):
    await update.message.reply_text("Hey! 👋 Wanna make a poster?\n\nDo /newposter")


async def new_poster(update, ctx):
    ctx.user_data.clear(); ctx.user_data["d"] = {}
    await goto(ctx, update.effective_chat.id, "type")


async def cancel_cmd(update, ctx):
    ctx.user_data.clear()
    await update.message.reply_text("❌ Cancelled. Do /newposter when you are ready.")


# ---------------------------------------------------------------- text and image input
def parse_hex(text):
    return ["#" + f.lstrip("#").upper() for f in re.findall(r"#?[0-9a-fA-F]{6}\b", text)]


async def on_text(update, ctx):
    ud = ctx.user_data; m = update.message; chat_id = update.effective_chat.id; text = m.text.strip()
    step = ud.get("step")
    if not step:
        await m.reply_text("Do /newposter to start 🙂"); return
    d = ud.setdefault("d", {})
    if ud.get("await") == "bghex":
        hx = parse_hex(text)
        if len(hx) != 1:
            await m.reply_text("That is not a valid HEX. Example: <code>#E11D1D</code>", parse_mode="HTML"); return
        ud["await"] = None; await choose_bg(ctx, chat_id, hx[0]); return
    if ud.get("await") == "gradhex":
        hx = parse_hex(text)
        if len(hx) != 2:
            await m.reply_text("Send <b>two</b> HEX codes (start, end), like:\n<code>#0B0B10 #E11D1D</code>", parse_mode="HTML"); return
        ud["await"] = None; ud["cust"] = (hx[0], hx[1]); await drop_preview(ctx, chat_id)
        buf = io.BytesIO(); poster.gradient_preview("Custom", hx[0], hx[1]).save(buf, "PNG"); buf.seek(0)
        sent = await m.reply_photo(buf, caption="Use this gradient?", reply_markup=Markup([[Btn("✅ Use this gradient", callback_data="gcustuse"), Btn("↩️ Back", callback_data="pback")]]))
        ud["swatch_msg"] = sent.message_id; return
    if step == "title":
        d["title"] = text[:80]; await next_step(ctx, chat_id)
    elif step == "synopsis":
        d["synopsis"] = text[:1800]; await next_step(ctx, chat_id)
    elif step == "genres":
        g = [x.strip() for x in re.split(r"[,\n]", text) if x.strip()]
        if len(g) < 5:
            await m.reply_text(f"I got {len(g)} genre{'s' if len(g) != 1 else ''}. Please send all <b>5</b>, separated by commas.\nExample: <code>Action, Drama, Comedy, Mystery, Crime</code>", parse_mode="HTML"); return
        d["genres"] = g[:5]; await next_step(ctx, chat_id)
    elif step == "rating":
        mt = re.fullmatch(r"(\d{1,3})\s*%?", text)
        if not mt or int(mt.group(1)) > 100:
            await m.reply_text("Please send a number from 0 to 100 (like <code>74</code>) or use the buttons.", parse_mode="HTML"); return
        d["rating"] = f"{int(mt.group(1))}%"; await next_step(ctx, chat_id)
    else:
        await m.reply_text("Please use the buttons above 👆 (or /cancel).")


async def on_image(update, ctx):
    ud = ctx.user_data; m = update.message
    if ud.get("step") != "cover":
        await m.reply_text("I do not need an image right now. Do /newposter to start 🙂"); return
    tg_file = await (m.photo[-1] if m.photo else m.document).get_file()
    ud["d"]["cover"] = bytes(await tg_file.download_as_bytearray())
    await next_step(ctx, chat_id=update.effective_chat.id)


# ---------------------------------------------------------------- buttons
async def drop_preview(ctx, chat_id):
    old = ctx.user_data.pop("swatch_msg", None)
    if old:
        try: await ctx.bot.delete_message(chat_id, old)
        except Exception: pass


async def choose_bg(ctx, chat_id, hex_or_none):
    """Background chosen -> remember it, then ask for the gradient (or rebuild straight away when only changing the background)."""
    ud = ctx.user_data; ud.setdefault("fill", {})["bg"] = hex_or_none; await drop_preview(ctx, chat_id)
    if ud.get("only") == "bg" and ud["fill"].get("c1"):
        ud["only"] = None; await build(ctx, chat_id, ud["fill"])
    else:
        await goto(ctx, chat_id, "gradient")


async def choose_gradient(ctx, chat_id, c1, c2):
    ud = ctx.user_data; fill = ud.setdefault("fill", {}); fill["c1"], fill["c2"] = c1, c2; ud["only"] = None; await drop_preview(ctx, chat_id)
    await build(ctx, chat_id, fill)


async def on_button(update, ctx):
    q = update.callback_query; ud = ctx.user_data; data = q.data; chat_id = q.message.chat_id
    parts = data.split(":"); act = parts[0]
    if act == "noop":
        await q.answer(); return
    if act == "new":
        await q.answer(); ud.clear(); ud["d"] = {}; await goto(ctx, chat_id, "type"); return
    if act == "cancel":
        await q.answer("Cancelled"); ud.clear()
        try: await q.message.edit_reply_markup(None)
        except Exception: pass
        await ctx.bot.send_message(chat_id, "❌ Cancelled. Do /newposter when you are ready."); return
    if act == "retry":
        await q.answer(); d = ud.get("d") or {}
        if ud.get("fill", {}).get("c1") and d.get("cover"): await build(ctx, chat_id, ud["fill"])
        elif ud.get("step"): await ask(ctx, chat_id)
        else: await ctx.bot.send_message(chat_id, "Nothing to retry. Do /newposter 🙂")
        return
    if act in ("chg_bg", "chg_grad"):
        await q.answer()
        if not (ud.get("d") or {}).get("cover"):
            await ctx.bot.send_message(chat_id, "That poster is too old. Do /newposter 🙂"); return
        ud["only"] = "bg" if act == "chg_bg" else "grad"; await goto(ctx, chat_id, "bg" if act == "chg_bg" else "gradient"); return
    step = ud.get("step")
    if not step:
        await q.answer("This button is old. Do /newposter 🙂", show_alert=True); return
    d = ud.setdefault("d", {})

    if act == "back":
        await q.answer()
        try: await q.message.edit_reply_markup(None)
        except Exception: pass
        await drop_preview(ctx, chat_id)
        if STEPS.index(step) > 0: await goto(ctx, chat_id, STEPS[STEPS.index(step) - 1])
        return
    if act == "pback":
        await q.answer(); ud.pop("swatch_msg", None); await q.message.delete(); return

    if act == "type" and step == "type":
        await q.answer(); d["type"] = parts[1]; await q.message.edit_text(f"📚 Type: <b>{parts[1]}</b> ✅", parse_mode="HTML"); await next_step(ctx, chat_id)
    elif act == "size" and step == "size":
        await q.answer(); d["size"] = parts[1]; await q.message.edit_text(f"🔠 Text size: <b>{parts[1].title()}</b> ✅", parse_mode="HTML"); await next_step(ctx, chat_id)
    elif act == "rate" and step == "rating":
        await q.answer(); d["rating"] = parts[1]; await q.message.edit_text(f"⭐ Rating: <b>{parts[1]}</b> ✅", parse_mode="HTML"); await next_step(ctx, chat_id)
    elif step in ("bg", "gradient"):
        await color_buttons(update, ctx, act, parts)
    else:
        await q.answer("This button is old.", show_alert=False)


async def color_buttons(update, ctx, act, parts):
    q = update.callback_query; ud = ctx.user_data; chat_id = q.message.chat_id
    if act in ("bgpage", "gradpage"):
        await q.answer(); await q.message.edit_reply_markup(list_keyboard("bg" if act == "bgpage" else "grad", int(parts[1])))
    elif act == "bgpick":
        await q.answer(); name, hx = BG_COLORS[int(parts[1])]; await drop_preview(ctx, chat_id)
        im = await asyncio.to_thread(poster.bg_preview, hx); buf = io.BytesIO(); im.save(buf, "JPEG", quality=90); buf.seek(0)
        sent = await q.message.reply_photo(buf, caption=f"{name}  {hx.upper() if hx else '(original)'}", reply_markup=Markup([[
            Btn("✅ Use this colour", callback_data=f"bguse:{parts[1]}"), Btn("↩️ Back", callback_data="pback")]]))
        ud["swatch_msg"] = sent.message_id
    elif act == "bguse":
        await q.answer("Got it"); await choose_bg(ctx, chat_id, BG_COLORS[int(parts[1])][1])
    elif act == "gradpick":
        await q.answer(); name, c1, c2 = GRADIENTS[int(parts[1])]; await drop_preview(ctx, chat_id)
        buf = io.BytesIO(); poster.gradient_preview(name, c1, c2).save(buf, "PNG"); buf.seek(0)
        sent = await q.message.reply_photo(buf, caption="Use this gradient?", reply_markup=Markup([[
            Btn("✅ Use this gradient", callback_data=f"graduse:{parts[1]}"), Btn("↩️ Back", callback_data="pback")]]))
        ud["swatch_msg"] = sent.message_id
    elif act == "graduse":
        await q.answer("Making your poster… ⏳"); _, c1, c2 = GRADIENTS[int(parts[1])]; await choose_gradient(ctx, chat_id, c1, c2)
    elif act == "gcustuse":
        c = ud.get("cust")
        if not c:
            await q.answer("Send the two HEX codes again", show_alert=True); return
        await q.answer("Making your poster… ⏳"); await choose_gradient(ctx, chat_id, c[0], c[1])
    elif act == "bgcustom":
        await q.answer(); ud["await"] = "bghex"
        await ctx.bot.send_message(chat_id, "✍️ Send a HEX colour like <code>#E11D1D</code>", parse_mode="HTML")
    elif act == "gradcustom":
        await q.answer(); ud["await"] = "gradhex"
        await ctx.bot.send_message(chat_id, "✍️ Send <b>two</b> HEX colours (start, end), for example:\n<code>#0B0B10 #E11D1D</code>", parse_mode="HTML")
    else:
        await q.answer("This button is old.")


# ---------------------------------------------------------------- building the poster
async def build(ctx, chat_id, fill):
    ud = ctx.user_data; d = ud["d"]; ud["fill"] = dict(fill)
    wait = await ctx.bot.send_message(chat_id, "⏳ Making your poster…")

    def work():
        cover = Image.open(io.BytesIO(d["cover"]))
        im = poster.render(d["title"], d["synopsis"], d.get("genres", []), d.get("rating", "N/A"), cover, fill, text_size=d.get("size", "medium"), media_type=d.get("type", "Manhwa"))
        full, size = poster.save_png_capped(im, MAX_FILE_MB)
        small = io.BytesIO(); im.convert("RGB").resize((1920, 1080), Image.LANCZOS).save(small, "JPEG", quality=92); small.seek(0)
        return small, full, size
    try:                                     # 1) making the poster (code problems show up here)
        async with SEM:
            small, full, size = await asyncio.to_thread(work)
    except Exception as err:
        try: await wait.delete()
        except Exception: pass
        await send_report(ctx.bot, chat_id, err); return
    try:                                     # 2) sending it (network problems show up here)
        try: await wait.delete()
        except Exception: pass
        await ctx.bot.send_photo(chat_id, small, caption=f"✅ {d['title']}", write_timeout=120, reply_markup=Markup([
            [Btn("🖼 Change background", callback_data="chg_bg"), Btn("🌈 Change gradient", callback_data="chg_grad")], [Btn("🆕 New poster", callback_data="new")]]))
        await ctx.bot.send_document(chat_id, full, filename=f"{re.sub(r'[^A-Za-z0-9]+', '_', d['title'])}_poster.png",
                                    caption=f"Full quality file 📁  {size[0]}×{size[1]}px · {full.getbuffer().nbytes / 1048576:.1f} MB", write_timeout=300)
    except Exception as err:
        await send_report(ctx.bot, chat_id, err)


def main():
    poster.ensure_fonts()
    app = (Application.builder().token(os.environ["BOT_TOKEN"])
           .persistence(PicklePersistence(os.path.join(HERE, "botdata.pickle")))
           .connect_timeout(30).read_timeout(60).write_timeout(120).pool_timeout(30).build())
    app.add_handler(TypeHandler(Update, gatekeeper), group=-1)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("newposter", new_poster))
    app.add_handler(CommandHandler("cancel", cancel_cmd))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, on_image))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(on_error)
    app.run_polling()


if __name__ == "__main__":
    main()
