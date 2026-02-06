"""
Match simulation engine for Rocket League GM Simulator.
Uses weighted RNG based on player attributes to generate realistic match outcomes.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import random
import math

from ..models.player import Player, PlayerStats
from ..models.team import Team


@dataclass
class PlayerMatchStats:
    """Individual player stats for a single game."""
    player_id: str
    goals: int = 0
    assists: int = 0
    saves: int = 0
    shots: int = 0
    demos: int = 0
    rating: float = 6.0  # Match rating 0-10
    
    def to_dict(self) -> dict:
        return {
            'player_id': self.player_id,
            'goals': self.goals,
            'assists': self.assists,
            'saves': self.saves,
            'shots': self.shots,
            'demos': self.demos,
            'rating': round(self.rating, 1)
        }


@dataclass
class GameResult:
    """Result of a single game (one game in a series)."""
    home_score: int
    away_score: int
    home_stats: List[PlayerMatchStats]
    away_stats: List[PlayerMatchStats]
    overtime: bool = False
    
    @property
    def winner(self) -> str:
        return "home" if self.home_score > self.away_score else "away"
    
    def to_dict(self) -> dict:
        return {
            'home_score': self.home_score,
            'away_score': self.away_score,
            'home_stats': [s.to_dict() for s in self.home_stats],
            'away_stats': [s.to_dict() for s in self.away_stats],
            'overtime': self.overtime
        }


@dataclass
class SeriesResult:
    """Result of a best-of-N series."""
    home_team_id: str
    away_team_id: str
    home_wins: int
    away_wins: int
    games: List[GameResult]
    best_of: int
    
    @property
    def winner_id(self) -> str:
        return self.home_team_id if self.home_wins > self.away_wins else self.away_team_id
    
    @property
    def loser_id(self) -> str:
        return self.away_team_id if self.home_wins > self.away_wins else self.home_team_id
    
    @property
    def score(self) -> str:
        return f"{self.home_wins}-{self.away_wins}"
    
    def total_goals(self, team_id: str) -> int:
        if team_id == self.home_team_id:
            return sum(g.home_score for g in self.games)
        return sum(g.away_score for g in self.games)
    
    def to_dict(self) -> dict:
        return {
            'home_team_id': self.home_team_id,
            'away_team_id': self.away_team_id,
            'home_wins': self.home_wins,
            'away_wins': self.away_wins,
            'games': [g.to_dict() for g in self.games],
            'best_of': self.best_of
        }


class MatchEngine:
    """
    Simulates Rocket League matches using weighted RNG.
    """
    
    def __init__(self):
        # Simulation parameters
        self.base_scoring_chances = 12  # Average chances per team per game
        self.base_conversion_rate = 0.25  # Base chance to score on a chance
        self.overtime_golden_goal = True
        
    def simulate_series(
        self,
        home_team: Team,
        away_team: Team,
        home_players: List[Player],
        away_players: List[Player],
        best_of: int = 5
    ) -> SeriesResult:
        """
        Simulate a best-of-N series between two teams.
        """
        wins_needed = (best_of // 2) + 1
        home_wins = 0
        away_wins = 0
        games = []
        
        while home_wins < wins_needed and away_wins < wins_needed:
            game = self.simulate_game(
                home_team, away_team,
                home_players, away_players,
                series_game_num=len(games) + 1,
                is_elimination=(home_wins == wins_needed - 1 or away_wins == wins_needed - 1)
            )
            games.append(game)
            
            if game.winner == "home":
                home_wins += 1
            else:
                away_wins += 1
        
        return SeriesResult(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_wins=home_wins,
            away_wins=away_wins,
            games=games,
            best_of=best_of
        )
    
    def simulate_game(
        self,
        home_team: Team,
        away_team: Team,
        home_players: List[Player],
        away_players: List[Player],
        series_game_num: int = 1,
        is_elimination: bool = False
    ) -> GameResult:
        """
        Simulate a single game between two teams.
        """
        # Calculate team strengths
        home_off = self._team_offensive_rating(home_players, home_team.chemistry)
        home_def = self._team_defensive_rating(home_players, home_team.chemistry)
        away_off = self._team_offensive_rating(away_players, away_team.chemistry)
        away_def = self._team_defensive_rating(away_players, away_team.chemistry)
        
        # Simulate scoring chances for each team
        home_chances = self._generate_chances(home_off, away_def)
        away_chances = self._generate_chances(away_off, home_def)
        
        # Convert chances to goals
        home_goals, home_stats = self._resolve_chances(
            home_chances, home_players, away_players, home_team.chemistry, is_elimination
        )
        away_goals, away_stats = self._resolve_chances(
            away_chances, away_players, home_players, away_team.chemistry, is_elimination
        )
        
        # Handle overtime if tied
        overtime = False
        while home_goals == away_goals:
            overtime = True
            # Golden goal - each team gets fewer chances in OT
            ot_home_chances = max(1, self._generate_chances(home_off, away_def) // 3)
            ot_away_chances = max(1, self._generate_chances(away_off, home_def) // 3)
            
            ot_home_goals, ot_home_stats = self._resolve_chances(
                ot_home_chances, home_players, away_players, home_team.chemistry, True
            )
            ot_away_goals, ot_away_stats = self._resolve_chances(
                ot_away_chances, away_players, home_players, away_team.chemistry, True
            )
            
            # Merge OT stats
            for i, stat in enumerate(ot_home_stats):
                home_stats[i].goals += stat.goals
                home_stats[i].shots += stat.shots
            for i, stat in enumerate(ot_away_stats):
                away_stats[i].goals += stat.goals
                away_stats[i].shots += stat.shots
            
            home_goals += ot_home_goals
            away_goals += ot_away_goals
            
            # If still tied, continue OT
            if home_goals == away_goals:
                continue
        
        # Distribute saves based on defensive actions
        self._distribute_saves(home_stats, away_goals, home_players)
        self._distribute_saves(away_stats, home_goals, away_players)
        
        # Calculate player ratings
        self._calculate_ratings(home_stats, home_goals, away_goals)
        self._calculate_ratings(away_stats, away_goals, home_goals)
        
        return GameResult(
            home_score=home_goals,
            away_score=away_goals,
            home_stats=home_stats,
            away_stats=away_stats,
            overtime=overtime
        )
    
    def _team_offensive_rating(self, players: List[Player], chemistry: int) -> float:
        """Calculate team's offensive strength."""
        if not players:
            return 50.0
        
        ratings = [p.attributes.offensive_rating() for p in players[:3]]
        base = sum(ratings) / len(ratings)
        
        # Chemistry bonus
        chem_mod = 1.0 + (chemistry - 50) * 0.003
        
        # Passing/teamwork bonus
        teamwork = sum(p.attributes.teamwork for p in players[:3]) / 3
        team_mod = 1.0 + (teamwork - 50) * 0.002
        
        return base * chem_mod * team_mod
    
    def _team_defensive_rating(self, players: List[Player], chemistry: int) -> float:
        """Calculate team's defensive strength."""
        if not players:
            return 50.0
        
        ratings = [p.attributes.defensive_rating() for p in players[:3]]
        base = sum(ratings) / len(ratings)
        
        # Chemistry bonus
        chem_mod = 1.0 + (chemistry - 50) * 0.003
        
        return base * chem_mod
    
    def _generate_chances(self, offensive: float, defensive: float) -> int:
        """Generate number of scoring chances based on team strengths."""
        # Base chances modified by offensive vs defensive rating
        ratio = offensive / max(defensive, 1)
        modifier = 0.8 + (ratio * 0.4)  # Range roughly 0.8 to 1.6
        
        base = self.base_scoring_chances * modifier
        
        # Add randomness
        variance = random.gauss(0, 2)
        chances = int(max(5, base + variance))
        
        return chances
    
    def _resolve_chances(
        self,
        num_chances: int,
        attacking_players: List[Player],
        defending_players: List[Player],
        chemistry: int,
        is_clutch: bool
    ) -> Tuple[int, List[PlayerMatchStats]]:
        """
        Resolve scoring chances into goals and individual stats.
        Returns (total_goals, player_stats_list)
        """
        goals = 0
        
        # Initialize stats for each player
        stats = [PlayerMatchStats(player_id=p.id) for p in attacking_players[:3]]
        
        for _ in range(num_chances):
            # Select primary attacker (weighted by offensive attributes)
            attacker_idx = self._select_attacker(attacking_players[:3])
            attacker = attacking_players[attacker_idx]
            
            # Calculate conversion probability
            conversion_prob = self._calculate_conversion_prob(
                attacker, defending_players[:3], chemistry, is_clutch
            )
            
            # Apply consistency variance
            consistency_mod = self._apply_consistency(attacker.attributes.consistency)
            final_prob = conversion_prob * consistency_mod
            
            # Record shot
            stats[attacker_idx].shots += 1
            
            # Roll for goal
            if random.random() < final_prob:
                goals += 1
                stats[attacker_idx].goals += 1
                
                # Chance for assist
                if random.random() < 0.6 and len(attacking_players) >= 2:
                    assister_idx = self._select_assister(attacking_players[:3], attacker_idx)
                    stats[assister_idx].assists += 1
        
        return goals, stats
    
    def _select_attacker(self, players: List[Player]) -> int:
        """Select which player takes the shot (weighted by offensive ability)."""
        weights = []
        for p in players:
            weight = (p.attributes.finishing * 0.4 + 
                     p.attributes.shooting * 0.3 +
                     p.attributes.creativity * 0.3)
            weights.append(weight)
        
        total = sum(weights)
        r = random.random() * total
        cumulative = 0
        
        for i, w in enumerate(weights):
            cumulative += w
            if r <= cumulative:
                return i
        
        return 0
    
    def _select_assister(self, players: List[Player], exclude_idx: int) -> int:
        """Select assist player (weighted by passing ability)."""
        indices = [i for i in range(len(players)) if i != exclude_idx]
        
        if not indices:
            return 0
        
        weights = []
        for i in indices:
            weight = (players[i].attributes.passing * 0.5 +
                     players[i].attributes.creativity * 0.3 +
                     players[i].attributes.game_reading * 0.2)
            weights.append(weight)
        
        total = sum(weights)
        r = random.random() * total
        cumulative = 0
        
        for i, w in enumerate(weights):
            cumulative += w
            if r <= cumulative:
                return indices[i]
        
        return indices[0]
    
    def _calculate_conversion_prob(
        self,
        attacker: Player,
        defenders: List[Player],
        chemistry: int,
        is_clutch: bool
    ) -> float:
        """Calculate probability of converting a chance to a goal."""
        # Attacker's shooting ability
        attack_score = (attacker.attributes.finishing * 0.4 +
                       attacker.attributes.shooting * 0.3 +
                       attacker.attributes.creativity * 0.2 +
                       attacker.attributes.aerial * 0.1)
        
        # Defenders' saving ability (average)
        if defenders:
            defend_score = sum(
                (d.attributes.saving * 0.5 + d.attributes.challenging * 0.3 +
                 d.attributes.positioning * 0.2)
                for d in defenders
            ) / len(defenders)
        else:
            defend_score = 50
        
        # Base probability
        ratio = attack_score / max(defend_score, 1)
        base_prob = self.base_conversion_rate * (0.5 + ratio * 0.5)
        
        # Clutch modifier
        if is_clutch:
            clutch_mod = 1.0 + (attacker.attributes.clutch - 50) * 0.005
            base_prob *= clutch_mod
        
        # Cap probability
        return max(0.05, min(0.60, base_prob))
    
    def _apply_consistency(self, consistency: int) -> float:
        """
        Apply consistency-based variance.
        High consistency = performs near expected level.
        Low consistency = more variance (could be brilliant or terrible).
        """
        # Variance inversely proportional to consistency
        variance = (100 - consistency) / 100 * 0.4
        modifier = random.gauss(1.0, variance)
        
        return max(0.5, min(1.5, modifier))
    
    def _distribute_saves(
        self,
        stats: List[PlayerMatchStats],
        opponent_goals: int,
        players: List[Player]
    ):
        """Distribute saves among players based on defensive attributes."""
        # Estimate total shots against (goals + saves)
        # Typical shot conversion is ~30%, so saves = shots * 0.7
        estimated_shots_against = int(opponent_goals / 0.3) if opponent_goals > 0 else random.randint(8, 15)
        total_saves = max(0, estimated_shots_against - opponent_goals)
        
        if total_saves == 0 or not players:
            return
        
        # Weight by saving attribute
        weights = [p.attributes.saving for p in players[:3]]
        total_weight = sum(weights)
        
        for i, stat in enumerate(stats[:3]):
            if total_weight > 0:
                player_saves = int(total_saves * (weights[i] / total_weight))
                # Add some randomness
                player_saves += random.randint(-1, 1)
                stat.saves = max(0, player_saves)
    
    def _calculate_ratings(
        self,
        stats: List[PlayerMatchStats],
        team_goals: int,
        opponent_goals: int
    ):
        """Calculate match ratings for each player."""
        won = team_goals > opponent_goals
        
        for stat in stats:
            # Base rating
            rating = 6.0
            
            # Goals contribution
            rating += stat.goals * 0.8
            rating += stat.assists * 0.4
            rating += stat.saves * 0.2
            
            # Efficiency
            if stat.shots > 0:
                shooting_pct = stat.goals / stat.shots
                if shooting_pct > 0.4:
                    rating += 0.5
                elif shooting_pct < 0.15:
                    rating -= 0.3
            
            # Win bonus
            if won:
                rating += 0.5
            else:
                rating -= 0.3
            
            # Cap rating
            stat.rating = max(1.0, min(10.0, rating))


def simulate_match(
    home_team: Team,
    away_team: Team,
    home_players: List[Player],
    away_players: List[Player],
    best_of: int = 5
) -> SeriesResult:
    """
    Convenience function to simulate a match.
    """
    engine = MatchEngine()
    return engine.simulate_series(
        home_team, away_team,
        home_players, away_players,
        best_of
    )
