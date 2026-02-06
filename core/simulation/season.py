"""
League and Season management for Rocket League GM Simulator.
Handles scheduling, standings, and season progression.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import random
import itertools

from ..models.player import Player
from ..models.team import Team
from .match_engine import MatchEngine, SeriesResult


class SeasonPhase(Enum):
    OFFSEASON = "offseason"
    PRESEASON = "preseason"
    # Split 1
    SPLIT1_REGIONAL_1 = "split1_regional_1"
    SPLIT1_REGIONAL_2 = "split1_regional_2"
    SPLIT1_REGIONAL_3 = "split1_regional_3"
    SPLIT1_MAJOR = "split1_major"
    # Between splits
    SPLIT_BREAK = "split_break"
    # Split 2
    SPLIT2_REGIONAL_1 = "split2_regional_1"
    SPLIT2_REGIONAL_2 = "split2_regional_2"
    SPLIT2_REGIONAL_3 = "split2_regional_3"
    SPLIT2_MAJOR = "split2_major"
    # Worlds
    WORLDS = "worlds"
    SEASON_END = "season_end"


# Helper lists for phase identification
REGIONAL_PHASES = [
    SeasonPhase.SPLIT1_REGIONAL_1,
    SeasonPhase.SPLIT1_REGIONAL_2,
    SeasonPhase.SPLIT1_REGIONAL_3,
    SeasonPhase.SPLIT2_REGIONAL_1,
    SeasonPhase.SPLIT2_REGIONAL_2,
    SeasonPhase.SPLIT2_REGIONAL_3,
]

MAJOR_PHASES = [
    SeasonPhase.SPLIT1_MAJOR,
    SeasonPhase.SPLIT2_MAJOR,
    SeasonPhase.WORLDS,
]


@dataclass
class Standing:
    """Team standing in a league/tournament."""
    team_id: str
    wins: int = 0
    losses: int = 0
    game_wins: int = 0
    game_losses: int = 0
    points: int = 0  # For point-based systems
    
    @property
    def win_pct(self) -> float:
        total = self.wins + self.losses
        return self.wins / total if total > 0 else 0.0
    
    @property
    def game_diff(self) -> int:
        return self.game_wins - self.game_losses
    
    def __lt__(self, other: 'Standing') -> bool:
        # Sort by: points > wins > game_diff > game_wins
        if self.points != other.points:
            return self.points < other.points
        if self.wins != other.wins:
            return self.wins < other.wins
        if self.game_diff != other.game_diff:
            return self.game_diff < other.game_diff
        return self.game_wins < other.game_wins


@dataclass
class ScheduledMatch:
    """A scheduled match in the season."""
    match_id: str
    home_team_id: str
    away_team_id: str
    week: int
    phase: SeasonPhase
    best_of: int = 5
    result: Optional[SeriesResult] = None
    
    @property
    def is_played(self) -> bool:
        return self.result is not None
    
    def to_dict(self) -> dict:
        return {
            'match_id': self.match_id,
            'home_team_id': self.home_team_id,
            'away_team_id': self.away_team_id,
            'week': self.week,
            'phase': self.phase.value,
            'best_of': self.best_of,
            'result': self.result.to_dict() if self.result else None
        }


@dataclass
class League:
    """
    A regional league containing teams.
    """
    id: str
    name: str
    region: str
    team_ids: List[str] = field(default_factory=list)
    
    # Current season state
    current_week: int = 1
    current_phase: SeasonPhase = SeasonPhase.OFFSEASON
    
    # Schedule and standings
    schedule: List[ScheduledMatch] = field(default_factory=list)
    standings: Dict[str, Standing] = field(default_factory=dict)
    
    # Season history
    season_number: int = 1
    champions_history: List[str] = field(default_factory=list)
    
    def add_team(self, team_id: str):
        if team_id not in self.team_ids:
            self.team_ids.append(team_id)
            self.standings[team_id] = Standing(team_id=team_id)
    
    def remove_team(self, team_id: str):
        if team_id in self.team_ids:
            self.team_ids.remove(team_id)
            self.standings.pop(team_id, None)
    
    def generate_schedule(self, phase: SeasonPhase, weeks: int = 3) -> List[ScheduledMatch]:
        """
        Generate round-robin schedule for a phase.
        Each team plays every other team once.
        """
        schedule = []
        match_id_counter = len(self.schedule)
        
        # Generate all matchups
        matchups = list(itertools.combinations(self.team_ids, 2))
        random.shuffle(matchups)
        
        # Distribute across weeks
        matches_per_week = max(1, len(matchups) // weeks)
        
        for i, (team1, team2) in enumerate(matchups):
            week = (i // matches_per_week) + 1
            week = min(week, weeks)  # Cap at max weeks
            
            # Randomize home/away
            if random.random() < 0.5:
                home, away = team1, team2
            else:
                home, away = team2, team1
            
            match = ScheduledMatch(
                match_id=f"{phase.value}_{match_id_counter}",
                home_team_id=home,
                away_team_id=away,
                week=week,
                phase=phase,
                best_of=5
            )
            schedule.append(match)
            match_id_counter += 1
        
        self.schedule.extend(schedule)
        return schedule
    
    def get_week_matches(self, week: int, phase: SeasonPhase = None) -> List[ScheduledMatch]:
        """Get all matches for a specific week."""
        matches = [m for m in self.schedule if m.week == week]
        if phase:
            matches = [m for m in matches if m.phase == phase]
        return matches
    
    def get_unplayed_matches(self) -> List[ScheduledMatch]:
        """Get all unplayed matches."""
        return [m for m in self.schedule if not m.is_played]
    
    def get_sorted_standings(self) -> List[Standing]:
        """Get standings sorted by rank (best first)."""
        return sorted(self.standings.values(), reverse=True)
    
    def generate_major_bracket(self, num_teams: int = 8) -> List[ScheduledMatch]:
        """
        Generate a major/worlds bracket for top teams.
        Single elimination bracket.
        """
        schedule = []
        match_id_counter = len(self.schedule)
        
        # Get top teams by standings
        sorted_standings = self.get_sorted_standings()
        qualified_teams = [s.team_id for s in sorted_standings[:num_teams]]
        
        if len(qualified_teams) < 2:
            return schedule
        
        # Create bracket matchups (1v8, 2v7, 3v6, 4v5 for quarterfinals)
        # Week 1: Quarterfinals
        qf_matchups = []
        for i in range(min(4, len(qualified_teams) // 2)):
            high_seed = qualified_teams[i]
            low_seed = qualified_teams[-(i + 1)] if len(qualified_teams) > i + 4 else qualified_teams[i + 4] if i + 4 < len(qualified_teams) else None
            if low_seed:
                qf_matchups.append((high_seed, low_seed))
        
        for home, away in qf_matchups:
            match = ScheduledMatch(
                match_id=f"{self.current_phase.value}_{match_id_counter}",
                home_team_id=home,
                away_team_id=away,
                week=1,
                phase=self.current_phase,
                best_of=7  # Best of 7 for majors
            )
            schedule.append(match)
            match_id_counter += 1
        
        self.schedule.extend(schedule)
        return schedule
    
    def update_standings(self, result: SeriesResult):
        """Update standings based on a match result."""
        winner_id = result.winner_id
        loser_id = result.loser_id
        
        # Update winner
        if winner_id in self.standings:
            self.standings[winner_id].wins += 1
            self.standings[winner_id].game_wins += result.home_wins if winner_id == result.home_team_id else result.away_wins
            self.standings[winner_id].game_losses += result.away_wins if winner_id == result.home_team_id else result.home_wins
            self.standings[winner_id].points += 3
        
        # Update loser
        if loser_id in self.standings:
            self.standings[loser_id].losses += 1
            self.standings[loser_id].game_wins += result.home_wins if loser_id == result.home_team_id else result.away_wins
            self.standings[loser_id].game_losses += result.away_wins if loser_id == result.home_team_id else result.home_wins
            self.standings[loser_id].points += 0
    
    def reset_for_new_season(self):
        """Reset league state for a new season."""
        self.current_week = 1
        self.current_phase = SeasonPhase.OFFSEASON
        self.schedule = []
        self.standings = {tid: Standing(team_id=tid) for tid in self.team_ids}
        self.season_number += 1
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'region': self.region,
            'team_ids': self.team_ids,
            'current_week': self.current_week,
            'current_phase': self.current_phase.value,
            'schedule': [m.to_dict() for m in self.schedule],
            'standings': {k: vars(v) for k, v in self.standings.items()},
            'season_number': self.season_number,
            'champions_history': self.champions_history
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'League':
        league = cls(
            id=data['id'],
            name=data['name'],
            region=data['region'],
            team_ids=data['team_ids'],
            current_week=data.get('current_week', 1),
            season_number=data.get('season_number', 1),
            champions_history=data.get('champions_history', [])
        )
        league.current_phase = SeasonPhase(data.get('current_phase', 'offseason'))
        
        # Rebuild standings
        for tid, sdata in data.get('standings', {}).items():
            league.standings[tid] = Standing(**sdata)
        
        return league


class SeasonManager:
    """
    Manages season progression, simulation, and events.
    """
    
    def __init__(
        self,
        league: League,
        teams: Dict[str, Team],
        players: Dict[str, Player]
    ):
        self.league = league
        self.teams = teams
        self.players = players
        self.match_engine = MatchEngine()
        
        # Event log
        self.events: List[Dict] = []
    
    def start_new_season(self):
        """Initialize a new season."""
        self.league.reset_for_new_season()
        
        # Reset team season stats
        for team in self.teams.values():
            team.reset_season_stats()
        
        # Reset player season stats
        for player in self.players.values():
            player.reset_season_stats()
        
        self.add_event("season_start", f"Season {self.league.season_number} begins!")
        
        # Move to preseason
        self.advance_phase()
    
    def advance_phase(self) -> SeasonPhase:
        """Advance to the next season phase."""
        phase_order = [
            SeasonPhase.OFFSEASON,
            SeasonPhase.PRESEASON,
            # Split 1
            SeasonPhase.SPLIT1_REGIONAL_1,
            SeasonPhase.SPLIT1_REGIONAL_2,
            SeasonPhase.SPLIT1_REGIONAL_3,
            SeasonPhase.SPLIT1_MAJOR,
            # Between splits
            SeasonPhase.SPLIT_BREAK,
            # Split 2
            SeasonPhase.SPLIT2_REGIONAL_1,
            SeasonPhase.SPLIT2_REGIONAL_2,
            SeasonPhase.SPLIT2_REGIONAL_3,
            SeasonPhase.SPLIT2_MAJOR,
            # Worlds
            SeasonPhase.WORLDS,
            SeasonPhase.SEASON_END
        ]
        
        current_idx = phase_order.index(self.league.current_phase)
        next_idx = min(current_idx + 1, len(phase_order) - 1)
        self.league.current_phase = phase_order[next_idx]
        
        # Reset week counter for new phase
        self.league.current_week = 1
        
        # Generate schedule for regional phases
        if self.league.current_phase in REGIONAL_PHASES:
            self.league.generate_schedule(self.league.current_phase, weeks=3)
            phase_name = self._format_phase_name(self.league.current_phase)
            self.add_event("phase_start", f"{phase_name} begins!")
        
        # Major phases get a bracket schedule
        elif self.league.current_phase in MAJOR_PHASES:
            self.league.generate_major_bracket()
            phase_name = self._format_phase_name(self.league.current_phase)
            self.add_event("phase_start", f"{phase_name} begins!")
        
        # Split break - training camp time
        elif self.league.current_phase == SeasonPhase.SPLIT_BREAK:
            self.add_event("split_break", "Split Break begins! Teams enter training camp.")
        
        return self.league.current_phase
    
    def _format_phase_name(self, phase: SeasonPhase) -> str:
        """Format phase name for display."""
        name = phase.value
        # Convert split1_regional_1 -> Split 1 Regional 1
        if name.startswith('split1_'):
            return "Split 1 " + name[7:].replace('_', ' ').title()
        elif name.startswith('split2_'):
            return "Split 2 " + name[7:].replace('_', ' ').title()
        else:
            return name.replace('_', ' ').title()
    
    def simulate_week(self) -> List[SeriesResult]:
        """Simulate all matches for the current week."""
        matches = self.league.get_week_matches(
            self.league.current_week,
            self.league.current_phase
        )
        
        results = []
        for match in matches:
            if match.is_played:
                continue
            
            result = self.simulate_match(match)
            results.append(result)
        
        # Check if phase is complete
        unplayed = [m for m in self.league.schedule 
                   if m.phase == self.league.current_phase and not m.is_played]
        
        if not unplayed:
            # Phase complete
            phase_name = self.league.current_phase.value.replace('_', ' ').title()
            self.add_event("phase_end", f"{phase_name} complete!")
            
            # Award placements for regionals
            if self.league.current_phase in REGIONAL_PHASES:
                standings = self.league.get_sorted_standings()
                if standings:
                    winner = standings[0]
                    team = self.teams.get(winner.team_id)
                    if team:
                        team.season_stats.regional_placements.append(1)
                        self.add_event("placement", f"{team.name} wins {phase_name}!")
            
            # Award placements for majors
            elif self.league.current_phase in MAJOR_PHASES:
                standings = self.league.get_sorted_standings()
                if standings:
                    winner = standings[0]
                    team = self.teams.get(winner.team_id)
                    if team:
                        team.season_stats.major_placement = 1
                        self.add_event("major_winner", f"{team.name} wins the {phase_name}!")
        else:
            self.league.current_week += 1
        
        return results
    
    def simulate_match(self, match: ScheduledMatch) -> SeriesResult:
        """Simulate a single scheduled match."""
        home_team = self.teams.get(match.home_team_id)
        away_team = self.teams.get(match.away_team_id)
        
        if not home_team or not away_team:
            raise ValueError(f"Team not found for match {match.match_id}")
        
        # Get active roster players
        home_players = [self.players[pid] for pid in home_team.active_roster 
                       if pid in self.players]
        away_players = [self.players[pid] for pid in away_team.active_roster 
                       if pid in self.players]
        
        # Simulate
        result = self.match_engine.simulate_series(
            home_team, away_team,
            home_players, away_players,
            match.best_of
        )
        
        # Record result
        match.result = result
        
        # Update standings
        self.league.update_standings(result)
        
        # Update team stats
        self._update_team_stats(home_team, result, is_home=True)
        self._update_team_stats(away_team, result, is_home=False)
        
        # Update player stats
        self._update_player_stats(result)
        
        # Update Elo
        home_team.update_elo(away_team.elo, result.winner_id == home_team.id)
        away_team.update_elo(home_team.elo, result.winner_id == away_team.id)
        
        # Update chemistry (teams that play together build chemistry)
        home_team.update_chemistry(len(result.games))
        away_team.update_chemistry(len(result.games))
        
        # Log event
        winner = self.teams.get(result.winner_id)
        loser = self.teams.get(result.loser_id)
        self.add_event(
            "match_result",
            f"{winner.name} defeats {loser.name} {result.score}",
            data={'match_id': match.match_id, 'result': result.to_dict()}
        )
        
        return result
    
    def _update_team_stats(self, team: Team, result: SeriesResult, is_home: bool):
        """Update team statistics after a match."""
        won = result.winner_id == team.id
        
        if is_home:
            team_wins = result.home_wins
            team_losses = result.away_wins
            goals_for = result.total_goals(team.id)
            goals_against = result.total_goals(result.away_team_id)
        else:
            team_wins = result.away_wins
            team_losses = result.home_wins
            goals_for = result.total_goals(team.id)
            goals_against = result.total_goals(result.home_team_id)
        
        team.season_stats.wins += team_wins
        team.season_stats.losses += team_losses
        team.season_stats.goals_for += goals_for
        team.season_stats.goals_against += goals_against
        
        if won:
            team.season_stats.series_wins += 1
        else:
            team.season_stats.series_losses += 1
    
    def _update_player_stats(self, result: SeriesResult):
        """Update individual player statistics after a match."""
        for game in result.games:
            # Home team players
            for pstat in game.home_stats:
                if pstat.player_id in self.players:
                    player = self.players[pstat.player_id]
                    player.season_stats.games_played += 1
                    player.season_stats.goals += pstat.goals
                    player.season_stats.assists += pstat.assists
                    player.season_stats.saves += pstat.saves
                    player.season_stats.shots += pstat.shots
                    
                    player.career_stats.games_played += 1
                    player.career_stats.goals += pstat.goals
                    player.career_stats.assists += pstat.assists
                    player.career_stats.saves += pstat.saves
                    player.career_stats.shots += pstat.shots
            
            # Away team players
            for pstat in game.away_stats:
                if pstat.player_id in self.players:
                    player = self.players[pstat.player_id]
                    player.season_stats.games_played += 1
                    player.season_stats.goals += pstat.goals
                    player.season_stats.assists += pstat.assists
                    player.season_stats.saves += pstat.saves
                    player.season_stats.shots += pstat.shots
                    
                    player.career_stats.games_played += 1
                    player.career_stats.goals += pstat.goals
                    player.career_stats.assists += pstat.assists
                    player.career_stats.saves += pstat.saves
                    player.career_stats.shots += pstat.shots
    
    def process_end_of_season(self):
        """Handle end of season tasks."""
        # Age all players
        for player in self.players.values():
            regressions = player.age_one_year()
            if regressions:
                self.add_event(
                    "player_regression",
                    f"{player.name} shows signs of aging",
                    data={'player_id': player.id, 'regressions': regressions}
                )
        
        # Develop young players
        for player in self.players.values():
            if player.age < 24:
                team = self.teams.get(player.team_id)
                training_quality = 60 if team else 40
                improvements = player.develop(training_quality)
                if improvements:
                    self.add_event(
                        "player_development",
                        f"{player.name} improved!",
                        data={'player_id': player.id, 'improvements': improvements}
                    )
        
        # Record champion
        standings = self.league.get_sorted_standings()
        if standings:
            champion_id = standings[0].team_id
            self.league.champions_history.append(champion_id)
            champion = self.teams.get(champion_id)
            if champion:
                self.add_event(
                    "champion",
                    f"{champion.name} wins Season {self.league.season_number}!"
                )
    
    def add_event(self, event_type: str, message: str, data: dict = None):
        """Add an event to the log."""
        self.events.append({
            'type': event_type,
            'message': message,
            'phase': self.league.current_phase.value,
            'week': self.league.current_week,
            'season': self.league.season_number,
            'data': data or {}
        })
    
    def get_recent_events(self, count: int = 10) -> List[Dict]:
        """Get the most recent events."""
        return self.events[-count:]
