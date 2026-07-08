import logging
import requests

from config import FOOTBALL_DATA_KEY
from agents import apply_names

log = logging.getLogger(__name__)

BASE_URL = 'https://api.football-data.org/v4'
COMPETITION = 'PL'  # Premier League

_HEADERS = {'X-Auth-Token': FOOTBALL_DATA_KEY}


def _translate_club(name: str) -> str:
    """Klub nomini apply_names orqali o'zbekchalashtiradi (mavjud bo'lsa)."""
    return apply_names(name)


def fetch_standings() -> list[dict] | None:
    """
    Premier-liga jadvalini qaytaradi:
    [{"position": 1, "team": "Fuqarolar", "played": 38, "won": 28, "draw": 5,
      "lost": 5, "goal_diff": 47, "points": 89, "crest": "https://..."}]
    FOOTBALL_DATA_KEY yo'q yoki xato bo'lsa None qaytaradi.
    """
    if not FOOTBALL_DATA_KEY:
        return None
    try:
        res = requests.get(
            f'{BASE_URL}/competitions/{COMPETITION}/standings',
            headers=_HEADERS, timeout=10,
        )
        res.raise_for_status()
        data = res.json()
        table = next(
            (s['table'] for s in data.get('standings', []) if s.get('type') == 'TOTAL'),
            [],
        )
        return [
            {
                'position': row['position'],
                'team': _translate_club(row['team']['name']),
                'played': row['playedGames'],
                'won': row['won'],
                'draw': row['draw'],
                'lost': row['lost'],
                'goal_diff': row['goalDifference'],
                'points': row['points'],
                'crest': row['team'].get('crest'),
            }
            for row in table
        ]
    except Exception as e:
        log.error(f'[Football-data] Jadval xato: {e}')
        return None


_STATUS_UZ = {
    'SCHEDULED': 'rejalashtirilgan',
    'TIMED': 'rejalashtirilgan',
    'IN_PLAY': 'jonli',
    'PAUSED': 'tanaffus',
    'FINISHED': 'tugadi',
    'POSTPONED': "ko'chirildi",
    'CANCELLED': 'bekor qilindi',
    'SUSPENDED': "to'xtatildi",
}


def fetch_matches_by_date(date_str: str) -> list[dict] | None:
    """
    Berilgan sana (YYYY-MM-DD) uchun Premier-liga o'yinlarini qaytaradi:
    [{"home": "Fuqarolar", "away": "To'pchilar", "home_score": 2, "away_score": 1,
      "status": "jonli", "minute": None, "utc_date": "...", "home_crest": "...", "away_crest": "..."}]
    """
    if not FOOTBALL_DATA_KEY:
        return None
    try:
        res = requests.get(
            f'{BASE_URL}/competitions/{COMPETITION}/matches',
            headers=_HEADERS,
            params={'dateFrom': date_str, 'dateTo': date_str},
            timeout=10,
        )
        res.raise_for_status()
        matches = res.json().get('matches', [])
        result = []
        for m in matches:
            score = m.get('score', {}).get('fullTime', {}) or {}
            result.append({
                'home': _translate_club(m['homeTeam']['name']),
                'away': _translate_club(m['awayTeam']['name']),
                'home_score': score.get('home'),
                'away_score': score.get('away'),
                'status': _STATUS_UZ.get(m.get('status', ''), m.get('status', '')),
                'utc_date': m.get('utcDate'),
                'home_crest': m['homeTeam'].get('crest'),
                'away_crest': m['awayTeam'].get('crest'),
            })
        return result
    except Exception as e:
        log.error(f'[Football-data] O\'yinlar xato: {e}')
        return None
