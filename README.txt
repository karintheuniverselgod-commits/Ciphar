MANHWA ABYSS POSTER BOT - quick start

DOCKER (VPS):
  1. Upload + unzip this folder, then:   cd posterbot && cp .env.example .env && nano .env      (paste BOT_TOKEN)
  2. docker compose up -d --build
  3. docker compose logs -f
  Update later: replace the changed files, then  docker compose up -d --build   (your .env and ./data stay as they are)

STEPS IN THE BOT:  type (Manhwa / Manhua) > title > synopsis > text size > 5 genres > rating (%) > cover > background colour > gradient
  - The underline in the top bar moves to the chosen type.
  - Background colour = 80 colours (the glowing rays change colour), custom HEX, preview before using.
  - Gradient = 300 gradients (title, bars, pills, JOIN NOW, ABOUT tab and the left side), custom gradient, preview before using.
  - After a poster you can change only the background, or only the gradient, without typing everything again.

FONTS (fonts/):  Bebas Neue (title) and Poppins are downloaded automatically.
  Glacial Indifference (About text + rating) is included.  white-apricot_regular.otf (genres) is the font file you sent.
  To use another genre font, put its file in fonts/ with "apricot" in the name.

FILES
  bot.py / run.py   the bot (run.py adds the owner / authorized-users system)
  poster.py         draws the poster      palettes.py   80 background colours + 300 gradients
  template.png      template with the placeholder texts removed (used by the bot)
  bg_orig.png       your background alone (the bot recolours it)     layout.npz   shape / glass data
  template_orig.png your original template     build_assets.py   rebuilds template.png + layout.npz
                    (run it ONLY if you change template_orig.png or bg_orig.png:  pip install scipy numpy pillow && python build_assets.py)
  If you change the layout (cover / text positions), send the new template + background to Claude - positions are numbers in poster.py.

SETTINGS (.env):  MAX_PARALLEL=4   POSTER_SCALE=1 (6400x3600, 0.5 = faster/smaller)   MAX_FILE_MB=25
