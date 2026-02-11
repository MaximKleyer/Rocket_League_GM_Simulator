"""
Team model for Rocket League GM Simulator.
Manages roster, chemistry, finances, and team-level statistics.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
import uuid


@dataclass
class TrainingAllocation:
    """Training focus allocation - imported here to avoid circular imports."""
    mechanical: int = 34
    game_sense: int = 33
    mental: int = 33
    
    def set_allocation(self, mechanical: int, game_sense: int, mental: int) -> bool:
        if mechanical + game_sense + mental != 100:
            return False
        if any(x < 0 or x > 100 for x in [mechanical, game_sense, mental]):
            return False
        self.mechanical = mechanical
        self.game_sense = game_sense
        self.mental = mental
        return True
    
    def reset_to_default(self):
        self.mechanical = 34
        self.game_sense = 33
        self.mental = 33
    
    def to_dict(self) -> dict:
        return {'mechanical': self.mechanical, 'game_sense': self.game_sense, 'mental': self.mental}
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TrainingAllocation':
        return cls(mechanical=data.get('mechanical', 34), 
                   game_sense=data.get('game_sense', 33), 
                   mental=data.get('mental', 33))


@dataclass
class Contract:
    """Player contract details."""
    player_id: str
    team_id: str
    salary: int  # Yearly salary in dollars
    years: int  # Years remaining on contract (1-5)
    buyout: int  # Buyout clause amount
    
    # Legacy support for old saves
    length: int = 0  # Deprecated, use years
    
    def __post_init__(self):
        # Convert old monthly contracts to yearly
        if self.length > 0 and self.years == 0:
            self.years = max(1, self.length // 12)
            self.salary = self.salary * 12  # Convert monthly to yearly
            self.length = 0
    
    def yearly_cost(self) -> int:
        return self.salary
    
    def total_value(self) -> int:
        return self.salary * self.years
    
    def to_dict(self) -> dict:
        return {
            'player_id': self.player_id,
            'team_id': self.team_id,
            'salary': self.salary,
            'years': self.years,
            'buyout': self.buyout
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Contract':
        # Handle legacy 'length' field
        if 'length' in data and 'years' not in data:
            data['years'] = max(1, data.get('length', 12) // 12)
            data['salary'] = data.get('salary', 0) * 12
        return cls(
            player_id=data['player_id'],
            team_id=data['team_id'],
            salary=data.get('salary', 0),
            years=data.get('years', 1),
            buyout=data.get('buyout', 0)
        )


@dataclass  
class TeamStats:
    """Team season statistics."""
    wins: int = 0
    losses: int = 0
    series_wins: int = 0
    series_losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    
    # Tournament placements
    regional_placements: List[int] = field(default_factory=list)  # e.g., [1, 3, 2]
    major_placement: Optional[int] = None
    
    @property
    def win_pct(self) -> float:
        total = self.wins + self.losses
        return (self.wins / total * 100) if total > 0 else 0.0
    
    @property
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against
    
    @property
    def series_record(self) -> str:
        return f"{self.series_wins}-{self.series_losses}"
    
    @property
    def game_record(self) -> str:
        return f"{self.wins}-{self.losses}"
    
    def to_dict(self) -> dict:
        return {
            'wins': self.wins, 'losses': self.losses,
            'series_wins': self.series_wins, 'series_losses': self.series_losses,
            'goals_for': self.goals_for, 'goals_against': self.goals_against,
            'regional_placements': self.regional_placements,
            'major_placement': self.major_placement
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TeamStats':
        return cls(**data)


@dataclass
class Finances:
    """Team financial state."""
    balance: int = 100000  # Current cash
    monthly_budget: int = 25000  # Spending limit per month
    
    # Revenue streams
    sponsor_income: int = 10000  # Monthly
    merch_income: int = 2000  # Monthly
    content_income: int = 3000  # Monthly (streaming, YouTube)
    
    # Prize pool winnings (added when earned)
    prize_earnings: int = 0
    
    @property
    def monthly_revenue(self) -> int:
        return self.sponsor_income + self.merch_income + self.content_income
    
    @property
    def yearly_budget(self) -> int:
        """Yearly salary budget."""
        return self.monthly_budget * 12
    
    def process_month(self, salary_expenses: int) -> int:
        """Process monthly finances. Returns new balance."""
        self.balance += self.monthly_revenue
        self.balance -= salary_expenses
        return self.balance
    
    def add_prize_money(self, amount: int):
        self.prize_earnings += amount
        self.balance += amount
    
    def can_afford(self, amount: int) -> bool:
        return self.balance >= amount
    
    def to_dict(self) -> dict:
        return {
            'balance': self.balance, 'monthly_budget': self.monthly_budget,
            'sponsor_income': self.sponsor_income, 'merch_income': self.merch_income,
            'content_income': self.content_income, 'prize_earnings': self.prize_earnings
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Finances':
        return cls(**data)


@dataclass
class Team:
    """
    A Rocket League esports team/organization.
    """
    id: str
    name: str
    abbreviation: str  # 3-4 letter tag (e.g., "NRG", "G2", "FAZE")
    region: str  # NA, EU, SAM, OCE, MENA, APAC, SSA
    
    # Roster: list of player IDs (active roster = first 3)
    roster: List[str] = field(default_factory=list)
    
    # Contracts keyed by player_id
    contracts: Dict[str, Contract] = field(default_factory=dict)
    
    # Team state
    chemistry: int = 50  # 0-100, builds over time with stable roster
    reputation: int = 50  # 0-100, affects free agent interest
    fan_base: int = 50  # 0-100, affects revenue
    
    # Stats
    season_stats: TeamStats = field(default_factory=TeamStats)
    all_time_stats: TeamStats = field(default_factory=TeamStats)
    
    # Finances
    finances: Finances = field(default_factory=Finances)
    
    # Elo rating for simulation
    elo: int = 1500
    
    # Is this the player's team?
    is_player_team: bool = False
    
    # Training allocation
    training: TrainingAllocation = field(default_factory=TrainingAllocation)
    
    # Previous roster for chemistry calculations (stored at split boundaries)
    previous_roster: List[str] = field(default_factory=list)
    
    # Win/loss streak tracking (positive = win streak, negative = lose streak)
    streak: int = 0
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]
    
    @property
    def active_roster(self) -> List[str]:
        """First 3 players are active roster."""
        return self.roster[:3]
    
    @property
    def substitute(self) -> Optional[str]:
        """4th player is substitute."""
        return self.roster[3] if len(self.roster) > 3 else None
    
    @property
    def roster_size(self) -> int:
        return len(self.roster)
    
    @property
    def yearly_salary(self) -> int:
        """Total yearly salary obligations."""
        return sum(c.yearly_cost() for c in self.contracts.values())
    
    @property
    def monthly_salary(self) -> int:
        """Total monthly salary obligations (for display)."""
        return self.yearly_salary // 12
    
    @property
    def salary_cap_space(self) -> int:
        """Remaining yearly budget space."""
        return self.finances.yearly_budget - self.yearly_salary
    
    def add_player(self, player_id: str, contract: Contract):
        """Sign a player to the roster."""
        if len(self.roster) >= 5:
            raise ValueError("Roster full (max 5 players)")
        
        self.roster.append(player_id)
        self.contracts[player_id] = contract
        
        # Chemistry drops with roster changes
        self.chemistry = max(0, self.chemistry - 10)
    
    def remove_player(self, player_id: str) -> Optional[Contract]:
        """Release a player from the roster."""
        if player_id not in self.roster:
            return None
        
        self.roster.remove(player_id)
        contract = self.contracts.pop(player_id, None)
        
        # Chemistry drops with roster changes
        self.chemistry = max(0, self.chemistry - 15)
        
        return contract
    
    def swap_roster_position(self, idx1: int, idx2: int):
        """Swap two players' positions in roster order."""
        if 0 <= idx1 < len(self.roster) and 0 <= idx2 < len(self.roster):
            self.roster[idx1], self.roster[idx2] = self.roster[idx2], self.roster[idx1]
    
    def update_chemistry(self, games_played_together: int = 1):
        """
        Chemistry builds slowly over time with stable roster.
        +1 for every ~5 games played together, capped at 100.
        """
        gain = games_played_together // 5
        self.chemistry = min(100, self.chemistry + gain)
    
    def update_elo(self, opponent_elo: int, won: bool, k_factor: int = 32):
        """Update Elo rating after a match/series."""
        expected = 1 / (1 + 10 ** ((opponent_elo - self.elo) / 400))
        actual = 1.0 if won else 0.0
        self.elo = int(self.elo + k_factor * (actual - expected))
    
    def process_month(self):
        """Process end-of-month finances."""
        self.finances.process_month(self.monthly_salary)
        
        # Decrement contract lengths
        expired = []
        for pid, contract in self.contracts.items():
            contract.length -= 1
            if contract.length <= 0:
                expired.append(pid)
        
        return expired  # List of player_ids whose contracts expired
    
    def reset_season_stats(self):
        """Reset stats for new season."""
        # Add to all-time before reset
        self.all_time_stats.wins += self.season_stats.wins
        self.all_time_stats.losses += self.season_stats.losses
        self.all_time_stats.series_wins += self.season_stats.series_wins
        self.all_time_stats.series_losses += self.season_stats.series_losses
        self.all_time_stats.goals_for += self.season_stats.goals_for
        self.all_time_stats.goals_against += self.season_stats.goals_against
        
        self.season_stats = TeamStats()
    
    def team_overall(self, players: Dict[str, 'Player']) -> int:
        """
        Calculate team overall from active roster players.
        Requires dict of player_id -> Player objects.
        """
        if not self.active_roster:
            return 0
        
        ratings = []
        for pid in self.active_roster:
            if pid in players:
                ratings.append(players[pid].overall)
        
        if not ratings:
            return 0
        
        # Average with chemistry bonus
        base = sum(ratings) / len(ratings)
        chem_bonus = (self.chemistry - 50) * 0.1  # +/- 5 points max
        return int(base + chem_bonus)
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'abbreviation': self.abbreviation,
            'region': self.region,
            'roster': self.roster,
            'contracts': {k: v.to_dict() for k, v in self.contracts.items()},
            'chemistry': self.chemistry,
            'reputation': self.reputation,
            'fan_base': self.fan_base,
            'season_stats': self.season_stats.to_dict(),
            'all_time_stats': self.all_time_stats.to_dict(),
            'finances': self.finances.to_dict(),
            'elo': self.elo,
            'is_player_team': self.is_player_team,
            'training': self.training.to_dict(),
            'previous_roster': self.previous_roster,
            'streak': self.streak
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Team':
        team = cls(
            id=data['id'],
            name=data['name'],
            abbreviation=data['abbreviation'],
            region=data['region'],
            roster=data['roster'],
            chemistry=data.get('chemistry', 50),
            reputation=data.get('reputation', 50),
            fan_base=data.get('fan_base', 50),
            elo=data.get('elo', 1500),
            is_player_team=data.get('is_player_team', False),
            previous_roster=data.get('previous_roster', []),
            streak=data.get('streak', 0)
        )
        
        team.contracts = {k: Contract.from_dict(v) for k, v in data.get('contracts', {}).items()}
        team.season_stats = TeamStats.from_dict(data.get('season_stats', {}))
        team.all_time_stats = TeamStats.from_dict(data.get('all_time_stats', {}))
        team.finances = Finances.from_dict(data.get('finances', {}))
        
        if 'training' in data:
            team.training = TrainingAllocation.from_dict(data['training'])
        
        return team
    
    def __repr__(self):
        return f"Team({self.abbreviation} - {self.name}, {self.region})"
