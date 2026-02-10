"""
AI Team Management for Rocket League GM Simulator.
Handles AI decision-making for roster moves, signings, and releases.
"""

from typing import List, Dict, Optional, Tuple
import random

from ..models.player import Player
from ..models.team import Team, Contract


class TeamAI:
    """
    AI manager for a single team.
    Makes decisions about roster moves, signings, and releases.
    """
    
    def __init__(self, team: Team, personality: str = "balanced"):
        self.team = team
        self.personality = personality  # "aggressive", "balanced", "conservative", "rebuilding"
        
        # Personality affects decision thresholds
        self.traits = self._get_personality_traits()
    
    def _get_personality_traits(self) -> dict:
        """Get AI behavior thresholds based on personality."""
        personalities = {
            "aggressive": {
                "min_roster_overall": 70,      # Won't keep players below this
                "signing_threshold": 0.8,       # How much better FA needs to be
                "budget_aggression": 0.9,       # Willing to spend this % of budget
                "release_threshold": 0.7,       # Release if player < this % of team avg
                "young_player_bonus": 5,        # Bonus OVR points for young players
            },
            "balanced": {
                "min_roster_overall": 60,
                "signing_threshold": 1.0,
                "budget_aggression": 0.7,
                "release_threshold": 0.6,
                "young_player_bonus": 8,
            },
            "conservative": {
                "min_roster_overall": 50,
                "signing_threshold": 1.2,
                "budget_aggression": 0.5,
                "release_threshold": 0.5,
                "young_player_bonus": 10,
            },
            "rebuilding": {
                "min_roster_overall": 40,
                "signing_threshold": 0.9,
                "budget_aggression": 0.6,
                "release_threshold": 0.8,       # More willing to release veterans
                "young_player_bonus": 15,       # Heavy preference for youth
            }
        }
        return personalities.get(self.personality, personalities["balanced"])
    
    def evaluate_player_value(self, player: Player) -> float:
        """
        Calculate a player's value to the team.
        Returns a score considering OVR, age, potential, and salary.
        """
        base_value = player.overall
        
        # Age adjustment (prefer 18-23 range)
        if player.age < 18:
            age_mod = 0.9 + (player.age - 15) * 0.03
        elif player.age <= 23:
            age_mod = 1.1
        elif player.age <= 26:
            age_mod = 1.0 - (player.age - 23) * 0.05
        else:
            age_mod = 0.7 - (player.age - 26) * 0.1
        
        # Potential bonus for young players
        if player.age < 22:
            potential_bonus = (player.hidden.potential - player.overall) * 0.3
        else:
            potential_bonus = 0
        
        # Young player bonus from personality
        youth_bonus = 0
        if player.age < 21:
            youth_bonus = self.traits["young_player_bonus"] * (21 - player.age) / 5
        
        return (base_value * age_mod) + potential_bonus + youth_bonus
    
    def evaluate_roster_need(self, players: Dict[str, Player]) -> dict:
        """
        Analyze current roster and identify needs.
        Returns dict with analysis results.
        """
        roster_players = [players[pid] for pid in self.team.roster if pid in players]
        
        if not roster_players:
            return {
                "needs_players": True,
                "roster_size": 0,
                "avg_overall": 0,
                "weakest_player_id": None,
                "weakest_value": 0
            }
        
        # Calculate roster metrics
        avg_overall = sum(p.overall for p in roster_players) / len(roster_players)
        
        # Find weakest player by value
        player_values = [(p, self.evaluate_player_value(p)) for p in roster_players]
        player_values.sort(key=lambda x: x[1])
        weakest = player_values[0] if player_values else (None, 0)
        
        # Identify specific needs
        avg_age = sum(p.age for p in roster_players) / len(roster_players)
        
        return {
            "needs_players": len(roster_players) < 3,
            "roster_size": len(roster_players),
            "avg_overall": avg_overall,
            "avg_age": avg_age,
            "weakest_player_id": weakest[0].id if weakest[0] else None,
            "weakest_value": weakest[1],
            "has_sub": len(roster_players) >= 4
        }
    
    def should_release_player(
        self, 
        player: Player, 
        roster_analysis: dict
    ) -> Tuple[bool, str]:
        """
        Decide if a player should be released.
        Returns (should_release, reason).
        """
        # Never release if roster too small
        if roster_analysis["roster_size"] <= 3:
            return False, ""
        
        player_value = self.evaluate_player_value(player)
        
        # Release if significantly below team average
        threshold = roster_analysis["avg_overall"] * self.traits["release_threshold"]
        if player.overall < threshold:
            return True, f"performance below team standards (OVR {player.overall})"
        
        # Release expensive underperformers
        contract = self.team.contracts.get(player.id)
        if contract:
            # With yearly salaries ($12k-$150k), adjust threshold accordingly
            value_per_dollar = player_value / max(contract.salary, 12000)
            if value_per_dollar < 0.001 and player.overall < roster_analysis["avg_overall"]:
                return True, f"salary too high for performance"
        
        # Release old players on rebuilding teams
        if self.personality == "rebuilding" and player.age > 25:
            if player.overall < roster_analysis["avg_overall"] + 5:
                return True, f"rebuilding with youth focus"
        
        return False, ""
    
    def evaluate_free_agent(
        self, 
        free_agent: Player, 
        roster_analysis: dict,
        max_salary: int
    ) -> Tuple[bool, int, str]:
        """
        Evaluate whether to sign a free agent.
        Returns (should_sign, offer_salary, reason).
        """
        fa_value = self.evaluate_player_value(free_agent)
        
        # Calculate appropriate yearly salary offer based on overall
        # Use a simple tier system similar to ContractNegotiator
        if free_agent.overall >= 85:
            base_salary = 100000
        elif free_agent.overall >= 80:
            base_salary = 75000
        elif free_agent.overall >= 75:
            base_salary = 55000
        elif free_agent.overall >= 70:
            base_salary = 42000
        elif free_agent.overall >= 65:
            base_salary = 32000
        elif free_agent.overall >= 60:
            base_salary = 24000
        else:
            base_salary = 18000
        
        # Adjust based on how much we want them
        if fa_value > roster_analysis["avg_overall"] * 1.1:
            salary_mod = 1.2  # Pay premium for upgrades
        elif fa_value > roster_analysis["avg_overall"]:
            salary_mod = 1.0
        else:
            salary_mod = 0.8
        
        offer_salary = int(base_salary * salary_mod)
        offer_salary = max(12000, min(offer_salary, max_salary))  # Min $12k/year
        
        # Decision logic
        reason = ""
        should_sign = False
        
        # Must sign if roster too small
        if roster_analysis["roster_size"] < 3:
            should_sign = True
            reason = "roster below minimum"
        
        # Sign if clear upgrade
        elif fa_value > roster_analysis["weakest_value"] * self.traits["signing_threshold"]:
            if roster_analysis["roster_size"] < 4 or fa_value > roster_analysis["avg_overall"]:
                should_sign = True
                reason = f"upgrade over current roster"
        
        # Sign promising young players
        elif free_agent.age < 20 and free_agent.hidden.potential > 75:
            if roster_analysis["roster_size"] < 5:
                should_sign = True
                reason = f"high potential prospect"
        
        # Need a substitute
        elif not roster_analysis["has_sub"] and roster_analysis["roster_size"] < 4:
            if fa_value > roster_analysis["avg_overall"] * 0.8:
                should_sign = True
                reason = "need substitute player"
        
        return should_sign, offer_salary, reason
    
    def make_roster_decisions(
        self,
        players: Dict[str, Player],
        free_agents: List[Player]
    ) -> List[dict]:
        """
        Main decision-making function. Called periodically.
        Returns list of actions taken.
        """
        actions = []
        
        # Analyze current roster
        analysis = self.evaluate_roster_need(players)
        
        # Phase 1: Consider releases
        roster_players = [players[pid] for pid in self.team.roster if pid in players]
        for player in roster_players:
            should_release, reason = self.should_release_player(player, analysis)
            if should_release:
                actions.append({
                    "type": "release",
                    "player_id": player.id,
                    "player_name": player.name,
                    "reason": reason
                })
                # Update analysis after release decision
                analysis["roster_size"] -= 1
        
        # Phase 2: Consider signings
        max_budget = int(self.team.salary_cap_space * self.traits["budget_aggression"])
        
        # Sort free agents by value to this team
        fa_evaluated = [
            (fa, self.evaluate_player_value(fa)) 
            for fa in free_agents
        ]
        fa_evaluated.sort(key=lambda x: x[1], reverse=True)
        
        signings_this_cycle = 0
        max_signings = 2  # Don't sign too many at once
        
        for fa, fa_value in fa_evaluated:
            if signings_this_cycle >= max_signings:
                break
            
            if analysis["roster_size"] >= 5:
                break
            
            should_sign, offer_salary, reason = self.evaluate_free_agent(
                fa, analysis, max_budget
            )
            
            if should_sign and offer_salary <= max_budget:
                actions.append({
                    "type": "sign",
                    "player_id": fa.id,
                    "player_name": fa.name,
                    "salary": offer_salary,
                    "reason": reason
                })
                signings_this_cycle += 1
                analysis["roster_size"] += 1
                max_budget -= offer_salary
        
        return actions


class LeagueAI:
    """
    Manages AI decisions for all non-player teams in the league.
    """
    
    def __init__(
        self,
        teams: Dict[str, Team],
        players: Dict[str, Player],
        player_team_id: str = None
    ):
        self.teams = teams
        self.players = players
        self.player_team_id = player_team_id
        
        # Create AI managers for each AI team
        self.team_ais: Dict[str, TeamAI] = {}
        self._initialize_team_ais()
    
    def _initialize_team_ais(self):
        """Create AI managers with varied personalities."""
        personalities = ["aggressive", "balanced", "balanced", "conservative", "rebuilding"]
        
        for team_id, team in self.teams.items():
            if team_id == self.player_team_id:
                continue  # Skip player's team
            
            # Assign personality based on team strength
            roster = [self.players[pid] for pid in team.roster if pid in self.players]
            avg_ovr = sum(p.overall for p in roster) / len(roster) if roster else 50
            
            if avg_ovr > 70:
                personality = random.choice(["aggressive", "balanced"])
            elif avg_ovr > 60:
                personality = random.choice(["balanced", "conservative"])
            else:
                personality = random.choice(["rebuilding", "conservative", "balanced"])
            
            self.team_ais[team_id] = TeamAI(team, personality)
    
    def process_ai_decisions(
        self,
        free_agent_ids: List[str]
    ) -> Tuple[List[dict], List[str]]:
        """
        Process AI decisions for all teams.
        Returns (list of all actions, updated free_agent_ids).
        """
        all_actions = []
        
        # Get current free agents
        free_agents = [self.players[pid] for pid in free_agent_ids if pid in self.players]
        
        # Randomize order so same team doesn't always get first pick
        team_order = list(self.team_ais.keys())
        random.shuffle(team_order)
        
        for team_id in team_order:
            ai = self.team_ais[team_id]
            team = self.teams[team_id]
            
            # Get decisions
            actions = ai.make_roster_decisions(self.players, free_agents)
            
            # Execute actions
            for action in actions:
                action["team_id"] = team_id
                action["team_name"] = team.name
                
                if action["type"] == "release":
                    # Execute release
                    player_id = action["player_id"]
                    if player_id in team.roster:
                        team.remove_player(player_id)
                        self.players[player_id].team_id = None
                        free_agent_ids.append(player_id)
                        free_agents.append(self.players[player_id])
                        all_actions.append(action)
                
                elif action["type"] == "sign":
                    # Execute signing
                    player_id = action["player_id"]
                    if player_id in free_agent_ids and team.roster_size < 5:
                        salary = action["salary"]
                        years = random.randint(1, 3)  # 1-3 year contracts
                        contract = Contract(
                            player_id=player_id,
                            team_id=team_id,
                            salary=salary,
                            years=years,
                            buyout=salary * 2
                        )
                        team.add_player(player_id, contract)
                        self.players[player_id].team_id = team_id
                        free_agent_ids.remove(player_id)
                        free_agents = [fa for fa in free_agents if fa.id != player_id]
                        all_actions.append(action)
        
        return all_actions, free_agent_ids
    
    def get_team_ai(self, team_id: str) -> Optional[TeamAI]:
        """Get the AI manager for a specific team."""
        return self.team_ais.get(team_id)
