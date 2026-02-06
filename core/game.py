"""
Main Game class for Rocket League GM Simulator.
Orchestrates all game systems and handles save/load.
"""

import json
import os
import random
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

from .models.player import Player
from .models.team import Team, Contract
from .simulation.season import League, SeasonManager, SeasonPhase
from .data.generator import create_initial_game_state, generate_player, generate_free_agent_pool
from .ai.team_ai import LeagueAI


SAVE_VERSION = "1.0.0"


@dataclass
class GameSettings:
    """Game configuration settings."""
    difficulty: str = "normal"  # easy, normal, hard
    auto_save: bool = True
    simulation_speed: str = "normal"  # instant, fast, normal, detailed
    
    def to_dict(self) -> dict:
        return {
            'difficulty': self.difficulty,
            'auto_save': self.auto_save,
            'simulation_speed': self.simulation_speed
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GameSettings':
        return cls(**data)


class Game:
    """
    Main game orchestrator.
    Manages all game state and provides interface for game actions.
    """
    
    def __init__(self):
        self.league: Optional[League] = None
        self.teams: Dict[str, Team] = {}
        self.players: Dict[str, Player] = {}
        self.free_agent_ids: List[str] = []
        
        self.player_team_id: Optional[str] = None  # ID of user's team
        self.season_manager: Optional[SeasonManager] = None
        self.league_ai: Optional[LeagueAI] = None  # AI manager for all teams
        
        self.settings = GameSettings()
        
        # Metadata
        self.save_name: str = ""
        self.created_at: str = ""
        self.last_played: str = ""
    
    # =========================================================================
    # Game Initialization
    # =========================================================================
    
    def new_game(self, team_name: str, team_abbrev: str, region: str = "NA"):
        """
        Start a new game with the player managing a new team.
        """
        # Generate initial state
        state = create_initial_game_state()
        
        self.league = state['league']
        self.teams = state['teams']
        self.players = state['players']
        self.free_agent_ids = state['free_agent_ids']
        
        # Create player's team (or let them pick one)
        # For now, create a new team
        from .data.generator import generate_team
        player_team, roster = generate_team(region, tier="average")
        player_team.name = team_name
        player_team.abbreviation = team_abbrev
        player_team.is_player_team = True
        
        self.teams[player_team.id] = player_team
        self.league.add_team(player_team.id)
        
        for p in roster:
            self.players[p.id] = p
        
        self.player_team_id = player_team.id
        
        # Initialize season manager
        self.season_manager = SeasonManager(self.league, self.teams, self.players)
        
        # Initialize AI for non-player teams
        self.league_ai = LeagueAI(self.teams, self.players, self.player_team_id)
        
        # Set metadata
        self.created_at = datetime.now().isoformat()
        self.last_played = self.created_at
        self.save_name = f"{team_name}_{datetime.now().strftime('%Y%m%d')}"
        
        # Start first season
        self.season_manager.start_new_season()
    
    def select_existing_team(self, team_id: str):
        """Let player take control of an existing team."""
        if team_id in self.teams:
            # Remove player control from previous team
            if self.player_team_id and self.player_team_id in self.teams:
                self.teams[self.player_team_id].is_player_team = False
            
            self.player_team_id = team_id
            self.teams[team_id].is_player_team = True
    
    # =========================================================================
    # Game Properties
    # =========================================================================
    
    @property
    def player_team(self) -> Optional[Team]:
        """Get the player's team."""
        return self.teams.get(self.player_team_id) if self.player_team_id else None
    
    @property
    def current_phase(self) -> SeasonPhase:
        """Get current season phase."""
        return self.league.current_phase if self.league else SeasonPhase.OFFSEASON
    
    @property
    def current_week(self) -> int:
        """Get current week number."""
        return self.league.current_week if self.league else 0
    
    @property
    def season_number(self) -> int:
        """Get current season number."""
        return self.league.season_number if self.league else 0
    
    # =========================================================================
    # Roster Management
    # =========================================================================
    
    def get_team_roster(self, team_id: str) -> List[Player]:
        """Get all players on a team's roster."""
        team = self.teams.get(team_id)
        if not team:
            return []
        return [self.players[pid] for pid in team.roster if pid in self.players]
    
    def get_free_agents(self) -> List[Player]:
        """Get all available free agents."""
        return [self.players[pid] for pid in self.free_agent_ids if pid in self.players]
    
    def sign_free_agent(self, player_id: str, salary: int, length: int) -> bool:
        """
        Sign a free agent to the player's team.
        Returns True if successful.
        """
        if not self.player_team:
            return False
        
        if player_id not in self.free_agent_ids:
            return False
        
        player = self.players.get(player_id)
        if not player:
            return False
        
        team = self.player_team
        
        # Check roster space
        if team.roster_size >= 5:
            return False
        
        # Check budget
        if salary > team.salary_cap_space:
            return False
        
        # Create contract
        contract = Contract(
            player_id=player_id,
            team_id=team.id,
            salary=salary,
            length=length,
            buyout=salary * 3
        )
        
        # Add to team
        team.add_player(player_id, contract)
        player.team_id = team.id
        
        # Remove from free agents
        self.free_agent_ids.remove(player_id)
        
        # Log event
        if self.season_manager:
            self.season_manager.add_event(
                "signing",
                f"{team.name} signs {player.name} (${salary}/mo, {length} months)"
            )
        
        return True
    
    def release_player(self, player_id: str) -> bool:
        """
        Release a player from the player's team.
        Returns True if successful.
        """
        if not self.player_team:
            return False
        
        team = self.player_team
        
        if player_id not in team.roster:
            return False
        
        player = self.players.get(player_id)
        if not player:
            return False
        
        # Remove from team
        team.remove_player(player_id)
        player.team_id = None
        
        # Add to free agents
        self.free_agent_ids.append(player_id)
        
        # Log event
        if self.season_manager:
            self.season_manager.add_event(
                "release",
                f"{team.name} releases {player.name}"
            )
        
        return True
    
    def swap_roster_order(self, idx1: int, idx2: int) -> bool:
        """Swap positions in the player team's roster."""
        if not self.player_team:
            return False
        
        self.player_team.swap_roster_position(idx1, idx2)
        return True
    
    # =========================================================================
    # Season Progression
    # =========================================================================
    
    def advance_week(self) -> List[dict]:
        """
        Advance the game by one week.
        Simulates matches and returns results.
        """
        if not self.season_manager:
            return []
        
        results = self.season_manager.simulate_week()
        
        # Process AI roster moves (chance each week)
        if self.league_ai and random.random() < 0.3:  # 30% chance per week
            self.process_ai_moves()
        
        # Check for phase transitions
        unplayed = [m for m in self.league.schedule 
                   if m.phase == self.current_phase and not m.is_played]
        
        if not unplayed:
            self.advance_phase()
        
        self.last_played = datetime.now().isoformat()
        
        return [r.to_dict() for r in results]
    
    def process_ai_moves(self) -> List[dict]:
        """
        Process AI team roster decisions.
        Returns list of actions taken by AI teams.
        """
        if not self.league_ai:
            return []
        
        actions, self.free_agent_ids = self.league_ai.process_ai_decisions(
            self.free_agent_ids
        )
        
        # Log AI actions as events
        for action in actions:
            if action["type"] == "sign":
                self.season_manager.add_event(
                    "ai_signing",
                    f"{action['team_name']} signs {action['player_name']} (${action['salary']:,}/mo)",
                    data=action
                )
            elif action["type"] == "release":
                self.season_manager.add_event(
                    "ai_release",
                    f"{action['team_name']} releases {action['player_name']} ({action['reason']})",
                    data=action
                )
        
        return actions
    
    def advance_phase(self) -> SeasonPhase:
        """Advance to the next season phase."""
        if not self.season_manager:
            return SeasonPhase.OFFSEASON
        
        new_phase = self.season_manager.advance_phase()
        
        # AI teams make moves between phases
        if self.league_ai and new_phase in [SeasonPhase.REGIONAL_2, SeasonPhase.REGIONAL_3, 
                                             SeasonPhase.MAJOR, SeasonPhase.OFFSEASON]:
            self.process_ai_moves()
        
        if new_phase == SeasonPhase.SEASON_END:
            self.season_manager.process_end_of_season()
        
        return new_phase
    
    def start_new_season(self):
        """Start a new season."""
        if not self.season_manager:
            return
        
        # Generate new free agents
        new_fas = generate_free_agent_pool(self.league.region, count=10)
        for fa in new_fas:
            self.players[fa.id] = fa
            self.free_agent_ids.append(fa.id)
        
        # AI teams make offseason moves (multiple rounds)
        if self.league_ai:
            for _ in range(3):  # 3 rounds of AI moves
                self.process_ai_moves()
        
        self.season_manager.start_new_season()
    
    # =========================================================================
    # Information Queries
    # =========================================================================
    
    def get_standings(self) -> List[dict]:
        """Get current league standings."""
        if not self.league:
            return []
        
        standings = self.league.get_sorted_standings()
        result = []
        
        for i, standing in enumerate(standings):
            team = self.teams.get(standing.team_id)
            result.append({
                'rank': i + 1,
                'team_id': standing.team_id,
                'team_name': team.name if team else "Unknown",
                'team_abbrev': team.abbreviation if team else "???",
                'wins': standing.wins,
                'losses': standing.losses,
                'game_wins': standing.game_wins,
                'game_losses': standing.game_losses,
                'points': standing.points,
                'is_player_team': standing.team_id == self.player_team_id
            })
        
        return result
    
    def get_schedule(self, week: int = None) -> List[dict]:
        """Get match schedule."""
        if not self.league:
            return []
        
        if week is None:
            matches = self.league.schedule
        else:
            matches = self.league.get_week_matches(week, self.current_phase)
        
        result = []
        for match in matches:
            home = self.teams.get(match.home_team_id)
            away = self.teams.get(match.away_team_id)
            
            result.append({
                'match_id': match.match_id,
                'week': match.week,
                'phase': match.phase.value,
                'home_team': home.abbreviation if home else "???",
                'away_team': away.abbreviation if away else "???",
                'home_team_id': match.home_team_id,
                'away_team_id': match.away_team_id,
                'is_played': match.is_played,
                'result': match.result.score if match.result else None,
                'involves_player': (match.home_team_id == self.player_team_id or 
                                   match.away_team_id == self.player_team_id)
            })
        
        return result
    
    def get_recent_events(self, count: int = 10) -> List[dict]:
        """Get recent game events."""
        if not self.season_manager:
            return []
        return self.season_manager.get_recent_events(count)
    
    def get_stat_leaders(self, stat: str = "goals", count: int = 10) -> List[dict]:
        """Get league stat leaders for the current season."""
        players_with_teams = [
            (p, self.teams.get(p.team_id))
            for p in self.players.values()
            if p.team_id and p.season_stats.games_played > 0
        ]
        
        stat_attr = {
            "goals": lambda p: p.season_stats.goals,
            "assists": lambda p: p.season_stats.assists,
            "saves": lambda p: p.season_stats.saves,
            "games": lambda p: p.season_stats.games_played,
            "goals_per_game": lambda p: p.season_stats.goals_per_game,
            "assists_per_game": lambda p: p.season_stats.assists_per_game,
            "saves_per_game": lambda p: p.season_stats.saves_per_game,
        }
        
        getter = stat_attr.get(stat, stat_attr["goals"])
        
        sorted_players = sorted(players_with_teams, key=lambda x: getter(x[0]), reverse=True)
        
        result = []
        for i, (player, team) in enumerate(sorted_players[:count]):
            result.append({
                'rank': i + 1,
                'player_id': player.id,
                'player_name': player.name,
                'team_abbrev': team.abbreviation if team else "FA",
                'value': round(getter(player), 2),
                'games_played': player.season_stats.games_played
            })
        
        return result
    
    # =========================================================================
    # Save/Load
    # =========================================================================
    
    def save_game(self, filepath: str = None) -> str:
        """
        Save game to JSON file.
        Returns the filepath used.
        """
        if filepath is None:
            os.makedirs("saves", exist_ok=True)
            filepath = f"saves/{self.save_name}.json"
        
        self.last_played = datetime.now().isoformat()
        
        save_data = {
            'version': SAVE_VERSION,
            'metadata': {
                'save_name': self.save_name,
                'created_at': self.created_at,
                'last_played': self.last_played
            },
            'settings': self.settings.to_dict(),
            'player_team_id': self.player_team_id,
            'league': self.league.to_dict() if self.league else None,
            'teams': {k: v.to_dict() for k, v in self.teams.items()},
            'players': {k: v.to_dict() for k, v in self.players.items()},
            'free_agent_ids': self.free_agent_ids
        }
        
        with open(filepath, 'w') as f:
            json.dump(save_data, f, indent=2)
        
        return filepath
    
    @classmethod
    def load_game(cls, filepath: str) -> 'Game':
        """Load game from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        game = cls()
        
        # Check version for migrations
        version = data.get('version', '1.0.0')
        # Future: add migration logic here
        
        # Load metadata
        metadata = data.get('metadata', {})
        game.save_name = metadata.get('save_name', 'Unknown')
        game.created_at = metadata.get('created_at', '')
        game.last_played = metadata.get('last_played', '')
        
        # Load settings
        if 'settings' in data:
            game.settings = GameSettings.from_dict(data['settings'])
        
        # Load players first (teams reference them)
        for pid, pdata in data.get('players', {}).items():
            game.players[pid] = Player.from_dict(pdata)
        
        # Load teams
        for tid, tdata in data.get('teams', {}).items():
            game.teams[tid] = Team.from_dict(tdata)
        
        # Load league
        if data.get('league'):
            game.league = League.from_dict(data['league'])
        
        # Load other state
        game.player_team_id = data.get('player_team_id')
        game.free_agent_ids = data.get('free_agent_ids', [])
        
        # Initialize season manager
        if game.league:
            game.season_manager = SeasonManager(game.league, game.teams, game.players)
        
        # Initialize AI for non-player teams
        game.league_ai = LeagueAI(game.teams, game.players, game.player_team_id)
        
        return game
    
    @staticmethod
    def list_saves(directory: str = "saves") -> List[dict]:
        """List available save files."""
        saves = []
        
        if not os.path.exists(directory):
            return saves
        
        for filename in os.listdir(directory):
            if filename.endswith('.json'):
                filepath = os.path.join(directory, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    metadata = data.get('metadata', {})
                    saves.append({
                        'filepath': filepath,
                        'filename': filename,
                        'save_name': metadata.get('save_name', filename),
                        'last_played': metadata.get('last_played', ''),
                        'season': data.get('league', {}).get('season_number', 1)
                    })
                except:
                    pass
        
        return sorted(saves, key=lambda x: x.get('last_played', ''), reverse=True)