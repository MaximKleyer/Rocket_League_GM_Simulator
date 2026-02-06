"""
Training System for Rocket League GM Simulator.
Handles practice allocation and skill development.
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
    'saving': ['mechanical', 'game_sense'],      # Mechanics + positioning
    'challenging': ['mechanical', 'game_sense'], # Mechanics + decision making
    'finishing': ['mechanical', 'mental'],       # Mechanics + clutch
    'creativity': ['game_sense', 'mental']       # Vision + confidence
}


class TrainingManager:
    """
    Manages training sessions and player development.
    """
    
    def __init__(self):
        # Base improvement chances
        self.base_improvement_chance = 0.15  # 15% base chance per attribute
        self.max_weekly_improvements = 3     # Max attributes that can improve per player per week
        
        # Training quality factors
        self.team_facilities_bonus = 1.0     # Could be upgraded in future
    
    def process_weekly_training(
        self,
        players: List[Player],
        allocation: TrainingAllocation,
        team_chemistry: int = 50
    ) -> Dict[str, List[dict]]:
        """
        Process weekly training for a list of players.
        Returns dict of player_id -> list of improvements.
        """
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
        
        # Calculate training effectiveness based on player factors
        age_factor = self._get_age_factor(player.age)
        ambition_factor = player.hidden.ambition / 50  # 0.0 to 2.0
        chemistry_factor = 0.8 + (team_chemistry / 250)  # 0.8 to 1.2
        
        # Can't improve past potential
        room_to_grow = player.hidden.potential - player.overall
        if room_to_grow <= 0:
            return improvements
        
        # Reduced training effectiveness near potential cap
        potential_factor = min(1.0, room_to_grow / 20)
        
        # Combined effectiveness
        effectiveness = (
            self.base_improvement_chance * 
            age_factor * 
            ambition_factor * 
            chemistry_factor * 
            potential_factor *
            self.team_facilities_bonus
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
            
            # Training intensity from allocation
            intensity = percentage / 100
            
            # Get attributes for this category
            attrs = TRAINING_ATTRIBUTE_MAP.get(category, [])
            
            for attr in attrs:
                if improvements_count >= self.max_weekly_improvements:
                    break
                
                # Check if this attribute improves
                chance = effectiveness * intensity
                if random.random() < chance:
                    current_val = getattr(player.attributes, attr)
                    
                    # Can't exceed potential
                    if current_val >= player.hidden.potential:
                        continue
                    
                    # Improvement amount (usually 1, rarely 2)
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
        
        # Process cross-training attributes (lower chance)
        if improvements_count < self.max_weekly_improvements:
            for attr, categories in CROSS_TRAINING.items():
                if improvements_count >= self.max_weekly_improvements:
                    break
                
                # Average allocation of related categories
                related_allocation = sum(
                    getattr(allocation, cat) for cat in categories
                ) / len(categories) / 100
                
                chance = effectiveness * related_allocation * 0.5  # Half effectiveness
                
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
        """
        Get training effectiveness multiplier based on age.
        Young players improve faster.
        """
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
        
        # Temporarily boost training effectiveness
        original_chance = self.base_improvement_chance
        original_max = self.max_weekly_improvements
        
        self.base_improvement_chance = 0.25  # 25% during break
        self.max_weekly_improvements = 5     # More improvements possible
        
        for _ in range(sessions):
            results = self.process_weekly_training(players, allocation, team_chemistry)
            
            # Merge results
            for player_id, improvements in results.items():
                if player_id not in all_results:
                    all_results[player_id] = []
                all_results[player_id].extend(improvements)
        
        # Restore normal values
        self.base_improvement_chance = original_chance
        self.max_weekly_improvements = original_max
        
        return all_results
    
    def calculate_chemistry_boost(
        self,
        current_roster: List[str],
        previous_roster: List[str],
        current_chemistry: int
    ) -> Tuple[int, str]:
        """
        Calculate chemistry boost based on roster stability.
        Returns (new_chemistry, description).
        """
        if not previous_roster:
            return current_chemistry, "New team - no chemistry bonus"
        
        # Count players who stayed
        retained = len(set(current_roster) & set(previous_roster))
        total_previous = len(previous_roster)
        
        retention_rate = retained / total_previous if total_previous > 0 else 0
        
        if retention_rate >= 1.0:
            # Full roster retained
            boost = 15
            desc = "Full roster retained! Major chemistry boost"
        elif retention_rate >= 0.67:
            # 2/3+ retained
            boost = 10
            desc = "Core roster intact - strong chemistry boost"
        elif retention_rate >= 0.5:
            # Half retained
            boost = 5
            desc = "Roster changes - minor chemistry boost"
        elif retention_rate >= 0.33:
            # 1/3 retained
            boost = 0
            desc = "Major roster changes - chemistry maintained"
        else:
            # Almost entirely new roster
            boost = -10
            desc = "Near-complete roster overhaul - chemistry reset"
        
        new_chemistry = max(0, min(100, current_chemistry + boost))
        
        return new_chemistry, desc


# Preset training allocations for quick selection
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
        # Return a copy
        return TrainingAllocation(preset.mechanical, preset.game_sense, preset.mental)
    return None


def list_presets() -> List[Tuple[str, TrainingAllocation]]:
    """List all available presets."""
    return [(name, alloc) for name, alloc in TRAINING_PRESETS.items()]