"""
Data generation for Rocket League GM Simulator.
Creates fictional players, teams, and initial league setup.
"""

import random
import uuid
from typing import List, Dict, Tuple

from ..models.player import Player, PlayerAttributes, HiddenAttributes, generate_random_player
from ..models.team import Team, Contract, Finances


# Fictional player name components
FIRST_NAMES = [
    "Alex", "Jordan", "Tyler", "Kyle", "Ryan", "Jake", "Nick", "Mike",
    "Chris", "Matt", "Dan", "Sam", "Luke", "Jack", "Ben", "Tom",
    "Max", "Leo", "Finn", "Cole", "Zach", "Drew", "Sean", "Evan",
    "Seth", "Noah", "Liam", "Owen", "Eli", "Ian", "Kai", "Axel",
    "Marcus", "Adrian", "Felix", "Oscar", "Hugo", "Emil", "Lars", "Erik",
    "Theo", "Milo", "Arlo", "Ezra", "Jude", "Rhys", "Kian", "Niko"
]

LAST_NAMES = [
    "Storm", "Blaze", "Frost", "Knight", "Wolf", "Phoenix", "Hawk", "Viper",
    "Striker", "Shadow", "Thunder", "Flash", "Rocket", "Turbo", "Ace", "Legend",
    "Hunter", "Ranger", "Fury", "Titan", "Ghost", "Phantom", "Blade", "Steel",
    "Nova", "Bolt", "Apex", "Prime", "Echo", "Drift", "Flux", "Pulse",
    "Miller", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Martinez", "Davis",
    "Anderson", "Wilson", "Taylor", "Thomas", "Moore", "Jackson", "White", "Harris"
]

# Gamer tag styles
TAG_PREFIXES = ["x", "iM", "oX", "Im", "Its", "The", "Mr", "Dr", ""]
TAG_SUFFIXES = ["_", "x", "RL", "99", "7", "23", "0", "1", ""]

# Team name components
TEAM_PREFIXES = [
    "Team", "Cloud", "Evil", "Golden", "Royal", "Dark", "Neon", "Cyber",
    "Alpha", "Omega", "Prime", "Elite", "Apex", "Zero", "Nova", "Pulse"
]

TEAM_NAMES = [
    "Esports", "Gaming", "Athletics", "Legends", "Titans", "Guardians",
    "Warriors", "Knights", "Phoenix", "Dragons", "Wolves", "Lions",
    "Eagles", "Falcons", "Rockets", "Storm", "Thunder", "Lightning",
    "Velocity", "Momentum", "Precision", "Altitude", "Horizon", "Zenith"
]

ORG_SUFFIXES = ["Esports", "Gaming", "GG", "E-Sports", ""]

NATIONALITIES = {
    "NA": ["USA", "Canada", "Mexico"],
    "EU": ["France", "UK", "Germany", "Spain", "Netherlands", "Sweden", "Denmark", "Finland", "Poland", "Italy"],
    "SAM": ["Brazil", "Argentina", "Chile", "Peru"],
    "OCE": ["Australia", "New Zealand"],
    "MENA": ["Saudi Arabia", "UAE", "Morocco", "Tunisia"],
    "APAC": ["Japan", "South Korea", "India", "Thailand"]
}


def generate_gamer_tag() -> str:
    """Generate a realistic esports gamer tag."""
    style = random.choice(["word", "name_combo", "word_number", "stylized"])
    
    if style == "word":
        words = ["Turbo", "Atomic", "Cosmic", "Savage", "Rapid", "Fierce",
                "Silent", "Swift", "Mystic", "Chaos", "Rogue", "Blitz",
                "Scrub", "Jstn", "Squishy", "Retals", "Arsenal", "Torment",
                "Kaydop", "Fairy", "Alpha", "Joyo", "Zen", "Rise"]
        return random.choice(words)
    
    elif style == "name_combo":
        first = random.choice(FIRST_NAMES)[:3]
        last = random.choice(LAST_NAMES)[:4]
        return f"{first}{last}"
    
    elif style == "word_number":
        word = random.choice(["Fire", "Ice", "Dark", "Light", "Blue", "Red", "Neon"])
        num = random.randint(0, 99)
        return f"{word}{num}"
    
    else:  # stylized
        prefix = random.choice(TAG_PREFIXES)
        name = random.choice(FIRST_NAMES)
        suffix = random.choice(TAG_SUFFIXES)
        return f"{prefix}{name}{suffix}"


def generate_team_name() -> Tuple[str, str]:
    """Generate a team name and abbreviation."""
    style = random.choice(["prefix_name", "single_word", "org_style"])
    
    if style == "prefix_name":
        prefix = random.choice(TEAM_PREFIXES)
        name = random.choice(TEAM_NAMES)
        full_name = f"{prefix} {name}"
        abbrev = prefix[0] + name[:2]
    
    elif style == "single_word":
        name = random.choice(TEAM_NAMES)
        full_name = name
        abbrev = name[:3]
    
    else:  # org_style
        word1 = random.choice(["Gen", "Spaced", "Version", "OXG", "FaZe", "NRG", 
                               "Moist", "Karmine", "Dignitas", "Vitality"])
        suffix = random.choice(ORG_SUFFIXES)
        full_name = f"{word1} {suffix}".strip()
        abbrev = word1[:3].upper()
    
    return full_name, abbrev.upper()


def generate_player(region: str, tier: str = "average", age: int = None) -> Player:
    """Generate a single player for a specific region."""
    name = generate_gamer_tag()
    
    if age is None:
        # Age distribution weighted toward young players
        age_weights = {
            16: 5, 17: 10, 18: 15, 19: 15, 20: 12, 21: 10,
            22: 8, 23: 7, 24: 6, 25: 5, 26: 4, 27: 2, 28: 1
        }
        ages = list(age_weights.keys())
        weights = list(age_weights.values())
        age = random.choices(ages, weights=weights)[0]
    
    nationality = random.choice(NATIONALITIES.get(region, ["USA"]))
    
    return generate_random_player(name, age, tier)


def generate_team(
    region: str,
    tier: str = "average",
    player_pool: Dict[str, Player] = None
) -> Tuple[Team, List[Player]]:
    """
    Generate a team with a full roster.
    Returns (Team, list of new Players).
    """
    name, abbrev = generate_team_name()
    
    team = Team(
        id=str(uuid.uuid4())[:8],
        name=name,
        abbreviation=abbrev,
        region=region,
        chemistry=random.randint(40, 70),
        reputation=random.randint(30, 70),
        fan_base=random.randint(20, 60),
        elo=random.randint(1400, 1600)
    )
    
    # Adjust finances based on tier
    tier_budgets = {
        "star": (200000, 40000),
        "good": (150000, 30000),
        "average": (100000, 25000),
        "prospect": (60000, 15000)
    }
    balance, budget = tier_budgets.get(tier, (100000, 25000))
    team.finances = Finances(
        balance=balance,
        monthly_budget=budget,
        sponsor_income=random.randint(5000, 15000),
        merch_income=random.randint(1000, 5000),
        content_income=random.randint(2000, 8000)
    )
    
    # Generate roster (3 starters + 1 sub)
    new_players = []
    player_tiers = {
        "star": ["star", "star", "good", "good"],
        "good": ["good", "good", "average", "average"],
        "average": ["average", "average", "average", "prospect"],
        "prospect": ["prospect", "prospect", "prospect", "prospect"]
    }
    
    roster_tiers = player_tiers.get(tier, ["average"] * 4)
    
    for i, ptier in enumerate(roster_tiers):
        player = generate_player(region, ptier)
        player.team_id = team.id
        
        # Set role based on position
        roles = ["offensive", "playmaker", "defensive", "allrounder"]
        player.role = roles[i % len(roles)]
        
        new_players.append(player)
        
        # Create contract
        salary_ranges = {
            "star": (8000, 12000),
            "good": (5000, 8000),
            "average": (3000, 5000),
            "prospect": (1500, 3000)
        }
        min_sal, max_sal = salary_ranges.get(ptier, (3000, 5000))
        salary = random.randint(min_sal, max_sal)
        
        contract = Contract(
            player_id=player.id,
            team_id=team.id,
            salary=salary,
            length=random.randint(6, 24),  # 6-24 months
            buyout=salary * 6
        )
        
        team.add_player(player.id, contract)
        
        # Restore chemistry (it drops on add_player)
        team.chemistry = random.randint(50, 75)
    
    return team, new_players


def generate_league(
    region: str,
    num_teams: int = 8,
    tier_distribution: Dict[str, int] = None
) -> Tuple['League', Dict[str, Team], Dict[str, Player]]:
    """
    Generate a complete league with teams and players.
    """
    from ..simulation.season import League
    
    if tier_distribution is None:
        # Default: 1 star, 2 good, 3 average, 2 prospect
        tier_distribution = {"star": 1, "good": 2, "average": 3, "prospect": 2}
    
    # Ensure we have enough teams
    total_requested = sum(tier_distribution.values())
    if total_requested < num_teams:
        tier_distribution["average"] += (num_teams - total_requested)
    
    league = League(
        id=str(uuid.uuid4())[:8],
        name=f"RLCS {region}",
        region=region
    )
    
    teams = {}
    players = {}
    
    # Generate teams by tier
    tier_list = []
    for tier, count in tier_distribution.items():
        tier_list.extend([tier] * count)
    
    random.shuffle(tier_list)
    
    for tier in tier_list[:num_teams]:
        team, roster = generate_team(region, tier)
        teams[team.id] = team
        league.add_team(team.id)
        
        for player in roster:
            players[player.id] = player
    
    return league, teams, players


def generate_free_agent_pool(
    region: str,
    count: int = 20
) -> List[Player]:
    """Generate a pool of free agents for a region."""
    free_agents = []
    
    # Distribution: more average/prospects in FA pool
    tiers = ["star"] * 1 + ["good"] * 4 + ["average"] * 10 + ["prospect"] * 5
    
    for _ in range(count):
        tier = random.choice(tiers)
        player = generate_player(region, tier)
        free_agents.append(player)
    
    return free_agents


def create_initial_game_state() -> Dict:
    """
    Create complete initial game state for a new game.
    Returns dict with league, teams, players, and free_agents.
    """
    # Generate NA league as the primary league
    league, teams, players = generate_league("NA", num_teams=8)
    
    # Generate free agent pool
    free_agents = generate_free_agent_pool("NA", count=15)
    for fa in free_agents:
        players[fa.id] = fa
    
    return {
        'league': league,
        'teams': teams,
        'players': players,
        'free_agent_ids': [fa.id for fa in free_agents]
    }
