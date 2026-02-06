"""
Training System for Rocket League GM Simulator.
Handles practice allocation, player development, morale, and progression.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import random

from ..models.player import Player


@dataclass
class TrainingAllocation:
    """
    Training focus allocation for a team.
    Percentages must sum to 100.
    """
    mechanical: int = 34  # Default roughly equal split
    game_sense: int = 33
    mental: int = 33
    
    def __post_init__(self):
        self._normalize()
    
    def _normalize(self):
        """Ensure percentages sum to 100."""
        total = self.mechanical + self.game_sense + self.mental
        if total != 100 and total > 0:
            # Normalize
            self.mechanical = int(self.mechanical / total * 100)
            self.game_sense = int(self.game_sense / total * 100)
            self.mental = 100 - self.mechanical - self.game_sense
    
    def set_allocation(self, mechanical: int, game_sense: int, mental: int) -> bool:
        """
        Set new allocation. Returns True if valid (sums to 100).
        """
        if mechanical + game_sense + mental != 100:
            return False
        if any(x < 0 or x > 100 for x in [mechanical, game_sense, mental]):
            return False
        
        self.mechanical = mechanical
        self.game_sense = game_sense
        self.mental = mental
        return True
    
    def reset_to_default(self):
        """Reset to equal split."""
        self.mechanical = 34
        self.game_sense = 33
        self.mental = 33
    
    def to_dict(self) -> dict:
        return {
            'mechanical': self.mechanical,
            'game_sense': self.game_sense,
            'mental': self.mental
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TrainingAllocation':
        return cls(
            mechanical=data.get('mechanical', 34),
            game_sense=data.get('game_sense', 33),
            mental=data.get('mental', 33)
        )
    
    def __str__(self):
        return f"Mechanical: {self.mechanical}% | Game Sense: {self.game_sense}% | Mental: {self.mental}%"


# Mapping of training categories to player attributes
TRAINING_ATTRIBUTE_MAP = {
    'mechanical': [
        'aerial', 'ground_control', 'shooting', 
        'advanced_mechanics', 'recovery', 'car_control'
    ],
    'game_sense': [
        'positioning', 'game_reading', 'decision_making',
        'passing', 'boost_management'
    ],
    'mental': [
        'speed', 'consistency', 'clutch', 
        'mental', 'teamwork'
    ]
}

# Additional attributes that get minor training from multiple categories
CROSS_TRAINING = {
    'saving': ['mechanical', 'game_sense'],
    'challenging': ['mechanical', 'game_sense'],
    'finishing': ['mechanical', 'mental'],
    'creativity': ['game_sense', 'mental']
}


class MoraleManager:
    """
    Manages player morale based on various factors.
    Morale affects training effectiveness and match performance.
    """
    
    # Morale thresholds
    VERY_LOW = 30
    LOW = 45
    NEUTRAL = 55
    HIGH = 70
    VERY_HIGH = 85
    
    @staticmethod
    def get_morale_description(morale: int) -> str:
        """Get text description of morale level."""
        if morale >= MoraleManager.VERY_HIGH:
            return "Ecstatic"
        elif morale >= MoraleManager.HIGH:
            return "Happy"
        elif morale >= MoraleManager.NEUTRAL:
            return "Content"
        elif morale >= MoraleManager.LOW:
            return "Unhappy"
        else:
            return "Miserable"
    
    @staticmethod
    def get_training_modifier(morale: int) -> float:
        """
        Get training effectiveness modifier based on morale.
        High morale = better training, low morale = worse training.
        """
        if morale >= MoraleManager.VERY_HIGH:
            return 1.3
        elif morale >= MoraleManager.HIGH:
            return 1.15
        elif morale >= MoraleManager.NEUTRAL:
            return 1.0
        elif morale >= MoraleManager.LOW:
            return 0.85
        else:
            return 0.6
    
    @staticmethod
    def get_match_modifier(morale: int) -> float:
        """
        Get match performance modifier based on morale.
        """
        if morale >= MoraleManager.VERY_HIGH:
            return 1.1
        elif morale >= MoraleManager.HIGH:
            return 1.05
        elif morale >= MoraleManager.NEUTRAL:
            return 1.0
        elif morale >= MoraleManager.LOW:
            return 0.95
        else:
            return 0.85
    
    @staticmethod
    def update_morale_after_match(
        player: Player,
        won: bool,
        was_starter: bool,
        team_chemistry: int,
        goals_scored: int = 0,
        was_mvp: bool = False
    ) -> int:
        """
        Update player morale after a match.
        Returns the morale change.
        """
        change = 0
        
        # Win/Loss impact
        if won:
            change += 3 if was_starter else 1
        else:
            change -= 4 if was_starter else -1
        
        # Not playing hurts morale
        if not was_starter:
            change -= 2
        
        # Personal performance
        if goals_scored >= 2:
            change += 3
        elif goals_scored == 1:
            change += 1
        
        if was_mvp:
            change += 5
        
        # Team chemistry affects morale stability
        if team_chemistry > 70:
            if change < 0:
                change = int(change * 0.7)  # Less negative impact
        elif team_chemistry < 40:
            if change < 0:
                change = int(change * 1.3)  # More negative impact
        
        # Player's mental attribute affects morale swings
        mental_factor = player.attributes.mental / 100
        if change < 0:
            change = int(change * (1.5 - mental_factor))  # High mental = less morale loss
        
        # Apply change with bounds
        old_morale = player.morale
        player.morale = max(10, min(100, player.morale + change))
        
        return player.morale - old_morale
    
    @staticmethod
    def weekly_morale_drift(player: Player, team_chemistry: int, is_starter: bool) -> int:
        """
        Weekly morale drift towards equilibrium.
        Players drift towards ~60-70 morale over time.
        """
        target = 65
        
        # Starters are happier
        if is_starter:
            target += 5
        else:
            target -= 10
        
        # Team chemistry affects baseline
        target += (team_chemistry - 50) // 5
        
        # Drift towards target
        if player.morale < target:
            change = min(3, target - player.morale)
        else:
            change = max(-2, target - player.morale)
        
        old_morale = player.morale
        player.morale = max(10, min(100, player.morale + change))
        
        return player.morale - old_morale


class TrainingManager:
    """
    Manages training sessions and player development.
    Training is now player-initiated (not automatic).
    """
    
    def __init__(self):
        # Base improvement chances
        self.base_improvement_chance = 0.18  # 18% base chance per attribute
        self.max_weekly_improvements = 3     # Max attributes that can improve per player per week
        
        # Track if training was done this week
        self.trained_this_week: Dict[str, bool] = {}
    
    def can_train(self, team_id: str) -> bool:
        """Check if team can train this week."""
        return not self.trained_this_week.get(team_id, False)
    
    def reset_weekly_training(self):
        """Reset training flags for new week."""
        self.trained_this_week = {}
    
    def process_weekly_training(
        self,
        players: List[Player],
        allocation: TrainingAllocation,
        team_chemistry: int = 50,
        mark_trained: bool = True,
        team_id: str = None
    ) -> Dict[str, List[dict]]:
        """
        Process weekly training for a list of players.
        Returns dict of player_id -> list of improvements.
        """
        if team_id and mark_trained:
            self.trained_this_week[team_id] = True
        
        results = {}
        
        for player in players:
            improvements = self._train_player(player, allocation, team_chemistry)
            if improvements:
                results[player.id] = improvements
        
        return results
    
    def _train_player(
        self,
        player: Player,
        allocation: TrainingAllocation,
        team_chemistry: int
    ) -> List[dict]:
        """
        Process training for a single player.
        Returns list of attribute improvements.
        """
        improvements = []
        
        # Can't improve past potential
        room_to_grow = player.hidden.potential - player.overall
        if room_to_grow <= 0:
            return improvements
        
        # Calculate training effectiveness
        age_factor = self._get_age_factor(player.age)
        ambition_factor = player.hidden.ambition / 50  # 0.0 to 2.0
        chemistry_factor = 0.8 + (team_chemistry / 250)  # 0.8 to 1.2
        morale_factor = MoraleManager.get_training_modifier(player.morale)
        potential_factor = min(1.0, room_to_grow / 20)
        
        # Combined effectiveness
        effectiveness = (
            self.base_improvement_chance * 
            age_factor * 
            ambition_factor * 
            chemistry_factor * 
            morale_factor *
            potential_factor
        )
        
        # Process each training category
        improvements_count = 0
        
        for category, percentage in [
            ('mechanical', allocation.mechanical),
            ('game_sense', allocation.game_sense),
            ('mental', allocation.mental)
        ]:
            if percentage == 0:
                continue
            
            intensity = percentage / 100
            attrs = TRAINING_ATTRIBUTE_MAP.get(category, [])
            
            for attr in attrs:
                if improvements_count >= self.max_weekly_improvements:
                    break
                
                chance = effectiveness * intensity
                if random.random() < chance:
                    current_val = getattr(player.attributes, attr)
                    
                    if current_val >= player.hidden.potential:
                        continue
                    
                    improvement = 1 if random.random() > 0.1 else 2
                    new_val = min(99, min(player.hidden.potential, current_val + improvement))
                    
                    if new_val > current_val:
                        setattr(player.attributes, attr, new_val)
                        improvements.append({
                            'attribute': attr,
                            'category': category,
                            'old_value': current_val,
                            'new_value': new_val,
                            'change': new_val - current_val
                        })
                        improvements_count += 1
        
        # Cross-training (lower chance)
        if improvements_count < self.max_weekly_improvements:
            for attr, categories in CROSS_TRAINING.items():
                if improvements_count >= self.max_weekly_improvements:
                    break
                
                related_allocation = sum(
                    getattr(allocation, cat) for cat in categories
                ) / len(categories) / 100
                
                chance = effectiveness * related_allocation * 0.5
                
                if random.random() < chance:
                    current_val = getattr(player.attributes, attr)
                    
                    if current_val >= player.hidden.potential:
                        continue
                    
                    improvement = 1
                    new_val = min(99, min(player.hidden.potential, current_val + improvement))
                    
                    if new_val > current_val:
                        setattr(player.attributes, attr, new_val)
                        improvements.append({
                            'attribute': attr,
                            'category': 'cross-training',
                            'old_value': current_val,
                            'new_value': new_val,
                            'change': new_val - current_val
                        })
                        improvements_count += 1
        
        return improvements
    
    def _get_age_factor(self, age: int) -> float:
        """Training effectiveness multiplier based on age."""
        if age < 17:
            return 1.5
        elif age < 19:
            return 1.3
        elif age < 21:
            return 1.1
        elif age < 23:
            return 1.0
        elif age < 25:
            return 0.7
        elif age < 27:
            return 0.4
        else:
            return 0.2
    
    def process_split_break_training(
        self,
        players: List[Player],
        allocation: TrainingAllocation,
        team_chemistry: int = 50,
        sessions: int = 4
    ) -> Dict[str, List[dict]]:
        """
        Process intensive training during split break.
        Multiple training sessions with boosted effectiveness.
        """
        all_results = {}
        
        original_chance = self.base_improvement_chance
        original_max = self.max_weekly_improvements
        
        self.base_improvement_chance = 0.25
        self.max_weekly_improvements = 5
        
        for _ in range(sessions):
            results = self.process_weekly_training(
                players, allocation, team_chemistry, 
                mark_trained=False
            )
            
            for player_id, improvements in results.items():
                if player_id not in all_results:
                    all_results[player_id] = []
                all_results[player_id].extend(improvements)
        
        self.base_improvement_chance = original_chance
        self.max_weekly_improvements = original_max
        
        return all_results
    
    def calculate_chemistry_boost(
        self,
        current_roster: List[str],
        previous_roster: List[str],
        current_chemistry: int
    ) -> Tuple[int, str]:
        """Calculate chemistry boost based on roster stability."""
        if not previous_roster:
            return current_chemistry, "New team - no chemistry bonus"
        
        retained = len(set(current_roster) & set(previous_roster))
        total_previous = len(previous_roster)
        
        retention_rate = retained / total_previous if total_previous > 0 else 0
        
        if retention_rate >= 1.0:
            boost = 15
            desc = "Full roster retained! Major chemistry boost"
        elif retention_rate >= 0.67:
            boost = 10
            desc = "Core roster intact - strong chemistry boost"
        elif retention_rate >= 0.5:
            boost = 5
            desc = "Roster changes - minor chemistry boost"
        elif retention_rate >= 0.33:
            boost = 0
            desc = "Major roster changes - chemistry maintained"
        else:
            boost = -10
            desc = "Near-complete roster overhaul - chemistry reset"
        
        new_chemistry = max(0, min(100, current_chemistry + boost))
        
        return new_chemistry, desc


class ProgressionManager:
    """
    Manages player progression at split breaks and season end.
    Players can upgrade or regress based on morale, age, performance, and RNG.
    """
    
    @staticmethod
    def apply_natural_regression(player: Player) -> Dict[str, int]:
        """
        Apply small natural regression after each split.
        Teams get "figured out" and rust sets in without playing.
        Returns dict of {attribute: change}.
        """
        changes = {}
        
        # All players lose a tiny bit to represent meta shifts and rust
        # Younger players lose less, older players lose more
        if player.age < 20:
            regression_chance = 0.15  # 15% per attribute
            max_loss = 1
        elif player.age < 24:
            regression_chance = 0.20
            max_loss = 1
        elif player.age < 27:
            regression_chance = 0.25
            max_loss = 2
        else:
            regression_chance = 0.35
            max_loss = 2
        
        # Pick 3-5 random attributes to potentially regress
        attr_names = list(player.attributes.to_dict().keys())
        num_checks = random.randint(3, 5)
        
        for _ in range(num_checks):
            if random.random() < regression_chance:
                attr = random.choice(attr_names)
                current = getattr(player.attributes, attr)
                decrease = random.randint(1, max_loss)
                new_val = max(1, current - decrease)
                if new_val < current:
                    setattr(player.attributes, attr, new_val)
                    changes[attr] = changes.get(attr, 0) - (current - new_val)
        
        return changes
    
    @staticmethod
    def process_split_progression(
        player: Player, 
        team_wins: int = 0, 
        team_losses: int = 0
    ) -> Dict[str, int]:
        """
        Process player progression at split break.
        Factors in performance (team record), morale, age, and more RNG.
        Returns dict of {attribute: change}.
        """
        changes = {}
        
        # Calculate performance factor from team record
        total_games = team_wins + team_losses
        if total_games > 0:
            win_rate = team_wins / total_games
            # Performance factor: 0.5 (bad team) to 1.5 (great team)
            performance_factor = 0.5 + win_rate
        else:
            performance_factor = 1.0
        
        # Base progression chances - INCREASED for more variance
        if player.age < 20:
            base_improve_chance = 0.55  # Young prospects
            base_regress_chance = 0.05
            improve_amount_range = (2, 5)  # Bigger gains
        elif player.age < 23:
            base_improve_chance = 0.45
            base_regress_chance = 0.08
            improve_amount_range = (1, 4)
        elif player.age < 26:
            base_improve_chance = 0.30
            base_regress_chance = 0.20
            improve_amount_range = (1, 3)
        else:
            base_improve_chance = 0.15
            base_regress_chance = 0.40
            improve_amount_range = (1, 2)
        
        # Morale modifiers (bigger impact)
        morale_factor = (player.morale / 60) ** 1.2  # More exponential effect
        improve_chance = base_improve_chance * morale_factor * performance_factor
        regress_chance = base_regress_chance * (1.5 / max(morale_factor, 0.5))
        
        # Room to grow affects improvement chance
        room_to_grow = player.hidden.potential - player.overall
        if room_to_grow <= 0:
            improve_chance = 0
        elif room_to_grow < 5:
            improve_chance *= 0.3
        elif room_to_grow < 10:
            improve_chance *= 0.6
        
        # Ambition affects improvement
        improve_chance *= (player.hidden.ambition / 45)  # Slightly more impact
        
        # Add some pure RNG variance (lucky/unlucky splits)
        rng_factor = random.uniform(0.7, 1.4)
        improve_chance *= rng_factor
        
        # Get all attribute names
        attr_names = list(player.attributes.to_dict().keys())
        
        # Try to improve MORE attributes (3-7 for more variance)
        num_improve_attempts = random.randint(3, 7)
        for _ in range(num_improve_attempts):
            if random.random() < improve_chance:
                attr = random.choice(attr_names)
                current = getattr(player.attributes, attr)
                
                if current < player.hidden.potential:
                    improvement = random.randint(*improve_amount_range)
                    new_val = min(99, min(player.hidden.potential, current + improvement))
                    if new_val > current:
                        setattr(player.attributes, attr, new_val)
                        changes[attr] = changes.get(attr, 0) + (new_val - current)
        
        # Regression for older players or low morale
        mechanical_attrs = ['aerial', 'ground_control', 'shooting', 
                           'advanced_mechanics', 'recovery', 'car_control', 'speed']
        
        # More regression attempts based on age
        num_regress_attempts = 1
        if player.age >= 27:
            num_regress_attempts = 3
        elif player.age >= 25:
            num_regress_attempts = 2
        
        for _ in range(num_regress_attempts):
            if random.random() < regress_chance:
                attr = random.choice(mechanical_attrs)
                current = getattr(player.attributes, attr)
                decrease = random.randint(1, 3)
                new_val = max(1, current - decrease)
                if new_val < current:
                    setattr(player.attributes, attr, new_val)
                    changes[attr] = changes.get(attr, 0) - (current - new_val)
        
        return changes
    
    @staticmethod
    def process_season_end_progression(
        player: Player,
        team_wins: int = 0,
        team_losses: int = 0
    ) -> Dict[str, int]:
        """
        Process player progression at season end.
        Bigger changes than split breaks with more variance.
        """
        changes = {}
        
        # Calculate performance factor
        total_games = team_wins + team_losses
        if total_games > 0:
            win_rate = team_wins / total_games
            performance_factor = 0.5 + win_rate
        else:
            performance_factor = 1.0
        
        # Base chances - HIGHER for end of season
        if player.age < 20:
            base_improve_chance = 0.65
            base_regress_chance = 0.05
            improve_amount_range = (3, 6)
        elif player.age < 23:
            base_improve_chance = 0.55
            base_regress_chance = 0.10
            improve_amount_range = (2, 5)
        elif player.age < 26:
            base_improve_chance = 0.35
            base_regress_chance = 0.25
            improve_amount_range = (1, 4)
        else:
            base_improve_chance = 0.15
            base_regress_chance = 0.45
            improve_amount_range = (1, 2)
        
        # Morale modifiers
        morale_factor = (player.morale / 60) ** 1.2
        improve_chance = base_improve_chance * morale_factor * performance_factor
        regress_chance = base_regress_chance * (1.5 / max(morale_factor, 0.5))
        
        # Room to grow
        room_to_grow = player.hidden.potential - player.overall
        if room_to_grow <= 0:
            improve_chance = 0
        elif room_to_grow < 5:
            improve_chance *= 0.3
        elif room_to_grow < 10:
            improve_chance *= 0.6
        
        # Ambition
        improve_chance *= (player.hidden.ambition / 45)
        
        # RNG variance
        rng_factor = random.uniform(0.6, 1.5)
        improve_chance *= rng_factor
        
        attr_names = list(player.attributes.to_dict().keys())
        
        # Try to improve 5-10 attributes for big offseason gains
        num_improve_attempts = random.randint(5, 10)
        for _ in range(num_improve_attempts):
            if random.random() < improve_chance:
                attr = random.choice(attr_names)
                current = getattr(player.attributes, attr)
                
                if current < player.hidden.potential:
                    improvement = random.randint(*improve_amount_range)
                    new_val = min(99, min(player.hidden.potential, current + improvement))
                    if new_val > current:
                        setattr(player.attributes, attr, new_val)
                        changes[attr] = changes.get(attr, 0) + (new_val - current)
        
        # Regression
        mechanical_attrs = ['aerial', 'ground_control', 'shooting', 
                           'advanced_mechanics', 'recovery', 'car_control', 'speed']
        
        num_regress_attempts = 1
        if player.age >= 28:
            num_regress_attempts = 4
        elif player.age >= 26:
            num_regress_attempts = 3
        elif player.age >= 24:
            num_regress_attempts = 2
        
        for _ in range(num_regress_attempts):
            if random.random() < regress_chance:
                attr = random.choice(mechanical_attrs)
                current = getattr(player.attributes, attr)
                decrease = random.randint(1, 4)
                new_val = max(1, current - decrease)
                if new_val < current:
                    setattr(player.attributes, attr, new_val)
                    changes[attr] = changes.get(attr, 0) - (current - new_val)
        
        return changes


class ChemistryManager:
    """
    Manages team chemistry based on performance and morale.
    """
    
    @staticmethod
    def update_chemistry_after_match(
        team_chemistry: int,
        won: bool,
        avg_morale: float,
        streak: int  # Positive = win streak, negative = lose streak
    ) -> Tuple[int, int]:
        """
        Update chemistry after a match.
        Returns (new_chemistry, change).
        """
        base_change = 0
        
        # Win/loss impact
        if won:
            base_change = 2
            if streak >= 3:  # Win streak bonus
                base_change += 1
            if streak >= 5:
                base_change += 1
        else:
            base_change = -3
            if streak <= -3:  # Lose streak penalty
                base_change -= 1
            if streak <= -5:
                base_change -= 2
        
        # Morale modifier
        morale_modifier = avg_morale / 70  # Around 1.0 at 70 morale
        
        if base_change > 0:
            # High morale accelerates chemistry gains
            base_change = int(base_change * morale_modifier)
        else:
            # Low morale makes losses hurt more
            base_change = int(base_change * (2 - morale_modifier))
        
        # Apply bounds
        new_chemistry = max(10, min(100, team_chemistry + base_change))
        actual_change = new_chemistry - team_chemistry
        
        return new_chemistry, actual_change
    
    @staticmethod
    def weekly_chemistry_drift(team_chemistry: int, avg_morale: float) -> Tuple[int, int]:
        """
        Weekly chemistry drift.
        Chemistry slowly drifts based on average team morale.
        """
        target = 50 + (avg_morale - 50) // 3  # 50-70 target based on morale
        
        if team_chemistry < target:
            change = min(2, target - team_chemistry)
        else:
            change = max(-1, target - team_chemistry)
        
        new_chemistry = max(10, min(100, team_chemistry + change))
        actual_change = new_chemistry - team_chemistry
        
        return new_chemistry, actual_change


# Preset training allocations
TRAINING_PRESETS = {
    'balanced': TrainingAllocation(34, 33, 33),
    'mechanical_focus': TrainingAllocation(60, 25, 15),
    'game_sense_focus': TrainingAllocation(25, 55, 20),
    'mental_focus': TrainingAllocation(20, 30, 50),
    'offensive': TrainingAllocation(50, 35, 15),
    'defensive': TrainingAllocation(30, 50, 20),
    'clutch': TrainingAllocation(25, 25, 50),
}


def get_preset(name: str) -> Optional[TrainingAllocation]:
    """Get a training preset by name."""
    preset = TRAINING_PRESETS.get(name.lower())
    if preset:
        return TrainingAllocation(preset.mechanical, preset.game_sense, preset.mental)
    return None


def list_presets() -> List[Tuple[str, TrainingAllocation]]:
    """List all available presets."""
    return [(name, alloc) for name, alloc in TRAINING_PRESETS.items()]
