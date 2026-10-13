import colorsys
from PIL import ImageColor

# ---- 80 common background colours: (name, hex). The first one keeps the original blue rays. ----
BG_COLORS = [
 ("Original Blue", None), ("Red", "#E11D1D"), ("Crimson", "#DC143C"), ("Dark Red", "#B00020"), ("Blood Red", "#8B0000"), ("Maroon", "#800020"),
 ("Orange", "#FF7A00"), ("Dark Orange", "#E8590C"), ("Burnt Orange", "#CC5500"), ("Amber", "#FFB000"), ("Gold", "#FFC400"), ("Yellow", "#FFE600"),
 ("Lemon", "#F5E50A"), ("Lime", "#7CFC00"), ("Neon Green", "#39FF14"), ("Green", "#16A34A"), ("Emerald", "#10B981"), ("Forest", "#1B7F3B"),
 ("Mint", "#3EE8B5"), ("Teal", "#0D9488"), ("Turquoise", "#1CC8C8"), ("Cyan", "#00E5FF"), ("Aqua", "#22D3EE"), ("Sky Blue", "#38BDF8"),
 ("Azure", "#1E90FF"), ("Blue", "#2563EB"), ("Royal Blue", "#2F4BDB"), ("Cobalt", "#0047AB"), ("Navy", "#1E3A8A"), ("Indigo", "#4F46E5"),
 ("Violet", "#7C3AED"), ("Purple", "#9333EA"), ("Deep Purple", "#6B21A8"), ("Orchid", "#C026D3"), ("Magenta", "#E100FF"), ("Fuchsia", "#FF00AA"),
 ("Hot Pink", "#FF2D95"), ("Pink", "#FF6FB5"), ("Rose", "#F43F5E"), ("Raspberry", "#D6004C"), ("Coral", "#FF6B5E"), ("Salmon", "#FA8072"),
 ("Peach", "#FF9E7A"), ("Brown", "#92400E"), ("Chocolate", "#7B3F00"), ("Coffee", "#6F4E37"), ("Copper", "#B8662B"), ("Bronze", "#A9681F"),
 ("Sand", "#D9B26F"), ("Olive", "#708238"), ("Moss", "#5A7D2A"), ("Jade", "#00A86B"), ("Sea Green", "#2E8B57"), ("Ice Blue", "#8FD3FE"),
 ("Steel Blue", "#4682B4"), ("Slate", "#64748B"), ("Gray", "#9CA3AF"), ("Silver", "#C0C7D1"), ("White", "#FFFFFF"), ("Charcoal", "#4B5563"),
 ("Lavender", "#A78BFA"), ("Lilac", "#C084FC"), ("Plum", "#8E3A8E"), ("Wine", "#722F37"), ("Cherry", "#C2185B"), ("Ruby", "#E0115F"),
 ("Scarlet", "#FF2400"), ("Tangerine", "#FF8C42"), ("Mustard", "#E1AD01"), ("Chartreuse", "#A3E635"), ("Spring Green", "#00FF7F"), ("Aquamarine", "#5EEAD4"),
 ("Electric Blue", "#0A5CFF"), ("Ultramarine", "#3F2BFF"), ("Midnight Blue", "#1B2A6B"), ("Periwinkle", "#7F8CFF"), ("Bubblegum", "#FF8AD8"), ("Blush", "#F8A5C2"),
 ("Rust", "#B7410E"), ("Neon Cyan", "#00F5FF"),
]

_HAND = [
 ("Original Purple", "#470152", "#E753FE"), ("Sunset", "#FF512F", "#F09819"), ("Ocean", "#2193B0", "#1B6CA8"), ("Instagram", "#833AB4", "#FD1D1D"),
 ("Peach Glow", "#FF9966", "#FF5E62"), ("Mint Fresh", "#00B09B", "#4FA83D"), ("Lavender Dream", "#8E6CD1", "#E26BC2"), ("Fire", "#F12711", "#F5AF19"),
 ("Sky", "#2F80ED", "#56CCF2"), ("Berry", "#8E2DE2", "#4A00E0"), ("Candy", "#FF0844", "#FF7A59"), ("Aqua", "#13547A", "#2BB5A5"),
 ("Mango", "#F7971E", "#FFD200"), ("Emerald", "#0F9B58", "#2BB0C9"), ("Midnight", "#232526", "#485563"), ("Cherry", "#EB3349", "#F45C43"),
 ("Grape", "#5F2C82", "#49A09D"), ("Blue Lagoon", "#1FA2A6", "#191654"), ("Bubblegum", "#FF4FC3", "#3813C2"), ("Deep Space", "#000046", "#1CB5E0"),
 ("Royal Night", "#141E30", "#3A5F9E"), ("Neon Pink", "#FF0099", "#7A1FA2"), ("Forest", "#134E5E", "#71B280"), ("Passion", "#E52D27", "#B31217"),
 ("Twilight", "#2C3E83", "#C4457E"), ("Aurora", "#00C9A7", "#845EC2"), ("Cosmic", "#FF00CC", "#333399"), ("Rosewater", "#E8607A", "#F5A3B1"),
 ("Ruby Glow", "#C31432", "#240B36"), ("Citrus", "#F9A825", "#7CB342"), ("Tropical", "#06BEB6", "#48B1BF"), ("Northern Lights", "#43CEA2", "#185A9D"),
 ("Magic Hour", "#FF6B6B", "#556270"), ("Dusk", "#6A3093", "#A044FF"), ("Dawn", "#F857A6", "#FF5858"), ("Velvet", "#7B1E3A", "#D64F6B"),
 ("Cyber", "#00F0FF", "#7000FF"), ("Lava", "#FF4E50", "#F9D423"), ("Toxic", "#B2FF00", "#00A86B"), ("Galaxy", "#0F0C29", "#6A4C93"),
 ("Purple Rain", "#41295A", "#B24592"), ("Hot Sunset", "#FF0F7B", "#F89B29"), ("Cool Blues", "#2193B0", "#6A82FB"), ("Warm Flame", "#FF9A9E", "#E8506E"),
 ("Iceberg", "#4CA1AF", "#2C3E50"), ("Sakura", "#E96FA6", "#F4A6C3"), ("Matcha", "#7BA05B", "#3C6E47"), ("Coffee", "#7B5B45", "#3E2723"),
 ("Wine", "#8E2C48", "#3B0A1E"), ("Steel", "#667DB6", "#2F3E5C"),
 ("Blush", "#C94B8C", "#F78DA7"), ("Plum", "#3B0A45", "#A63A8F"), ("Teal Night", "#06202B", "#1B8A8F"), ("Gold Rush", "#8A5A00", "#F5B700"),
 ("Moss", "#1F3B2D", "#7DA36B"), ("Coral Reef", "#FF6F61", "#2B9EB3"), ("Neon Lime", "#1E3C00", "#9BE800"), ("Rose Quartz", "#B24A6B", "#F6B8C8"),
 ("Electric Blue", "#0A1AFF", "#00D4FF"), ("Burnt Orange", "#7A1F00", "#FF8A1F"), ("Lilac Mist", "#6F4BA8", "#C9A6F0"), ("Mocha Rose", "#4A2A2A", "#C98B8B"),
 ("Arctic", "#0B3C5D", "#9AD1E6"), ("Sunrise", "#FF3D68", "#FFC371"), ("Ink Blue", "#05103A", "#2A56C6"), ("Fresh Mint", "#0B6E4F", "#8EE4AF"),
]


# ---- 300 gradients: (name, colour 1 = start, colour 2 = end). Dark-to-colour ones first (the template's look) ----
_DARK = "#0B0B10"
_BASE = [("Ruby", "#E0115F"), ("Coral", "#FF6F61"), ("Orange", "#FF8C1A"), ("Gold", "#F5B700"), ("Lime", "#7CB342"), ("Emerald", "#10B981"),
         ("Teal", "#14B8A6"), ("Cyan", "#06B6D4"), ("Sky", "#3B9EFF"), ("Royal", "#2F5DCB"), ("Indigo", "#4F46E5"), ("Violet", "#8B5CF6"),
         ("Magenta", "#D946EF"), ("Pink", "#FF4D9D"), ("Slate", "#475569"), ("Crimson", "#9B1B30"), ("Amber", "#FFB000"), ("Olive", "#6B7A1F"),
         ("Jade", "#00A86B"), ("Navy", "#0B1F4D"), ("Plum", "#6B2C6E"), ("Rose", "#E8607A"), ("Mocha", "#6F4E37"), ("Red", "#E11D1D"),
         ("Green", "#16A34A"), ("Blue", "#2563EB"), ("Purple", "#9333EA"), ("Yellow", "#FFE600"), ("Peach", "#FF9E7A"), ("Mint", "#3EE8B5")]
def _build_gradients(total=300):
    items = [("Original Indigo", "#1B1C24", "#4848CA")]; names = {"Original Indigo"}
    for n_, hx in _BASE:                                     # 30 "dark -> colour" gradients like the examples
        nm = f"Dark {n_}"; items.append((nm, _DARK, hx)); names.add(nm)
    for nm, a, b in _HAND:
        if nm not in names: names.add(nm); items.append((nm, a, b))
    n = len(_BASE)
    for gap in range(1, 20):
        for i in range(n):
            (a_, ha), (b_, hb) = _BASE[i], _BASE[(i + gap) % n]; nm = f"{a_} {b_}"
            if nm not in names and f"{b_} {a_}" not in names: names.add(nm); items.append((nm, ha, hb))
            if len(items) >= total: return items[:total]
    return items[:total]
GRADIENTS = _build_gradients()
