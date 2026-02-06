"""
Player model for Rocket League GM Simulator.
Attributes designed specifically for competitive Rocket League.
"""

from dataclasses import dataclass, field
from typing import Optional
import random
import uuid


@dataclass
class PlayerAttributes:
    """
    20-attribute system tailored to Rocket League.
    All attributes on 1-99 scale.
    """
    # Mechanical Skills (6)
    aerial: int = 50          # Air control, air dribbles
    ground_control: int = 50  # Dribbling, flicks
    shooting: int = 50        # Power, placement
    advanced_mechanics: int = 50  # Flip resets, ceiling shots
    recovery: int = 50        # Wave dashes, half-flips, landing
    car_control: int = 50     # General movement precision
    
    # Game Sense (5)
    positioning: int = 50     # Rotation, being in right place
    game_reading: int = 50    # Anticipating plays
    decision_making: int = 50 # When to challenge vs wait
    passing: int = 50         # Vision and execution of team plays
    boost_management: int = 50  # Efficient collection/usage
    
    # Defensive/Offensive (4)
    saving: int = 50          # Shot-stopping
    challenging: int = 50     # 50/50s, shadow defense
    finishing: int = 50       # Converting chances
    creativity: int = 50      # Creating chances, playmaking
    
    # Meta Attributes (5)
    speed: int = 50           # Pace of play
    consistency: int = 50     # Performance reliability (KEY attribute)
    clutch: int = 50          # Performance in high-pressure moments
    mental: int = 50          # Tilt resistance, bounce-back ability
    teamwork: int = 50        # Communication, synergy modifier
    
    def overall(self) -> int:
        """Calculate overall rating (weighted average)."""
        # Game sense weighted higher than pure mechanics
        mechanical = (self.aerial + self.ground_control + self.shooting + 
                     self.advanced_mechanics + self.recovery + self.car_control) / 6
        game_sense = (self.positioning + self.game_reading + self.decision_making +
                     self.passing + self.boost_management) / 5
        defensive = (self.saving + self.challenging) / 2
        offensive = (self.finishing + self.creativity) / 2
        meta = (self.speed + self.consistency + self.clutch + self.mental + self.teamwork) / 5
        
        # Weights: game_sense > mechanics > consistency > others
        return int(mechanical * 0.25 + game_sense * 0.30 + defensive * 0.10 + 
                   offensive * 0.15 + meta * 0.20)
    
    def offensive_rating(self) -> int:
        """Rating for offensive calculations."""
        return int((self.shooting * 0.25 + self.finishing * 0.30 + self.creativity * 0.20 +
                   self.aerial * 0.15 + self.ground_control * 0.10))
    
    def defensive_rating(self) -> int:
        """Rating for defensive calculations."""
        return int((self.saving * 0.35 + self.challenging * 0.25 + self.positioning * 0.25 +
                   self.game_reading * 0.15))
    
    def to_dict(self) -> dict:
        return {
            'aerial': self.aerial, 'ground_control': self.ground_control,
            'shooting': self.shooting, 'advanced_mechanics': self.advanced_mechanics,
            'recovery': self.recovery, 'car_control': self.car_control,
            'positioning': self.positioning, 'game_reading': self.game_reading,
            'decision_making': self.decision_making, 'passing': self.passing,
            'boost_management': self.boost_management, 'saving': self.saving,
            'challenging': self.challenging, 'finishing': self.finishing,
            'creativity': self.creativity, 'speed': self.speed,
            'consistency': self.consistency, 'clutch': self.clutch,
            'mental': self.mental, 'teamwork': self.teamwork
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PlayerAttributes':
        return cls(**data)


@dataclass
class HiddenAttributes:
    """Hidden attributes for development and scouting."""
    potential: int = 70       # Maximum CA ceiling (1-99)
    ambition: int = 50        # Training ethic, development rate
    adaptability: int = 50    # Adjustment to new teammates/meta
    injury_prone: int = 20    # RSI/burnout risk (lower is better)
    
    def to_dict(self) -> dict:
        return {'potential': self.potential, 'ambition': self.ambition,
                'adaptability': self.adaptability, 'injury_prone': self.injury_prone}
    
    @classmethod
    def from_dict(cls, data: dict) -> 'HiddenAttributes':
        return cls(**data)


@dataclass
class PlayerStats:
    """Career and season statistics."""
    games_played: int = 0
    goals: int = 0
    assists: int = 0
    saves: int = 0
    shots: int = 0
    demos: int = 0
    mvps: int = 0
    
    # Derived stats
    @property
    def shooting_pct(self) -> float:
        return (self.goals / self.shots * 100) if self.shots > 0 else 0.0
    
    @property
    def goals_per_game(self) -> float:
        return self.goals / self.games_played if self.games_played > 0 else 0.0
    
    @property
    def assists_per_game(self) -> float:
        return self.assists / self.games_played if self.games_played > 0 else 0.0
    
    @property
    def saves_per_game(self) -> float:
        return self.saves / self.games_played if self.games_played > 0 else 0.0
    
    def to_dict(self) -> dict:
        return {'games_played': self.games_played, 'goals': self.goals,
                'assists': self.assists, 'saves': self.saves, 'shots': self.shots,
                'demos': self.demos, 'mvps': self.mvps}
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PlayerStats':
        return cls(**data)


@dataclass
class Player:
    """
    A Rocket League esports player.
    """
    id: str
    name: str
    age: int
    nationality: str
    
    attributes: PlayerAttributes
    hidden: HiddenAttributes
    
    # Career tracking
    career_stats: PlayerStats = field(default_factory=PlayerStats)
    season_stats: PlayerStats = field(default_factory=PlayerStats)
    
    # Contract/team info (managed externally)
    team_id: Optional[str] = None
    
    # Development tracking
    games_since_last_development: int = 0
    
    # Morale and form (0-100)
    morale: int = 70
    form: int = 50  # Recent performance trend
    
    # Role tendency: "offensive", "defensive", "playmaker", "allrounder"
    role: str = "allrounder"
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]
    
    @property
    def overall(self) -> int:
        return self.attributes.overall()
    
    @property
    def market_value(self) -> int:
        """Estimate market value based on attributes, age, potential."""
        base = self.overall * 1000
        
        # Age modifier (peak 18-23)
        if self.age < 18:
            age_mod = 0.8 + (self.age - 15) * 0.1
        elif self.age <= 23:
            age_mod = 1.1
        elif self.age <= 26:
            age_mod = 1.0 - (self.age - 23) * 0.05
        else:
            age_mod = 0.7 - (self.age - 26) * 0.1
        
        # Potential modifier
        potential_mod = 1.0 + (self.hidden.potential - 70) * 0.01
        
        return int(base * age_mod * potential_mod)
    
    def develop(self, training_quality: int = 50) -> dict:
        """
        Process player development. Called periodically.
        Returns dict of attribute changes.
        """
        changes = {}
        
        # Can't develop past potential
        if self.overall >= self.hidden.potential:
            return changes
        
        # Development rate based on age
        if self.age < 18:
            base_rate = 0.15
        elif self.age <= 21:
            base_rate = 0.10
        elif self.age <= 24:
            base_rate = 0.05
        else:
            base_rate = 0.02
        
        # Modify by ambition and training
        rate = base_rate * (self.hidden.ambition / 50) * (training_quality / 50)
        
        # Randomly improve 1-3 attributes
        attr_names = list(self.attributes.to_dict().keys())
        num_improvements = random.randint(1, 3)
        
        for _ in range(num_improvements):
            if random.random() < rate:
                attr = random.choice(attr_names)
                current = getattr(self.attributes, attr)
                if current < self.hidden.potential:
                    improvement = random.randint(1, 2)
                    new_val = min(99, current + improvement)
                    setattr(self.attributes, attr, new_val)
                    changes[attr] = improvement
        
        return changes
    
    def age_one_year(self) -> dict:
        """
        Process yearly aging. Returns regression changes.
        """
        self.age += 1
        regressions = {}
        
        # Regression starts at 24, accelerates after 26
        if self.age >= 24:
            if self.age >= 27:
                regression_chance = 0.4
                regression_amount = (2, 4)
            elif self.age >= 24:
                regression_chance = 0.2
                regression_amount = (1, 2)
            else:
                return regressions
            
            # Mechanical attributes regress faster than game sense
            mechanical_attrs = ['aerial', 'ground_control', 'shooting', 
                               'advanced_mechanics', 'recovery', 'car_control', 'speed']
            
            for attr in mechanical_attrs:
                if random.random() < regression_chance:
                    current = getattr(self.attributes, attr)
                    decrease = random.randint(*regression_amount)
                    new_val = max(1, current - decrease)
                    setattr(self.attributes, attr, new_val)
                    regressions[attr] = -decrease
        
        return regressions
    
    def reset_season_stats(self):
        """Reset season stats for new season."""
        self.season_stats = PlayerStats()
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'age': self.age,
            'nationality': self.nationality,
            'attributes': self.attributes.to_dict(),
            'hidden': self.hidden.to_dict(),
            'career_stats': self.career_stats.to_dict(),
            'season_stats': self.season_stats.to_dict(),
            'team_id': self.team_id,
            'morale': self.morale,
            'form': self.form,
            'role': self.role
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Player':
        return cls(
            id=data['id'],
            name=data['name'],
            age=data['age'],
            nationality=data['nationality'],
            attributes=PlayerAttributes.from_dict(data['attributes']),
            hidden=HiddenAttributes.from_dict(data['hidden']),
            career_stats=PlayerStats.from_dict(data['career_stats']),
            season_stats=PlayerStats.from_dict(data['season_stats']),
            team_id=data.get('team_id'),
            morale=data.get('morale', 70),
            form=data.get('form', 50),
            role=data.get('role', 'allrounder')
        )
    
    def __repr__(self):
        return f"Player({self.name}, {self.age}yo, OVR:{self.overall})"


def generate_random_player(name: str, age: int = None, tier: str = "average") -> Player:
    """
    Generate a random player with attributes based on tier.
    Tiers: "star" (75-90), "good" (65-80), "average" (50-70), "prospect" (40-60)
    """
    if age is None:
        age = random.randint(17, 28)
    
    tier_ranges = {
        "star": (75, 90),
        "good": (65, 80),
        "average": (50, 70),
        "prospect": (40, 60)
    }
    
    low, high = tier_ranges.get(tier, (50, 70))
    
    # Generate attributes with some variance
    attrs = {}
    for attr in PlayerAttributes.__dataclass_fields__:
        base = random.randint(low, high)
        variance = random.randint(-5, 5)
        attrs[attr] = max(1, min(99, base + variance))
    
    # Hidden attributes
    potential = min(99, random.randint(low + 5, high + 15))
    
    nationalities = ["USA", "France", "UK", "Germany", "Spain", "Canada", 
                    "Brazil", "Sweden", "Denmark", "Saudi Arabia", "Australia"]
    
    return Player(
        id=str(uuid.uuid4())[:8],
        name=name,
        age=age,
        nationality=random.choice(nationalities),
        attributes=PlayerAttributes(**attrs),
        hidden=HiddenAttributes(
            potential=potential,
            ambition=random.randint(40, 80),
            adaptability=random.randint(40, 70),
            injury_prone=random.randint(10, 40)
        ),
        role=random.choice(["offensive", "defensive", "playmaker", "allrounder"])
    )
