import re

# ── O'zbek nomlari (faqat RSS News workflow uchun — football-specific) ────
NAMES = {
    'Premier League': 'Premier-liga',
    'Champions League': 'Chempionlar ligasi',
    'FA Cup': 'FA Kubogi',
    'Carabao Cup': 'Karabao Kubogi',
    'Europa League': 'Evropa ligasi',
    'Conference League': 'Konferensiyalar ligasi',
    'Manchester City': 'Manchester Siti',
    'Man City': 'Manchester Siti',
    'Manchester United': 'Manchester Yunayted',
    'Man United': 'Manchester Yunayted',
    'Man Utd': 'Manchester Yunayted',
    'Chelsea': 'Chelsi',
    'Liverpool': 'Liverpul',
    'Tottenham Hotspur': 'Tottenhem Xotspur',
    'Tottenham': 'Tottenhem',
    'Spurs': 'Tottenhem',
    'Newcastle United': 'Nyukasl Yunayted',
    'Newcastle': 'Nyukasl',
    'West Ham United': 'Vest Hem Yunayted',
    'West Ham': 'Vest Hem',
    'Brighton': 'Brayton',
    'Crystal Palace': 'Kristal Pelas',
    'Fulham': 'Fulhem',
    'Bournemouth': 'Bornmut',
    'Nottingham Forest': 'Nottingem Forest',
    'Leicester City': 'Lester Siti',
    'Leicester': 'Lester',
    'Wolverhampton': 'Vulverhempton',
    'Wolves': 'Vulverhempton',
    'Erling Haaland': 'Erling Holland',
    'Haaland': 'Holland',
    'Mohamed Salah': 'Muhammad Saloh',
    'Salah': 'Saloh',
    'Virgil van Dijk': 'Virjil van Deyk',
    'Pep Guardiola': 'Pep Gvardiola',
    'Guardiola': 'Gvardiola',
    'Marcus Rashford': 'Markus Reshford',
    'Rashford': 'Reshford',
}


def apply_names(text: str) -> str:
    if not text:
        return ''
    result = text
    for eng, uzb in sorted(NAMES.items(), key=lambda x: -len(x[0])):
        result = re.sub(rf'(?<!\w){re.escape(eng)}(?!\w)', uzb, result, flags=re.IGNORECASE)
    return result
