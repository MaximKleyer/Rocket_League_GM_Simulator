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
from .models.team import Team, Contract, TrainingAllocation
from .simulation.season import League, SeasonManager, SeasonPhase, REGIONAL_PHASES, MAJOR_PHASES
from .simulation.training import (
    TrainingManager, MoraleManager, ChemistryManager, ProgressionManager,
    TRAINING_ATTRIBUTE_MAP
)
from .simulation.contracts import (
    ContractNegotiator, ContractManager, NegotiationState, 
    Willingness, ExpiringContract
)
from .simulation.tournament import (
    SwissBracket, DoubleEliminationBracket, RegionalTournament, REGIONAL_POINTS
)
from .data.generator import (
    create_initial_game_state, generate_player, generate_free_agent_pool,
    generate_rookie_class, retire_old_free_agents
)
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
        self.training_manager: TrainingManager = TrainingManager()  # Training system
        
        # Tournament system
        self.current_regional: Optional[RegionalTournament] = None
        self.season_points: Dict[str, int] = {}  # Accumulated points per team
        
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
        32 teams total (31 AI + player team).
        """
        # Generate initial state (31 AI teams)
        state = create_initial_game_state()
        
        self.league = state['league']
        self.teams = state['teams']
        self.players = state['players']
        self.free_agent_ids = state['free_agent_ids']
        
        # Create player's team (32nd team)
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
        
        # Initialize season points for all teams
        self.season_points = {tid: 0 for tid in self.teams}
        
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
    
    def sign_free_agent(self, player_id: str, salary: int, years: int) -> bool:
        """
        Sign a free agent to the player's team.
        Salary is yearly, years is contract length (1-5).
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
        
        # Check budget (yearly)
        if salary > team.salary_cap_space:
            return False
        
        # Create contract
        contract = ContractManager.create_contract(
            player_id=player_id,
            team_id=team.id,
            salary=salary,
            years=years
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
                f"{team.name} signs {player.name} (${salary:,}/yr, {years} year{'s' if years > 1 else ''})"
            )
        
        return True
    
    # =========================================================================
    # Contract Negotiation System
    # =========================================================================
    
    def start_negotiation(
        self,
        player_id: str,
        is_re_sign: bool = False
    ) -> Optional[NegotiationState]:
        """
        Start contract negotiation with a player.
        
        Args:
            player_id: The player to negotiate with
            is_re_sign: True if re-signing existing player
        
        Returns:
            NegotiationState or None if player not found
        """
        player = self.players.get(player_id)
        if not player:
            return None
        
        team = self.player_team
        if not team:
            return None
        
        # Get previous salary if re-signing
        previous_salary = 0
        if is_re_sign and player_id in team.contracts:
            previous_salary = team.contracts[player_id].salary
        
        # Get team stats for market value calculation
        team_stats = {
            'wins': team.season_stats.series_wins,
            'losses': team.season_stats.series_losses
        }
        
        # Get league standings for willingness calculation
        standings = self.get_standings()
        
        return ContractNegotiator.start_negotiation(
            player=player,
            team=team,
            is_re_sign=is_re_sign,
            league_standings=standings,
            team_stats=team_stats,
            previous_salary=previous_salary
        )
    
    def make_contract_offer(
        self,
        state: NegotiationState,
        salary: int,
        years: int
    ) -> tuple:
        """
        Make a contract offer during negotiation.
        
        Returns:
            (accepted: bool, message: str)
        """
        player = self.players.get(state.player_id)
        player_name = player.name if player else "The player"
        
        accepted, message = ContractNegotiator.make_offer(state, salary, years)
        
        # Replace placeholder with actual name
        message = message.replace("The player", player_name)
        
        if accepted:
            # Sign the player
            if state.is_re_sign:
                # Update existing contract
                self.player_team.contracts[state.player_id] = ContractManager.create_contract(
                    player_id=state.player_id,
                    team_id=self.player_team.id,
                    salary=salary,
                    years=years
                )
                if self.season_manager:
                    self.season_manager.add_event(
                        "re_signing",
                        f"{self.player_team.name} re-signs {player_name} (${salary:,}/yr, {years} year{'s' if years > 1 else ''})"
                    )
            else:
                # Sign as free agent
                self.sign_free_agent(state.player_id, salary, years)
        
        return accepted, message
    
    def end_contract_talks(self, state: NegotiationState) -> str:
        """
        End negotiations without a deal.
        If re-signing, player becomes a free agent.
        """
        player = self.players.get(state.player_id)
        player_name = player.name if player else "The player"
        
        message = ContractNegotiator.end_negotiations(state)
        message = message.replace("The player", player_name)
        
        # If re-signing failed, release the player
        if state.is_re_sign:
            self.release_player(state.player_id)
        
        return message
    
    def get_expiring_contracts(self) -> List[ExpiringContract]:
        """Get list of expiring contracts on player's team."""
        if not self.player_team:
            return []
        
        return ContractManager.get_expiring_contracts(
            self.player_team, self.players
        )
    
    def get_market_value(self, player_id: str) -> int:
        """Get a player's market value (yearly salary)."""
        player = self.players.get(player_id)
        if not player:
            return 0
        
        team_stats = None
        if self.player_team:
            team_stats = {
                'wins': self.player_team.season_stats.series_wins,
                'losses': self.player_team.season_stats.series_losses
            }
        
        return ContractNegotiator.calculate_market_value(player, team_stats)
    
    def process_season_contracts(self):
        """
        Process contracts at end of season.
        Decrements years remaining on all contracts.
        Called at season end.
        """
        expired_by_team = {}
        
        for team_id, team in self.teams.items():
            expired = ContractManager.process_contract_year(team)
            if expired:
                expired_by_team[team_id] = expired
        
        return expired_by_team
    
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
    # Training Management
    # =========================================================================
    
    def get_training_allocation(self) -> dict:
        """Get current training allocation for player's team."""
        if not self.player_team:
            return {'mechanical': 34, 'game_sense': 33, 'mental': 33}
        return self.player_team.training.to_dict()
    
    def set_training_allocation(self, mechanical: int, game_sense: int, mental: int) -> bool:
        """
        Set training allocation for player's team.
        Returns True if valid (sums to 100).
        """
        if not self.player_team:
            return False
        return self.player_team.training.set_allocation(mechanical, game_sense, mental)
    
    def reset_training_allocation(self):
        """Reset training to default balanced allocation."""
        if self.player_team:
            self.player_team.training.reset_to_default()
    
    def can_train(self) -> bool:
        """Check if player's team can train this week."""
        if not self.player_team:
            return False
        return self.training_manager.can_train(self.player_team_id)
    
    def do_training(self) -> Dict[str, List[dict]]:
        """
        Player-initiated weekly training for their team.
        Can only be done once per week.
        Returns dict of {player_id: [improvements]}.
        """
        if not self.player_team:
            return {}
        
        if not self.can_train():
            return {}
        
        roster = self.get_team_roster(self.player_team_id)
        results = self.training_manager.process_weekly_training(
            roster,
            self.player_team.training,
            self.player_team.chemistry,
            mark_trained=True,
            team_id=self.player_team_id
        )
        
        # Log improvements
        for player_id, improvements in results.items():
            player = self.players.get(player_id)
            if player and improvements:
                attrs = [imp['attribute'] for imp in improvements]
                self.season_manager.add_event(
                    "training",
                    f"{player.name} improved: {', '.join(attrs)}",
                    data={'player_id': player_id, 'improvements': improvements}
                )
        
        return results
    
    def process_ai_training(self):
        """Process training for all AI teams."""
        for team_id, team in self.teams.items():
            if team_id == self.player_team_id:
                continue  # Skip player team
            
            if not self.training_manager.can_train(team_id):
                continue
            
            roster = self.get_team_roster(team_id)
            self.training_manager.process_weekly_training(
                roster,
                team.training,
                team.chemistry,
                mark_trained=True,
                team_id=team_id
            )
    
    def get_team_average_morale(self, team_id: str) -> float:
        """Get average morale of a team's active roster."""
        roster = self.get_team_roster(team_id)
        if not roster:
            return 50.0
        active = roster[:3]  # Active players only
        return sum(p.morale for p in active) / len(active)
    
    def update_morale_after_match(self, team_id: str, won: bool, player_stats: dict = None):
        """Update morale for all players on a team after a match."""
        team = self.teams.get(team_id)
        if not team:
            return
        
        roster = self.get_team_roster(team_id)
        for i, player in enumerate(roster):
            is_starter = i < 3
            goals = 0
            was_mvp = False
            
            if player_stats and player.id in player_stats:
                goals = player_stats[player.id].get('goals', 0)
                was_mvp = player_stats[player.id].get('mvp', False)
            
            MoraleManager.update_morale_after_match(
                player, won, is_starter, team.chemistry, goals, was_mvp
            )
    
    def update_chemistry_after_match(self, team_id: str, won: bool) -> int:
        """Update chemistry for a team after a match. Returns the change."""
        team = self.teams.get(team_id)
        if not team:
            return 0
        
        # Update streak
        if won:
            if team.streak >= 0:
                team.streak += 1
            else:
                team.streak = 1
        else:
            if team.streak <= 0:
                team.streak -= 1
            else:
                team.streak = -1
        
        # Get average morale
        avg_morale = self.get_team_average_morale(team_id)
        
        # Update chemistry
        new_chem, change = ChemistryManager.update_chemistry_after_match(
            team.chemistry, won, avg_morale, team.streak
        )
        team.chemistry = new_chem
        
        return change
    
    def process_split_break(self) -> Dict[str, dict]:
        """
        Process split break for all teams.
        Includes natural regression, progression, intensive training camp, and chemistry boost.
        Returns dict with results per team.
        """
        results = {
            'natural_regression': {},
            'progression': {},
            'training': {},
            'chemistry': {}
        }
        
        for team_id, team in self.teams.items():
            roster = self.get_team_roster(team_id)
            
            # Get team record for performance factor
            team_wins = team.season_stats.series_wins
            team_losses = team.season_stats.series_losses
            
            # ===== NATURAL REGRESSION =====
            # All players lose a bit due to meta shifts and rust
            team_regression = {}
            for player in roster:
                reg_changes = ProgressionManager.apply_natural_regression(player)
                if reg_changes:
                    team_regression[player.id] = {
                        'name': player.name,
                        'changes': reg_changes,
                        'new_overall': player.overall
                    }
            
            if team_regression:
                results['natural_regression'][team_id] = team_regression
            
            # ===== PROGRESSION =====
            # Players upgrade or regress based on morale, age, performance, RNG
            team_progression = {}
            for player in roster:
                changes = ProgressionManager.process_split_progression(
                    player, team_wins, team_losses
                )
                if changes:
                    team_progression[player.id] = {
                        'name': player.name,
                        'changes': changes,
                        'new_overall': player.overall
                    }
            
            if team_progression:
                results['progression'][team_id] = team_progression
            
            # ===== CHEMISTRY BOOST =====
            # Get previous roster (stored at end of Split 1)
            previous_roster = getattr(team, '_split1_roster', [])
            
            new_chem, chem_desc = self.training_manager.calculate_chemistry_boost(
                team.roster[:3],
                previous_roster[:3] if previous_roster else [],
                team.chemistry
            )
            
            old_chemistry = team.chemistry
            team.chemistry = new_chem
            
            results['chemistry'][team_id] = {
                'team_name': team.name,
                'old_chemistry': old_chemistry,
                'new_chemistry': new_chem,
                'boost': new_chem - old_chemistry,
                'description': chem_desc
            }
            
            # ===== INTENSIVE TRAINING =====
            training_results = self.training_manager.process_split_break_training(
                roster,
                team.training,
                team.chemistry,
                sessions=4
            )
            
            if training_results:
                results['training'][team_id] = training_results
        
        # Log player team's results
        if self.player_team_id:
            # Natural regression
            reg_info = results['natural_regression'].get(self.player_team_id, {})
            if reg_info:
                total_reg = sum(sum(p['changes'].values()) for p in reg_info.values())
                if total_reg < 0:
                    self.season_manager.add_event(
                        "natural_regression",
                        f"⏳ Meta shifts and rust: {abs(total_reg)} total stat decay across roster",
                        data=reg_info
                    )
            
            # Progression
            prog_info = results['progression'].get(self.player_team_id, {})
            for player_id, info in prog_info.items():
                total_change = sum(info['changes'].values())
                if total_change > 0:
                    self.season_manager.add_event(
                        "progression_up",
                        f"📈 {info['name']} developed! Overall now {info['new_overall']} (+{total_change})",
                        data=info
                    )
                elif total_change < 0:
                    self.season_manager.add_event(
                        "progression_down",
                        f"📉 {info['name']} regressed. Overall now {info['new_overall']} ({total_change})",
                        data=info
                    )
            
            # Chemistry
            chem_info = results['chemistry'].get(self.player_team_id, {})
            if chem_info:
                boost = chem_info['boost']
                boost_str = f"+{boost}" if boost >= 0 else str(boost)
                self.season_manager.add_event(
                    "split_break_chemistry",
                    f"Chemistry {chem_info['old_chemistry']} → {chem_info['new_chemistry']} ({boost_str}). {chem_info['description']}",
                    data=chem_info
                )
            
            # Training
            training_info = results['training'].get(self.player_team_id, {})
            if training_info:
                total_improvements = sum(len(imps) for imps in training_info.values())
                self.season_manager.add_event(
                    "split_break_training",
                    f"Training camp complete! {total_improvements} attribute improvements.",
                    data={'improvements': training_info}
                )
        
        return results
    
    def process_season_end_progression(self) -> Dict[str, dict]:
        """
        Process progression for all players at season end.
        Bigger changes than split breaks, includes natural regression.
        """
        results = {
            'natural_regression': {},
            'progression': {}
        }
        
        for team_id, team in self.teams.items():
            roster = self.get_team_roster(team_id)
            
            # Get team record for performance factor
            team_wins = team.season_stats.series_wins
            team_losses = team.season_stats.series_losses
            
            # ===== NATURAL REGRESSION =====
            team_regression = {}
            for player in roster:
                reg_changes = ProgressionManager.apply_natural_regression(player)
                if reg_changes:
                    team_regression[player.id] = {
                        'name': player.name,
                        'changes': reg_changes,
                        'new_overall': player.overall
                    }
            
            if team_regression:
                results['natural_regression'][team_id] = team_regression
            
            # ===== PROGRESSION =====
            team_progression = {}
            for player in roster:
                changes = ProgressionManager.process_season_end_progression(
                    player, team_wins, team_losses
                )
                if changes:
                    team_progression[player.id] = {
                        'name': player.name,
                        'changes': changes,
                        'new_overall': player.overall
                    }
            
            if team_progression:
                results['progression'][team_id] = team_progression
        
        # Also process free agents (no team record bonus)
        for player_id in self.free_agent_ids:
            player = self.players.get(player_id)
            if player:
                ProgressionManager.apply_natural_regression(player)
                ProgressionManager.process_season_end_progression(player, 0, 0)
        
        # Log player team's results
        if self.player_team_id:
            # Natural regression
            reg_info = results['natural_regression'].get(self.player_team_id, {})
            if reg_info:
                total_reg = sum(sum(p['changes'].values()) for p in reg_info.values())
                if total_reg < 0:
                    self.season_manager.add_event(
                        "season_regression",
                        f"⏳ Offseason rust: {abs(total_reg)} total stat decay across roster",
                        data=reg_info
                    )
            
            # Progression
            prog_info = results['progression'].get(self.player_team_id, {})
            for player_id, info in prog_info.items():
                total_change = sum(info['changes'].values())
                if total_change > 0:
                    self.season_manager.add_event(
                        "season_progression_up",
                        f"📈 {info['name']} had a growth spurt! Overall now {info['new_overall']} (+{total_change})",
                        data=info
                    )
                elif total_change < 0:
                    self.season_manager.add_event(
                        "season_progression_down",
                        f"📉 {info['name']} declined. Overall now {info['new_overall']} ({total_change})",
                        data=info
                    )
        
        return results
    
    def store_split1_rosters(self):
        """Store current rosters at end of Split 1 for chemistry calculation."""
        for team_id, team in self.teams.items():
            team._split1_roster = list(team.roster)
    
    # =========================================================================
    # Season Progression
    # =========================================================================
    
    def advance_week(self) -> List[dict]:
        """
        Advance the game by one round/week.
        Simulates tournament matches and processes morale/chemistry.
        AI teams train automatically. Player training is manual.
        Returns match results.
        """
        if not self.season_manager:
            return []
        
        # Reset training flags for new week
        self.training_manager.reset_weekly_training()
        
        # AI teams train automatically during regional phases
        if self.current_phase in REGIONAL_PHASES:
            self.process_ai_training()
        
        results = []
        
        # Handle regional tournament phases
        if self.current_phase in REGIONAL_PHASES and self.current_regional:
            results = self._simulate_tournament_round()
            
            # Check if regional is complete
            if self.current_regional.is_complete():
                self._finalize_regional()
                self.advance_phase()
        else:
            # Non-tournament phases (major, worlds - simplified for now)
            old_results = self.season_manager.simulate_week()
            results = [r.to_dict() for r in old_results]
            
            # Process morale and chemistry after matches
            for r in old_results:
                home_won = r.winner_id == r.home_team_id
                self.update_morale_after_match(r.home_team_id, home_won)
                self.update_chemistry_after_match(r.home_team_id, home_won)
                self.update_morale_after_match(r.away_team_id, not home_won)
                self.update_chemistry_after_match(r.away_team_id, not home_won)
            
            # Check for phase transitions
            unplayed = [m for m in self.league.schedule 
                       if m.phase == self.current_phase and not m.is_played]
            if not unplayed:
                self.advance_phase()
        
        # Process AI roster moves (chance each week)
        if self.league_ai and random.random() < 0.3:
            self.process_ai_moves()
        
        self.last_played = datetime.now().isoformat()
        
        return results
    
    def _simulate_tournament_round(self) -> List[dict]:
        """Simulate one round of the current tournament stage."""
        if not self.current_regional:
            return []
        
        results = []
        regional = self.current_regional
        
        # Determine which stage we're in and get matches
        if regional.current_stage == 'swiss_groups':
            # Run a round for both groups
            results.extend(self._run_swiss_round(regional.swiss_group_a, "Group A"))
            results.extend(self._run_swiss_round(regional.swiss_group_b, "Group B"))
            
            # Check if groups are complete
            if regional.swiss_group_a.is_complete and regional.swiss_group_b.is_complete:
                regional.advance_stage()
                self.season_manager.add_event(
                    "stage_complete",
                    "🏆 Swiss Groups complete! Top 16 advance to playoffs."
                )
        
        elif regional.current_stage == 'swiss_playoffs':
            results.extend(self._run_swiss_round(regional.swiss_playoffs, "Playoffs"))
            
            if regional.swiss_playoffs.is_complete:
                regional.advance_stage()
                self.season_manager.add_event(
                    "stage_complete",
                    "🏆 Swiss Playoffs complete! Top 8 advance to bracket."
                )
        
        elif regional.current_stage == 'double_elim':
            results.extend(self._run_double_elim_round(regional.double_elim))
            
            if regional.double_elim.is_complete:
                regional.advance_stage()
        
        return results
    
    def _run_swiss_round(self, bracket: SwissBracket, stage_name: str) -> List[dict]:
        """Run one round of a Swiss bracket."""
        if bracket.is_complete:
            return []
        
        # Generate matchups for this round
        matchups = bracket.generate_round_matchups()
        if not matchups:
            return []
        
        results = []
        match_engine = self.season_manager.match_engine
        
        for team1_id, team2_id in matchups:
            team1 = self.teams.get(team1_id)
            team2 = self.teams.get(team2_id)
            
            if not team1 or not team2:
                continue
            
            # Get rosters
            roster1 = self.get_team_roster(team1_id)
            roster2 = self.get_team_roster(team2_id)
            
            # Simulate the series
            series_result = match_engine.simulate_series(
                team1, team2, roster1, roster2, best_of=bracket.best_of
            )
            
            # Record result in bracket
            bracket.record_result(
                team1_id, team2_id,
                series_result.home_wins, series_result.away_wins
            )
            
            # Update team stats
            self._update_team_stats(series_result)
            
            # Update morale and chemistry
            team1_won = series_result.winner_id == team1_id
            self.update_morale_after_match(team1_id, team1_won)
            self.update_chemistry_after_match(team1_id, team1_won)
            self.update_morale_after_match(team2_id, not team1_won)
            self.update_chemistry_after_match(team2_id, not team1_won)
            
            result_dict = {
                'stage': stage_name,
                'round': bracket.current_round,
                'team1': team1.name,
                'team2': team2.name,
                'team1_id': team1_id,
                'team2_id': team2_id,
                'score': f"{series_result.home_wins}-{series_result.away_wins}",
                'winner': self.teams[series_result.winner_id].name,
                'winner_id': series_result.winner_id,
                'team1_record': bracket.records[team1_id].record_str,
                'team2_record': bracket.records[team2_id].record_str
            }
            results.append(result_dict)
            
            # Log player team matches
            if self.player_team_id in [team1_id, team2_id]:
                player_won = series_result.winner_id == self.player_team_id
                opponent = team2.name if team1_id == self.player_team_id else team1.name
                player_record = bracket.records[self.player_team_id].record_str
                
                if player_won:
                    self.season_manager.add_event(
                        "match_win",
                        f"✅ Victory vs {opponent}! Record: {player_record}",
                        data=result_dict
                    )
                else:
                    self.season_manager.add_event(
                        "match_loss",
                        f"❌ Loss vs {opponent}. Record: {player_record}",
                        data=result_dict
                    )
                
                # Check for elimination or qualification
                player_rec = bracket.records[self.player_team_id]
                if player_rec.wins >= bracket.win_threshold:
                    self.season_manager.add_event(
                        "qualified",
                        f"🎉 QUALIFIED! Advanced with {player_record} record!"
                    )
                elif player_rec.losses >= bracket.loss_threshold:
                    self.season_manager.add_event(
                        "eliminated",
                        f"💔 Eliminated from {stage_name} with {player_record} record."
                    )
        
        return results
    
    def _run_double_elim_round(self, bracket: DoubleEliminationBracket) -> List[dict]:
        """Run matches in the double elimination bracket."""
        results = []
        matches = bracket.get_next_matches()
        
        if not matches:
            return []
        
        match_engine = self.season_manager.match_engine
        
        for match in matches:
            team1_id = match['team1']
            team2_id = match['team2']
            
            if not team1_id or not team2_id:
                continue
            
            team1 = self.teams.get(team1_id)
            team2 = self.teams.get(team2_id)
            
            if not team1 or not team2:
                continue
            
            roster1 = self.get_team_roster(team1_id)
            roster2 = self.get_team_roster(team2_id)
            
            series_result = match_engine.simulate_series(
                team1, team2, roster1, roster2, best_of=bracket.best_of
            )
            
            bracket.record_result(
                match['match_id'],
                series_result.winner_id,
                series_result.home_wins,
                series_result.away_wins
            )
            
            self._update_team_stats(series_result)
            
            team1_won = series_result.winner_id == team1_id
            self.update_morale_after_match(team1_id, team1_won)
            self.update_chemistry_after_match(team1_id, team1_won)
            self.update_morale_after_match(team2_id, not team1_won)
            self.update_chemistry_after_match(team2_id, not team1_won)
            
            result_dict = {
                'stage': 'Playoffs',
                'match_id': match['match_id'],
                'team1': team1.name,
                'team2': team2.name,
                'team1_id': team1_id,
                'team2_id': team2_id,
                'score': f"{series_result.home_wins}-{series_result.away_wins}",
                'winner': self.teams[series_result.winner_id].name,
                'winner_id': series_result.winner_id
            }
            results.append(result_dict)
            
            # Log player team matches
            if self.player_team_id in [team1_id, team2_id]:
                player_won = series_result.winner_id == self.player_team_id
                opponent = team2.name if team1_id == self.player_team_id else team1.name
                
                if player_won:
                    self.season_manager.add_event(
                        "bracket_win",
                        f"✅ Bracket win vs {opponent}!",
                        data=result_dict
                    )
                else:
                    self.season_manager.add_event(
                        "bracket_loss",
                        f"❌ Bracket loss vs {opponent}.",
                        data=result_dict
                    )
        
        return results
    
    def _update_team_stats(self, result):
        """Update team season stats from a match result."""
        winner = self.teams.get(result.winner_id)
        loser = self.teams.get(result.loser_id)
        
        if winner:
            winner.season_stats.series_wins += 1
            winner.season_stats.wins += result.home_wins if result.winner_id == result.home_team_id else result.away_wins
            winner.season_stats.losses += result.away_wins if result.winner_id == result.home_team_id else result.home_wins
            winner.season_stats.goals_for += sum(g.home_score if result.winner_id == result.home_team_id else g.away_score for g in result.games)
            winner.season_stats.goals_against += sum(g.away_score if result.winner_id == result.home_team_id else g.home_score for g in result.games)
        
        if loser:
            loser.season_stats.series_losses += 1
            loser.season_stats.wins += result.home_wins if result.loser_id == result.home_team_id else result.away_wins
            loser.season_stats.losses += result.away_wins if result.loser_id == result.home_team_id else result.home_wins
            loser.season_stats.goals_for += sum(g.home_score if result.loser_id == result.home_team_id else g.away_score for g in result.games)
            loser.season_stats.goals_against += sum(g.away_score if result.loser_id == result.home_team_id else g.home_score for g in result.games)
    
    def _finalize_regional(self):
        """Finalize regional and award points."""
        if not self.current_regional:
            return
        
        regional = self.current_regional
        
        # Award points
        for team_id, points in regional.points_earned.items():
            if team_id not in self.season_points:
                self.season_points[team_id] = 0
            self.season_points[team_id] += points
            
            # Store in team stats
            team = self.teams.get(team_id)
            if team:
                placement = regional.final_placements.get(team_id, 32)
                team.season_stats.regional_placements.append(placement)
        
        # Log player team result
        if self.player_team_id:
            placement = regional.final_placements.get(self.player_team_id, 32)
            points = regional.points_earned.get(self.player_team_id, 0)
            total_points = self.season_points.get(self.player_team_id, 0)
            
            if placement <= 3:
                self.season_manager.add_event(
                    "regional_podium",
                    f"🏆 {placement}{'st' if placement == 1 else 'nd' if placement == 2 else 'rd'} PLACE! +{points} points (Total: {total_points})"
                )
            elif placement <= 8:
                self.season_manager.add_event(
                    "regional_top8",
                    f"🎯 Top 8 finish ({placement}th). +{points} points (Total: {total_points})"
                )
            elif placement <= 16:
                self.season_manager.add_event(
                    "regional_top16",
                    f"📊 Top 16 finish ({placement}th). +{points} points (Total: {total_points})"
                )
            else:
                self.season_manager.add_event(
                    "regional_eliminated",
                    f"📉 Eliminated in groups ({placement}th). 0 points (Total: {total_points})"
                )
        
        self.current_regional = None
    
    def start_regional(self):
        """Start a new regional tournament."""
        team_ids = list(self.teams.keys())
        
        if len(team_ids) != 32:
            raise ValueError(f"Need 32 teams for regional, have {len(team_ids)}")
        
        phase_name = self.current_phase.value.replace('_', ' ').title()
        self.current_regional = RegionalTournament(
            teams=team_ids,
            name=phase_name
        )
        
        # Log which group player is in
        if self.player_team_id:
            if self.player_team_id in self.current_regional.swiss_group_a.team_ids:
                group = "A"
            else:
                group = "B"
            self.season_manager.add_event(
                "regional_start",
                f"🏁 {phase_name} begins! You're in Group {group}."
            )
    
    def get_tournament_status(self) -> Optional[dict]:
        """Get current tournament status for display."""
        if not self.current_regional:
            return None
        
        regional = self.current_regional
        status = {
            'stage': regional.get_current_stage_name(),
            'is_complete': regional.is_complete()
        }
        
        if regional.current_stage == 'swiss_groups':
            # Get player's group status
            if self.player_team_id in regional.swiss_group_a.team_ids:
                bracket = regional.swiss_group_a
                status['group'] = 'A'
            else:
                bracket = regional.swiss_group_b
                status['group'] = 'B'
            
            player_rec = bracket.records.get(self.player_team_id)
            if player_rec:
                status['record'] = player_rec.record_str
                status['qualified'] = self.player_team_id in bracket.qualified
                status['eliminated'] = self.player_team_id in bracket.eliminated
            
            status['standings'] = self._get_swiss_standings(bracket)
        
        elif regional.current_stage == 'swiss_playoffs':
            bracket = regional.swiss_playoffs
            player_rec = bracket.records.get(self.player_team_id)
            if player_rec:
                status['record'] = player_rec.record_str
                status['qualified'] = self.player_team_id in bracket.qualified
                status['eliminated'] = self.player_team_id in bracket.eliminated
            else:
                status['eliminated'] = True  # Didn't make playoffs
            
            status['standings'] = self._get_swiss_standings(bracket)
        
        elif regional.current_stage == 'double_elim':
            bracket = regional.double_elim
            status['bracket'] = self._get_bracket_status(bracket)
        
        return status
    
    def _get_swiss_standings(self, bracket: SwissBracket) -> List[dict]:
        """Get Swiss bracket standings for display."""
        standings = []
        for rec in bracket.get_standings():
            team = self.teams.get(rec.team_id)
            if team:
                status = ""
                if rec.team_id in bracket.qualified:
                    status = "✅"
                elif rec.team_id in bracket.eliminated:
                    status = "❌"
                
                standings.append({
                    'team_id': rec.team_id,
                    'team_name': team.name,
                    'record': rec.record_str,
                    'game_diff': f"+{rec.game_diff}" if rec.game_diff > 0 else str(rec.game_diff),
                    'status': status,
                    'is_player': rec.team_id == self.player_team_id
                })
        return standings
    
    def _get_bracket_status(self, bracket: DoubleEliminationBracket) -> dict:
        """Get double elim bracket status for display."""
        return {
            'placements': bracket.placements,
            'current_phase': bracket.current_phase,
            'is_complete': bracket.is_complete
        }
    
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
        
        # Store rosters before advancing from Split 1 Major (for chemistry calculation)
        if self.current_phase == SeasonPhase.SPLIT1_MAJOR:
            self.store_split1_rosters()
        
        new_phase = self.season_manager.advance_phase()
        
        # Start regional tournaments
        if new_phase in REGIONAL_PHASES:
            self.start_regional()
        
        # AI teams make moves between regional phases and during breaks
        ai_move_phases = [
            SeasonPhase.SPLIT1_REGIONAL_2, SeasonPhase.SPLIT1_REGIONAL_3,
            SeasonPhase.SPLIT2_REGIONAL_2, SeasonPhase.SPLIT2_REGIONAL_3,
            SeasonPhase.SPLIT_BREAK, SeasonPhase.OFFSEASON
        ]
        if self.league_ai and new_phase in ai_move_phases:
            self.process_ai_moves()
        
        # Process split break (progression + training camp + chemistry boost)
        if new_phase == SeasonPhase.SPLIT_BREAK:
            self.process_split_break()
        
        # Process season end (bigger progression + aging)
        if new_phase == SeasonPhase.SEASON_END:
            self.process_season_end_progression()
            self.season_manager.process_end_of_season()
            
            # Reset streaks for all teams
            for team in self.teams.values():
                team.streak = 0
            
            # Reset season points
            self.season_points = {tid: 0 for tid in self.teams}
        
        return new_phase
    
    def start_new_season(self):
        """
        Start a new season.
        Adds rookies (with guaranteed star potential), manages FA pool size.
        """
        if not self.season_manager:
            return
        
        # ===== RETIRE OLD FREE AGENTS =====
        # Keep pool manageable by removing older/weaker FAs
        self.free_agent_ids = retire_old_free_agents(
            self.free_agent_ids,
            self.players,
            max_age=28,
            target_count=25
        )
        
        # ===== ADD ROOKIE CLASS =====
        # New young players entering the scene (guaranteed star after Worlds!)
        rookies = generate_rookie_class(
            self.league.region, 
            count=6,  # 6 new rookies each season
            guarantee_star=True  # At least one has 90+ potential
        )
        
        for rookie in rookies:
            self.players[rookie.id] = rookie
            self.free_agent_ids.append(rookie.id)
        
        # Log the rookies
        star_rookies = [r for r in rookies if r.hidden.potential >= 85]
        if star_rookies:
            names = ", ".join(r.name for r in star_rookies)
            self.season_manager.add_event(
                "rookie_class",
                f"🌟 New rookie class announced! High-potential prospects: {names}",
                data={'rookies': [r.to_dict() for r in star_rookies]}
            )
        else:
            self.season_manager.add_event(
                "rookie_class",
                f"🎓 {len(rookies)} new rookies enter the free agent pool",
                data={'count': len(rookies)}
            )
        
        # ===== ADD REGULAR FREE AGENTS =====
        # Fill back up to ~30 total if needed
        current_count = len(self.free_agent_ids)
        if current_count < 30:
            new_fas = generate_free_agent_pool(self.league.region, count=30 - current_count)
            for fa in new_fas:
                self.players[fa.id] = fa
                self.free_agent_ids.append(fa.id)
        
        # ===== AI OFFSEASON MOVES =====
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
