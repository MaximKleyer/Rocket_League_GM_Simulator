"""
Contract Negotiation System for Rocket League GM Simulator.
Handles player signings, re-signings, and contract negotiations.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple, Dict
import random

from ..models.player import Player
from ..models.team import Team, Contract


class Willingness(Enum):
    """Player's willingness to sign/re-sign with a team."""
    WANTS_TO_LEAVE = 1
    UNLIKELY = 2
    NEUTRAL = 3
    LIKELY = 4
    EAGER = 5
    
    def __str__(self):
        labels = {
            Willingness.WANTS_TO_LEAVE: "Wants to Leave",
            Willingness.UNLIKELY: "Unlikely",
            Willingness.NEUTRAL: "Neutral",
            Willingness.LIKELY: "Likely",
            Willingness.EAGER: "Eager to Join"
        }
        return labels[self]
    
    @property
    def color_indicator(self) -> str:
        """Get emoji indicator for willingness."""
        indicators = {
            Willingness.WANTS_TO_LEAVE: "🔴",
            Willingness.UNLIKELY: "🟠",
            Willingness.NEUTRAL: "🟡",
            Willingness.LIKELY: "🟢",
            Willingness.EAGER: "💚"
        }
        return indicators[self]


@dataclass
class NegotiationState:
    """Tracks the state of an ongoing negotiation."""
    player_id: str
    team_id: str
    is_re_sign: bool  # True if re-signing existing player, False if new signing
    
    # Initial values
    initial_willingness: Willingness = Willingness.NEUTRAL
    current_willingness: Willingness = Willingness.NEUTRAL
    asking_price: int = 0  # Yearly salary player wants
    market_value: int = 0  # Calculated market value
    previous_salary: int = 0  # Previous/current salary (0 for free agents)
    
    # Negotiation tracking
    offers_made: int = 0
    max_offers: int = 3
    last_offer: int = 0
    negotiations_ended: bool = False
    
    def can_make_offer(self) -> bool:
        """Check if more offers can be made."""
        return self.offers_made < self.max_offers and not self.negotiations_ended


class ContractNegotiator:
    """
    Handles contract negotiations between teams and players.
    """
    
    # Base yearly salaries by overall rating tier
    SALARY_TIERS = {
        90: 150000,  # Superstar
        85: 120000,  # Star
        80: 90000,   # Very Good
        75: 70000,   # Good
        70: 55000,   # Above Average
        65: 42000,   # Average
        60: 32000,   # Below Average
        55: 24000,   # Prospect
        50: 18000,   # Low
        0: 12000,    # Minimum
    }
    
    @classmethod
    def calculate_market_value(
        cls,
        player: Player,
        team_stats: Optional[Dict] = None
    ) -> int:
        """
        Calculate a player's market value (yearly salary).
        Based on overall rating and performance.
        """
        # Get base salary from tier
        base_salary = cls.SALARY_TIERS[0]
        for threshold, salary in sorted(cls.SALARY_TIERS.items(), reverse=True):
            if player.overall >= threshold:
                base_salary = salary
                break
        
        # Age modifier
        if player.age < 18:
            age_mod = 0.7  # Young, unproven
        elif player.age < 21:
            age_mod = 0.9  # Young talent
        elif player.age < 25:
            age_mod = 1.0  # Prime
        elif player.age < 28:
            age_mod = 0.9  # Experienced but aging
        else:
            age_mod = 0.7  # Veteran
        
        # Potential modifier (for young players)
        if player.age < 22:
            potential_mod = 1.0 + (player.hidden.potential - 70) * 0.01
        else:
            potential_mod = 1.0
        
        # Performance modifier (if team stats provided)
        perf_mod = 1.0
        if team_stats:
            wins = team_stats.get('wins', 0)
            losses = team_stats.get('losses', 0)
            total = wins + losses
            if total > 0:
                win_rate = wins / total
                # +/- 20% based on team performance
                perf_mod = 0.8 + (win_rate * 0.4)
        
        market_value = int(base_salary * age_mod * potential_mod * perf_mod)
        
        # Ensure minimum salary
        return max(12000, market_value)
    
    @classmethod
    def calculate_asking_price(
        cls,
        market_value: int,
        willingness: Willingness,
        previous_salary: int = 0
    ) -> int:
        """
        Calculate what the player is asking for.
        Players who don't want to join ask for more.
        """
        # Base asking is market value
        asking = market_value
        
        # Willingness modifier
        will_mods = {
            Willingness.WANTS_TO_LEAVE: 1.5,   # Wants much more to stay
            Willingness.UNLIKELY: 1.25,        # Wants premium
            Willingness.NEUTRAL: 1.1,          # Slight premium
            Willingness.LIKELY: 1.0,           # Fair market
            Willingness.EAGER: 0.9,            # Willing to take less
        }
        asking = int(asking * will_mods[willingness])
        
        # If re-signing, factor in previous salary
        if previous_salary > 0:
            # Players expect at least their previous salary
            if asking < previous_salary:
                asking = int((asking + previous_salary) / 2)
        
        return asking
    
    @classmethod
    def calculate_willingness(
        cls,
        player: Player,
        team: Team,
        is_re_sign: bool,
        league_standings: Optional[list] = None
    ) -> Willingness:
        """
        Calculate player's willingness to sign with a team.
        
        Factors:
        - Team performance (standings)
        - Player morale (for re-signs)
        - Age factors (young want playing time, vets want stability)
        """
        score = 50  # Start neutral
        
        # === TEAM PERFORMANCE ===
        if league_standings:
            # Find team position in standings
            team_position = None
            for i, standing in enumerate(league_standings):
                if standing.get('team_id') == team.id:
                    team_position = i + 1
                    break
            
            if team_position:
                num_teams = len(league_standings)
                # Top half of standings = bonus, bottom half = penalty
                if team_position <= num_teams // 4:  # Top 25%
                    score += 25
                elif team_position <= num_teams // 2:  # Top 50%
                    score += 10
                elif team_position <= (num_teams * 3) // 4:  # Bottom 50%
                    score -= 10
                else:  # Bottom 25%
                    score -= 20
        
        # === MORALE (for re-signs) ===
        if is_re_sign:
            morale_bonus = (player.morale - 50) // 5  # -8 to +10
            score += morale_bonus
        
        # === AGE FACTORS ===
        if player.age < 20:
            # Young players want playing time on competitive teams
            # Check if they'd be a starter (simplified - check overall)
            if player.overall >= 70:
                score += 5  # Good enough to start anywhere
            else:
                score -= 5  # Might be worried about playing time
        elif player.age >= 26:
            # Veterans prefer stability
            if is_re_sign:
                score += 15  # Prefer to stay
            else:
                score -= 5  # Hesitant to change teams
        
        # === TEAM CHEMISTRY ===
        if team.chemistry >= 80:
            score += 10
        elif team.chemistry >= 60:
            score += 5
        elif team.chemistry < 40:
            score -= 10
        
        # === CONVERT TO WILLINGNESS ===
        if score >= 75:
            return Willingness.EAGER
        elif score >= 60:
            return Willingness.LIKELY
        elif score >= 40:
            return Willingness.NEUTRAL
        elif score >= 25:
            return Willingness.UNLIKELY
        else:
            return Willingness.WANTS_TO_LEAVE
    
    @classmethod
    def start_negotiation(
        cls,
        player: Player,
        team: Team,
        is_re_sign: bool,
        league_standings: Optional[list] = None,
        team_stats: Optional[Dict] = None,
        previous_salary: int = 0
    ) -> NegotiationState:
        """
        Start a new contract negotiation.
        Returns the initial negotiation state.
        """
        # Calculate willingness
        willingness = cls.calculate_willingness(
            player, team, is_re_sign, league_standings
        )
        
        # Calculate market value
        market_value = cls.calculate_market_value(player, team_stats)
        
        # Calculate asking price
        asking_price = cls.calculate_asking_price(
            market_value, willingness, previous_salary
        )
        
        return NegotiationState(
            player_id=player.id,
            team_id=team.id,
            is_re_sign=is_re_sign,
            initial_willingness=willingness,
            current_willingness=willingness,
            asking_price=asking_price,
            market_value=market_value,
            previous_salary=previous_salary,
            offers_made=0,
            max_offers=3,
            negotiations_ended=False
        )
    
    @classmethod
    def make_offer(
        cls,
        state: NegotiationState,
        offered_salary: int,
        offered_years: int
    ) -> Tuple[bool, str]:
        """
        Make a contract offer to the player.
        
        Returns:
            (accepted: bool, message: str)
        """
        if not state.can_make_offer():
            return False, "Negotiations have ended."
        
        state.offers_made += 1
        state.last_offer = offered_salary
        
        # Calculate how offer compares to asking price
        offer_ratio = offered_salary / state.asking_price if state.asking_price > 0 else 1.0
        
        # Base acceptance thresholds by willingness
        acceptance_thresholds = {
            Willingness.EAGER: 0.80,        # Will accept 80% of asking
            Willingness.LIKELY: 0.90,       # Will accept 90% of asking
            Willingness.NEUTRAL: 0.95,      # Will accept 95% of asking
            Willingness.UNLIKELY: 1.00,     # Needs full asking price
            Willingness.WANTS_TO_LEAVE: 1.10,  # Needs premium
        }
        
        threshold = acceptance_thresholds[state.current_willingness]
        
        # Contract length affects acceptance
        # Players generally prefer longer contracts for security
        length_bonus = 0
        if offered_years >= 3:
            length_bonus = 0.05  # 5% bonus for long-term security
        elif offered_years == 1:
            length_bonus = -0.05  # Penalty for short-term
        
        effective_ratio = offer_ratio + length_bonus
        
        # Check if offer is accepted
        if effective_ratio >= threshold:
            state.negotiations_ended = True
            return True, f"{_get_player_name(state)} accepts the offer!"
        
        # Offer rejected - check if it was insulting (20%+ below asking)
        if offer_ratio < 0.80:
            # Insulting offer - willingness drops
            old_will = state.current_willingness
            new_will_value = max(1, state.current_willingness.value - 1)
            state.current_willingness = Willingness(new_will_value)
            
            # Recalculate asking price with new willingness
            state.asking_price = cls.calculate_asking_price(
                state.market_value,
                state.current_willingness,
                state.previous_salary
            )
            
            if state.offers_made >= state.max_offers:
                state.negotiations_ended = True
                return False, f"{_get_player_name(state)} is offended by the lowball offer and walks away!"
            else:
                return False, f"{_get_player_name(state)} is insulted by the offer. Willingness dropped from {old_will} to {state.current_willingness}."
        
        # Normal rejection
        if state.offers_made >= state.max_offers:
            state.negotiations_ended = True
            return False, f"{_get_player_name(state)} rejects the final offer. Negotiations have ended."
        
        # Calculate how close they were
        percent_of_asking = int(offer_ratio * 100)
        return False, f"{_get_player_name(state)} rejects the offer ({percent_of_asking}% of asking). {state.max_offers - state.offers_made} offer(s) remaining."
    
    @classmethod
    def end_negotiations(cls, state: NegotiationState) -> str:
        """
        End negotiations without a deal.
        """
        state.negotiations_ended = True
        if state.is_re_sign:
            return f"Contract talks with {_get_player_name(state)} have broken down. They will become a free agent."
        else:
            return f"You've ended negotiations with {_get_player_name(state)}."


def _get_player_name(state: NegotiationState) -> str:
    """Helper to get player name - would need actual player reference in real use."""
    return "The player"  # Placeholder - actual name passed in UI


@dataclass
class ExpiringContract:
    """Represents a contract that is expiring at season end."""
    player_id: str
    player_name: str
    team_id: str
    current_salary: int
    years_on_team: int  # How long they've been with the team
    
    def to_dict(self) -> dict:
        return {
            'player_id': self.player_id,
            'player_name': self.player_name,
            'team_id': self.team_id,
            'current_salary': self.current_salary,
            'years_on_team': self.years_on_team
        }


class ContractManager:
    """
    Manages contract expiration and renewal across the league.
    """
    
    @staticmethod
    def get_expiring_contracts(team: Team, players: Dict[str, Player]) -> list:
        """
        Get list of contracts expiring at end of season (1 year remaining).
        """
        expiring = []
        for player_id, contract in team.contracts.items():
            if contract.years <= 1:
                player = players.get(player_id)
                if player:
                    expiring.append(ExpiringContract(
                        player_id=player_id,
                        player_name=player.name,
                        team_id=team.id,
                        current_salary=contract.salary,
                        years_on_team=1  # Could track this properly
                    ))
        return expiring
    
    @staticmethod
    def process_contract_year(team: Team):
        """
        Process one year passing for all contracts.
        Called at season end.
        """
        expired_players = []
        for player_id, contract in list(team.contracts.items()):
            contract.years -= 1
            if contract.years <= 0:
                expired_players.append(player_id)
        
        return expired_players
    
    @staticmethod
    def create_contract(
        player_id: str,
        team_id: str,
        salary: int,
        years: int
    ) -> Contract:
        """Create a new contract."""
        return Contract(
            player_id=player_id,
            team_id=team_id,
            salary=salary,
            years=max(1, min(5, years)),  # 1-5 years
            buyout=salary * 2  # Buyout is 2 years salary
        )
