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
        
        # Create contract (yearly salaries)
        salary_ranges = {
            "star": (100000, 150000),     # $100k-$150k/year
            "good": (60000, 100000),      # $60k-$100k/year
            "average": (36000, 60000),    # $36k-$60k/year
            "prospect": (18000, 36000)    # $18k-$36k/year
        }
        min_sal, max_sal = salary_ranges.get(ptier, (36000, 60000))
        salary = random.randint(min_sal, max_sal)
        
        contract = Contract(
            player_id=player.id,
            team_id=team.id,
            salary=salary,
            years=random.randint(1, 3),  # 1-3 years
            buyout=salary * 2
        )
        
        team.add_player(player.id, contract)
        
        # Restore chemistry (it drops on add_player)
        team.chemistry = random.randint(50, 75)
    
    return team, new_players


def generate_league(
    region: str,
    num_teams: int = 32,
    tier_distribution: Dict[str, int] = None
) -> Tuple['League', Dict[str, Team], Dict[str, Player]]:
    """
    Generate a complete league with teams and players.
    Default is 32 teams for RLCS regional format.
    """
    from ..simulation.season import League
    
    if tier_distribution is None:
        # Distribution for 32 teams - pyramid structure
        if num_teams >= 32:
            tier_distribution = {
                "star": 4,       # Top tier teams
                "good": 8,       # Solid contenders
                "average": 12,   # Middle of the pack
                "prospect": 8    # Developing teams
            }
        elif num_teams >= 16:
            tier_distribution = {
                "star": 2,
                "good": 4,
                "average": 6,
                "prospect": 4
            }
        else:
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
    count: int = 30
) -> List[Player]:
    """Generate a pool of free agents for a region."""
    free_agents = []
    
    # Distribution: more average/prospects in FA pool
    # Adjusted for larger pool
    tiers = (
        ["star"] * 2 + 
        ["good"] * 6 + 
        ["average"] * 14 + 
        ["prospect"] * 8
    )
    
    for _ in range(count):
        tier = random.choice(tiers)
        player = generate_player(region, tier)
        free_agents.append(player)
    
    return free_agents


def generate_rookie(region: str, high_potential: bool = False) -> Player:
    """
    Generate a rookie (15-17 years old).
    Rookies have low current ability but varying potential.
    Small chance for "prodigy" rookies who come in with better stats.
    
    Args:
        region: Player's region
        high_potential: If True, guarantee high potential (85-95)
    """
    name = generate_gamer_tag()
    age = random.choice([15, 16, 17])
    nationality = random.choice(NATIONALITIES.get(region, ["USA"]))
    
    # Check for prodigy (10% chance, or higher if high_potential is set)
    prodigy_roll = random.random()
    is_prodigy = prodigy_roll < 0.10 or (high_potential and prodigy_roll < 0.35)
    
    if is_prodigy:
        # Prodigy: Higher starting stats, usually high potential
        base_level = random.randint(50, 65)  # Much higher base
        variance = 12
        
        attributes = PlayerAttributes(
            # Mechanical Skills - prodigies are already skilled
            aerial=random.randint(base_level, base_level + variance + 5),
            ground_control=random.randint(base_level - 5, base_level + variance),
            shooting=random.randint(base_level - 5, base_level + variance),
            advanced_mechanics=random.randint(base_level - 5, base_level + variance + 10),
            recovery=random.randint(base_level - 5, base_level + variance),
            car_control=random.randint(base_level, base_level + variance),
            
            # Game Sense - prodigies still have some gaps but are ahead
            positioning=random.randint(base_level - 10, base_level + 5),
            game_reading=random.randint(base_level - 10, base_level + 5),
            decision_making=random.randint(base_level - 15, base_level),
            passing=random.randint(base_level - 5, base_level + variance),
            boost_management=random.randint(base_level - 10, base_level + 5),
            
            # Defense/Offense
            saving=random.randint(base_level - 10, base_level + variance),
            challenging=random.randint(base_level - 10, base_level + 5),
            finishing=random.randint(base_level - 5, base_level + variance),
            creativity=random.randint(base_level, base_level + variance + 5),
            
            # Meta - prodigies can still be inconsistent
            speed=random.randint(base_level, base_level + variance + 5),
            consistency=random.randint(base_level - 15, base_level),  # Still inconsistent
            clutch=random.randint(base_level - 10, base_level + 5),
            mental=random.randint(base_level - 10, base_level + 5),
            teamwork=random.randint(base_level - 10, base_level + 5)
        )
        
        # Prodigies usually have high potential (80% chance of 80+)
        if high_potential:
            potential = random.randint(88, 95)
        else:
            prodigy_pot_roll = random.random()
            if prodigy_pot_roll < 0.50:
                potential = random.randint(85, 95)  # 50% chance elite
            elif prodigy_pot_roll < 0.80:
                potential = random.randint(78, 87)  # 30% chance very good
            else:
                potential = random.randint(70, 80)  # 20% chance good
    else:
        # Normal rookie: Lower starting stats
        base_level = random.randint(30, 50)
        variance = 8
        
        attributes = PlayerAttributes(
            # Mechanical Skills - rookies can be flashy but inconsistent
            aerial=random.randint(base_level - 5, base_level + variance + 5),
            ground_control=random.randint(base_level - 5, base_level + variance),
            shooting=random.randint(base_level - 5, base_level + variance),
            advanced_mechanics=random.randint(base_level - 10, base_level + variance + 10),
            recovery=random.randint(base_level - 5, base_level + variance),
            car_control=random.randint(base_level - 5, base_level + variance),
            
            # Game Sense - typically lower for rookies
            positioning=random.randint(base_level - 10, base_level),
            game_reading=random.randint(base_level - 10, base_level),
            decision_making=random.randint(base_level - 15, base_level - 5),
            passing=random.randint(base_level - 10, base_level + 5),
            boost_management=random.randint(base_level - 10, base_level),
            
            # Defense/Offense
            saving=random.randint(base_level - 10, base_level + 5),
            challenging=random.randint(base_level - 10, base_level),
            finishing=random.randint(base_level - 5, base_level + variance),
            creativity=random.randint(base_level - 5, base_level + variance + 5),
            
            # Meta - rookies can be inconsistent but have high ceilings
            speed=random.randint(base_level, base_level + variance + 5),
            consistency=random.randint(base_level - 15, base_level - 5),
            clutch=random.randint(base_level - 10, base_level + 5),
            mental=random.randint(base_level - 10, base_level + 5),
            teamwork=random.randint(base_level - 10, base_level + 5)
        )
        
        # Normal potential distribution
        if high_potential:
            potential = random.randint(85, 95)
        else:
            potential_roll = random.random()
            if potential_roll < 0.05:
                potential = random.randint(85, 95)  # 5% chance of star
            elif potential_roll < 0.20:
                potential = random.randint(75, 84)  # 15% chance of good
            elif potential_roll < 0.50:
                potential = random.randint(65, 74)  # 30% chance of average
            else:
                potential = random.randint(50, 64)  # 50% chance of low
    
    hidden = HiddenAttributes(
        potential=potential,
        ambition=random.randint(40, 90),  # Rookies can be very ambitious
        adaptability=random.randint(50, 80),  # Young = more adaptable
        injury_prone=random.randint(10, 30)
    )
    
    player = Player(
        id=str(uuid.uuid4())[:8],
        name=name,
        age=age,
        nationality=nationality,
        attributes=attributes,
        hidden=hidden,
        morale=random.randint(60, 85),  # Rookies tend to be enthusiastic
        form=random.randint(40, 60),
        role=random.choice(["offensive", "playmaker", "defensive", "allrounder"])
    )
    
    return player


def generate_rookie_class(region: str, count: int = 5, guarantee_star: bool = False) -> List[Player]:
    """
    Generate a class of rookies entering the scene.
    
    Args:
        region: Player's region
        count: Number of rookies to generate
        guarantee_star: If True, ensure at least one has top potential (90+)
    """
    rookies = []
    
    for i in range(count):
        # First rookie is guaranteed star if requested
        if guarantee_star and i == 0:
            rookie = generate_rookie(region, high_potential=True)
            # Make sure it's truly elite
            rookie.hidden.potential = random.randint(90, 95)
        else:
            rookie = generate_rookie(region, high_potential=False)
        
        rookies.append(rookie)
    
    return rookies


def retire_old_free_agents(
    free_agent_ids: List[str],
    players: Dict[str, Player],
    max_age: int = 28,
    target_count: int = 30
) -> List[str]:
    """
    Remove older free agents to make room for rookies.
    Returns updated list of free agent IDs.
    """
    current_count = len(free_agent_ids)
    
    if current_count <= target_count:
        return free_agent_ids
    
    # Sort by age (oldest first) then by overall (lowest first)
    def sort_key(pid):
        p = players.get(pid)
        if p:
            return (-p.age, p.overall)
        return (0, 0)
    
    sorted_fas = sorted(free_agent_ids, key=sort_key)
    
    # Keep only up to target_count, preferring younger/better players
    new_fas = []
    removed = []
    
    for pid in sorted_fas:
        player = players.get(pid)
        if player:
            if len(new_fas) < target_count:
                # Keep younger players and some older valuable ones
                if player.age < max_age or player.overall > 70:
                    new_fas.append(pid)
                else:
                    removed.append(pid)
            else:
                removed.append(pid)
    
    # If we still have too many, just trim to target
    if len(new_fas) > target_count:
        new_fas = new_fas[:target_count]
    
    return new_fas


def create_initial_game_state() -> Dict:
    """
    Create complete initial game state for a new game.
    Generates 31 AI teams (player adds the 32nd).
    Returns dict with league, teams, players, and free_agents.
    """
    # Generate NA league with 31 teams (player team is 32nd)
    league, teams, players = generate_league("NA", num_teams=31)
    
    # Generate free agent pool
    free_agents = generate_free_agent_pool("NA", count=25)
    
    # Add some rookies to the initial pool
    rookies = generate_rookie_class("NA", count=5, guarantee_star=False)
    free_agents.extend(rookies)
    
    for fa in free_agents:
        players[fa.id] = fa
    
    return {
        'league': league,
        'teams': teams,
        'players': players,
        'free_agent_ids': [fa.id for fa in free_agents]
    }
