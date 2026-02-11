"""
Tournament formats for Rocket League GM Simulator.
Implements Swiss bracket and Double Elimination systems.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum
import random

from .match_engine import MatchEngine, SeriesResult


class SwissRecord:
    """Tracks a team's record in a Swiss bracket."""
    def __init__(self, team_id: str):
        self.team_id = team_id
        self.wins = 0
        self.losses = 0
        self.game_wins = 0
        self.game_losses = 0
        self.opponents: Set[str] = set()  # Teams already played
        self.buchholz = 0  # Tiebreaker: sum of opponents' wins
    
    @property
    def record_str(self) -> str:
        return f"{self.wins}-{self.losses}"
    
    @property
    def game_diff(self) -> int:
        return self.game_wins - self.game_losses
    
    def __repr__(self):
        return f"SwissRecord({self.team_id}: {self.record_str})"


class SwissBracket:
    """
    Swiss-system tournament bracket.
    Teams play until they reach win_threshold wins or loss_threshold losses.
    """
    
    def __init__(
        self,
        team_ids: List[str],
        win_threshold: int = 3,
        loss_threshold: int = 3,
        best_of: int = 5
    ):
        self.team_ids = list(team_ids)
        self.win_threshold = win_threshold
        self.loss_threshold = loss_threshold
        self.best_of = best_of
        
        # Initialize records
        self.records: Dict[str, SwissRecord] = {
            tid: SwissRecord(tid) for tid in team_ids
        }
        
        # Track matches
        self.rounds: List[List[Tuple[str, str]]] = []  # List of rounds, each round is list of matchups
        self.results: List[Dict] = []  # All match results
        self.current_round = 0
        
        # Teams that have qualified or been eliminated
        self.qualified: List[str] = []
        self.eliminated: List[str] = []
        
        self.is_complete = False
    
    @property
    def active_teams(self) -> List[str]:
        """Teams still playing (not qualified or eliminated)."""
        return [
            tid for tid in self.team_ids
            if tid not in self.qualified and tid not in self.eliminated
        ]
    
    def get_standings(self) -> List[SwissRecord]:
        """Get current standings sorted by record."""
        standings = list(self.records.values())
        # Sort by: wins desc, losses asc, game diff desc, game wins desc
        standings.sort(key=lambda r: (-r.wins, r.losses, -r.game_diff, -r.game_wins))
        return standings
    
    def generate_round_matchups(self) -> List[Tuple[str, str]]:
        """
        Generate matchups for the next round using Swiss pairing rules.
        Teams are matched with similar records, avoiding rematches.
        """
        active = self.active_teams
        if len(active) < 2:
            # If only 1 team left, give them a bye (auto-win)
            if len(active) == 1:
                self._give_bye(active[0])
            return []
        
        # Group teams by record
        record_groups: Dict[str, List[str]] = {}
        for tid in active:
            record = self.records[tid].record_str
            if record not in record_groups:
                record_groups[record] = []
            record_groups[record].append(tid)
        
        # Sort records by win count descending
        sorted_records = sorted(record_groups.keys(), key=lambda r: -int(r.split('-')[0]))
        
        matchups = []
        paired = set()
        
        # Try to pair within same record group first
        for record in sorted_records:
            group = [t for t in record_groups[record] if t not in paired]
            random.shuffle(group)
            
            while len(group) >= 2:
                team1 = group.pop()
                
                # Find opponent team1 hasn't played
                opponent = None
                for t in group:
                    if t not in self.records[team1].opponents:
                        opponent = t
                        break
                
                if opponent:
                    group.remove(opponent)
                    matchups.append((team1, opponent))
                    paired.add(team1)
                    paired.add(opponent)
                else:
                    # No valid opponent in this group, push to next group
                    group.insert(0, team1)
                    break
            
            # Add leftover to next group
            if group:
                next_idx = sorted_records.index(record) + 1
                if next_idx < len(sorted_records):
                    next_record = sorted_records[next_idx]
                    record_groups[next_record].extend(group)
        
        # Handle any remaining unpaired teams (pair across records if necessary)
        unpaired = [t for t in active if t not in paired]
        random.shuffle(unpaired)
        
        while len(unpaired) >= 2:
            team1 = unpaired.pop()
            # Find any opponent not played yet
            for i, t in enumerate(unpaired):
                if t not in self.records[team1].opponents:
                    opponent = unpaired.pop(i)
                    matchups.append((team1, opponent))
                    break
            else:
                # All opponents played - allow rematch as last resort
                if unpaired:
                    opponent = unpaired.pop()
                    matchups.append((team1, opponent))
        
        # If there's 1 unpaired team, give them a bye
        if len(unpaired) == 1:
            self._give_bye(unpaired[0])
        
        self.rounds.append(matchups)
        self.current_round += 1
        return matchups
    
    def _give_bye(self, team_id: str):
        """Give a team a bye (automatic win for the round)."""
        self.records[team_id].wins += 1
        self.records[team_id].game_wins += 3  # Assume 3-0 bye win
        
        # Check for qualification
        if self.records[team_id].wins >= self.win_threshold:
            if team_id not in self.qualified:
                self.qualified.append(team_id)
        
        # Check if bracket is complete
        if len(self.active_teams) == 0:
            self.is_complete = True
    
    def record_result(
        self,
        team1_id: str,
        team2_id: str,
        team1_games: int,
        team2_games: int
    ) -> Dict:
        """
        Record a match result.
        Returns result dict with winner info.
        """
        winner_id = team1_id if team1_games > team2_games else team2_id
        loser_id = team2_id if team1_games > team2_games else team1_id
        
        # Update records
        self.records[winner_id].wins += 1
        self.records[winner_id].game_wins += max(team1_games, team2_games)
        self.records[winner_id].game_losses += min(team1_games, team2_games)
        self.records[winner_id].opponents.add(loser_id)
        
        self.records[loser_id].losses += 1
        self.records[loser_id].game_wins += min(team1_games, team2_games)
        self.records[loser_id].game_losses += max(team1_games, team2_games)
        self.records[loser_id].opponents.add(winner_id)
        
        # Check for qualification/elimination
        if self.records[winner_id].wins >= self.win_threshold:
            if winner_id not in self.qualified:
                self.qualified.append(winner_id)
        
        if self.records[loser_id].losses >= self.loss_threshold:
            if loser_id not in self.eliminated:
                self.eliminated.append(loser_id)
        
        # Check if bracket is complete
        if len(self.active_teams) == 0:
            self.is_complete = True
        
        result = {
            'team1_id': team1_id,
            'team2_id': team2_id,
            'team1_games': team1_games,
            'team2_games': team2_games,
            'winner_id': winner_id,
            'loser_id': loser_id,
            'round': self.current_round
        }
        self.results.append(result)
        return result
    
    def get_qualified_seeded(self) -> List[str]:
        """Get qualified teams seeded by final record."""
        # Sort qualified by record
        qualified_records = [self.records[tid] for tid in self.qualified]
        qualified_records.sort(key=lambda r: (-r.wins, r.losses, -r.game_diff, -r.game_wins))
        return [r.team_id for r in qualified_records]


class DoubleEliminationBracket:
    """
    Double elimination bracket for playoffs.
    Teams need to lose twice to be eliminated.
    """
    
    def __init__(self, team_ids: List[str], best_of: int = 7):
        """
        Initialize bracket with seeded teams.
        team_ids should be in seed order (1st seed first).
        """
        if len(team_ids) != 8:
            raise ValueError("Double elimination bracket requires exactly 8 teams")
        
        self.team_ids = list(team_ids)
        self.best_of = best_of
        
        # Upper bracket matches (winners bracket)
        # Round 1: 1v8, 4v5, 2v7, 3v6
        self.upper_r1 = [
            {'match_id': 'UB_R1_1', 'team1': team_ids[0], 'team2': team_ids[7], 'winner': None, 'loser': None},
            {'match_id': 'UB_R1_2', 'team1': team_ids[3], 'team2': team_ids[4], 'winner': None, 'loser': None},
            {'match_id': 'UB_R1_3', 'team1': team_ids[1], 'team2': team_ids[6], 'winner': None, 'loser': None},
            {'match_id': 'UB_R1_4', 'team1': team_ids[2], 'team2': team_ids[5], 'winner': None, 'loser': None},
        ]
        
        # Upper bracket semifinals
        self.upper_r2 = [
            {'match_id': 'UB_SF_1', 'team1': None, 'team2': None, 'winner': None, 'loser': None},  # UB_R1_1 winner vs UB_R1_2 winner
            {'match_id': 'UB_SF_2', 'team1': None, 'team2': None, 'winner': None, 'loser': None},  # UB_R1_3 winner vs UB_R1_4 winner
        ]
        
        # Upper bracket final
        self.upper_final = {'match_id': 'UB_F', 'team1': None, 'team2': None, 'winner': None, 'loser': None}
        
        # Lower bracket
        self.lower_r1 = [
            {'match_id': 'LB_R1_1', 'team1': None, 'team2': None, 'winner': None, 'loser': None},  # UB_R1_1 loser vs UB_R1_2 loser
            {'match_id': 'LB_R1_2', 'team1': None, 'team2': None, 'winner': None, 'loser': None},  # UB_R1_3 loser vs UB_R1_4 loser
        ]
        
        self.lower_r2 = [
            {'match_id': 'LB_R2_1', 'team1': None, 'team2': None, 'winner': None, 'loser': None},  # LB_R1_1 winner vs UB_SF_2 loser
            {'match_id': 'LB_R2_2', 'team1': None, 'team2': None, 'winner': None, 'loser': None},  # LB_R1_2 winner vs UB_SF_1 loser
        ]
        
        self.lower_r3 = [
            {'match_id': 'LB_SF', 'team1': None, 'team2': None, 'winner': None, 'loser': None},  # LB_R2 winners
        ]
        
        self.lower_final = {'match_id': 'LB_F', 'team1': None, 'team2': None, 'winner': None, 'loser': None}
        
        # Grand final
        self.grand_final = {'match_id': 'GF', 'team1': None, 'team2': None, 'winner': None, 'loser': None}
        self.bracket_reset = {'match_id': 'BR', 'team1': None, 'team2': None, 'winner': None, 'loser': None, 'needed': False}
        
        # Track placements
        self.placements: Dict[int, List[str]] = {}  # {place: [team_ids]}
        self.results: List[Dict] = []
        self.is_complete = False
        
        # Current round tracking
        self.current_phase = 'upper_r1'
    
    def get_next_matches(self) -> List[Dict]:
        """Get the next matches that need to be played."""
        if self.current_phase == 'upper_r1':
            return [m for m in self.upper_r1 if m['winner'] is None]
        elif self.current_phase == 'upper_r2_lower_r1':
            matches = [m for m in self.upper_r2 if m['winner'] is None]
            matches += [m for m in self.lower_r1 if m['winner'] is None]
            return matches
        elif self.current_phase == 'upper_final_lower_r2':
            matches = []
            if self.upper_final['winner'] is None and self.upper_final['team1']:
                matches.append(self.upper_final)
            matches += [m for m in self.lower_r2 if m['winner'] is None and m['team1']]
            return matches
        elif self.current_phase == 'lower_sf':
            if self.lower_r3[0]['winner'] is None and self.lower_r3[0]['team1']:
                return [self.lower_r3[0]]
            return []
        elif self.current_phase == 'lower_final':
            if self.lower_final['winner'] is None and self.lower_final['team1']:
                return [self.lower_final]
            return []
        elif self.current_phase == 'grand_final':
            if self.grand_final['winner'] is None and self.grand_final['team1']:
                return [self.grand_final]
            return []
        elif self.current_phase == 'bracket_reset':
            if self.bracket_reset['needed'] and self.bracket_reset['winner'] is None:
                return [self.bracket_reset]
            return []
        return []
    
    def record_result(self, match_id: str, winner_id: str, team1_games: int, team2_games: int) -> Dict:
        """Record a match result and advance the bracket."""
        # Find the match
        match = self._find_match(match_id)
        if not match:
            raise ValueError(f"Match {match_id} not found")
        
        loser_id = match['team2'] if winner_id == match['team1'] else match['team1']
        match['winner'] = winner_id
        match['loser'] = loser_id
        match['team1_games'] = team1_games if match['team1'] == winner_id else team2_games
        match['team2_games'] = team2_games if match['team1'] == winner_id else team1_games
        
        result = {
            'match_id': match_id,
            'team1_id': match['team1'],
            'team2_id': match['team2'],
            'winner_id': winner_id,
            'loser_id': loser_id,
            'team1_games': match['team1_games'],
            'team2_games': match['team2_games']
        }
        self.results.append(result)
        
        # Advance bracket
        self._advance_bracket(match_id, winner_id, loser_id)
        
        return result
    
    def _find_match(self, match_id: str) -> Optional[Dict]:
        """Find a match by ID."""
        all_matches = (
            self.upper_r1 + self.upper_r2 + [self.upper_final] +
            self.lower_r1 + self.lower_r2 + self.lower_r3 +
            [self.lower_final, self.grand_final, self.bracket_reset]
        )
        for m in all_matches:
            if m['match_id'] == match_id:
                return m
        return None
    
    def _advance_bracket(self, match_id: str, winner_id: str, loser_id: str):
        """Advance teams in the bracket based on match result."""
        
        # Upper R1 results
        if match_id == 'UB_R1_1':
            self.upper_r2[0]['team1'] = winner_id
            self.lower_r1[0]['team1'] = loser_id
        elif match_id == 'UB_R1_2':
            self.upper_r2[0]['team2'] = winner_id
            self.lower_r1[0]['team2'] = loser_id
        elif match_id == 'UB_R1_3':
            self.upper_r2[1]['team1'] = winner_id
            self.lower_r1[1]['team1'] = loser_id
        elif match_id == 'UB_R1_4':
            self.upper_r2[1]['team2'] = winner_id
            self.lower_r1[1]['team2'] = loser_id
        
        # Upper R2 (SF) results
        elif match_id == 'UB_SF_1':
            self.upper_final['team1'] = winner_id
            self.lower_r2[1]['team2'] = loser_id  # Drops to LB_R2_2
        elif match_id == 'UB_SF_2':
            self.upper_final['team2'] = winner_id
            self.lower_r2[0]['team2'] = loser_id  # Drops to LB_R2_1
        
        # Upper Final result
        elif match_id == 'UB_F':
            self.grand_final['team1'] = winner_id
            self.lower_final['team2'] = loser_id
        
        # Lower R1 results
        elif match_id == 'LB_R1_1':
            self.lower_r2[0]['team1'] = winner_id
            self._set_placement(loser_id, 7)  # 7th-8th
        elif match_id == 'LB_R1_2':
            self.lower_r2[1]['team1'] = winner_id
            self._set_placement(loser_id, 7)  # 7th-8th
        
        # Lower R2 results
        elif match_id == 'LB_R2_1':
            self.lower_r3[0]['team1'] = winner_id
            self._set_placement(loser_id, 5)  # 5th-6th
        elif match_id == 'LB_R2_2':
            self.lower_r3[0]['team2'] = winner_id
            self._set_placement(loser_id, 5)  # 5th-6th
        
        # Lower SF result
        elif match_id == 'LB_SF':
            self.lower_final['team1'] = winner_id
            self._set_placement(loser_id, 4)  # 4th
        
        # Lower Final result
        elif match_id == 'LB_F':
            self.grand_final['team2'] = winner_id
            self._set_placement(loser_id, 3)  # 3rd
        
        # Grand Final result
        elif match_id == 'GF':
            if winner_id == self.grand_final['team1']:
                # Upper bracket winner wins - tournament over
                self._set_placement(winner_id, 1)
                self._set_placement(loser_id, 2)
                self.is_complete = True
            else:
                # Lower bracket winner wins - bracket reset
                self.bracket_reset['needed'] = True
                self.bracket_reset['team1'] = self.grand_final['team1']
                self.bracket_reset['team2'] = winner_id
        
        # Bracket Reset result
        elif match_id == 'BR':
            self._set_placement(winner_id, 1)
            self._set_placement(loser_id, 2)
            self.is_complete = True
        
        # Update current phase
        self._update_phase()
    
    def _set_placement(self, team_id: str, place: int):
        """Record a team's final placement."""
        if place not in self.placements:
            self.placements[place] = []
        self.placements[place].append(team_id)
    
    def _update_phase(self):
        """Update the current phase based on completed matches."""
        # Check if upper R1 is complete
        if all(m['winner'] for m in self.upper_r1):
            self.current_phase = 'upper_r2_lower_r1'
        
        # Check if upper R2 and lower R1 are complete
        if (all(m['winner'] for m in self.upper_r2) and 
            all(m['winner'] for m in self.lower_r1)):
            self.current_phase = 'upper_final_lower_r2'
        
        # Check if upper final and lower R2 are complete
        if (self.upper_final['winner'] and 
            all(m['winner'] for m in self.lower_r2)):
            self.current_phase = 'lower_sf'
        
        # Check if lower SF is complete
        if self.lower_r3[0]['winner']:
            self.current_phase = 'lower_final'
        
        # Check if lower final is complete
        if self.lower_final['winner']:
            self.current_phase = 'grand_final'
        
        # Check if grand final decided
        if self.grand_final['winner'] and self.bracket_reset['needed']:
            self.current_phase = 'bracket_reset'
    
    def get_placements(self) -> Dict[int, List[str]]:
        """Get final placements for all teams."""
        return self.placements


# Points for regional placements
REGIONAL_POINTS = {
    1: 15,
    2: 11,
    3: 9,
    4: 7,
    5: 5,  # 5th-6th
    6: 5,
    7: 4,  # 7th-8th
    8: 4,
    9: 3,  # 9th-11th
    10: 3,
    11: 3,
    12: 2,  # 12th-14th
    13: 2,
    14: 2,
    15: 1,  # 15th-16th
    16: 1,
}


@dataclass
class RegionalTournament:
    """
    Full RLCS Regional tournament format.
    - 32 teams split into two 16-team Swiss groups
    - Top 8 from each group advance to 16-team Swiss
    - Top 8 from that advance to Double Elimination playoffs
    """
    
    teams: List[str]  # All 32 team IDs
    name: str = "Regional"
    
    # Tournament stages
    swiss_group_a: Optional[SwissBracket] = None
    swiss_group_b: Optional[SwissBracket] = None
    swiss_playoffs: Optional[SwissBracket] = None
    double_elim: Optional[DoubleEliminationBracket] = None
    
    # State tracking
    current_stage: str = "swiss_groups"  # swiss_groups, swiss_playoffs, double_elim, complete
    
    # Results
    final_placements: Dict[str, int] = field(default_factory=dict)  # team_id -> placement
    points_earned: Dict[str, int] = field(default_factory=dict)  # team_id -> points
    
    def __post_init__(self):
        if len(self.teams) != 32:
            raise ValueError(f"Regional requires 32 teams, got {len(self.teams)}")
        
        # Shuffle and split into two groups
        shuffled = list(self.teams)
        random.shuffle(shuffled)
        
        group_a = shuffled[:16]
        group_b = shuffled[16:]
        
        self.swiss_group_a = SwissBracket(group_a, win_threshold=3, loss_threshold=3, best_of=5)
        self.swiss_group_b = SwissBracket(group_b, win_threshold=3, loss_threshold=3, best_of=5)
    
    def get_current_stage_name(self) -> str:
        """Get human-readable stage name."""
        stage_names = {
            'swiss_groups': 'Swiss Stage - Groups',
            'swiss_playoffs': 'Swiss Stage - Playoffs',
            'double_elim': 'Playoff Bracket',
            'complete': 'Complete'
        }
        return stage_names.get(self.current_stage, self.current_stage)
    
    def advance_stage(self):
        """Advance to the next tournament stage."""
        if self.current_stage == 'swiss_groups':
            # Check if both groups are complete
            if self.swiss_group_a.is_complete and self.swiss_group_b.is_complete:
                # Record 17th-32nd placements (eliminated in groups - 0 points)
                for tid in self.swiss_group_a.eliminated + self.swiss_group_b.eliminated:
                    # These teams get placed 17-32 (no points)
                    place = 17 + len([t for t in self.final_placements if self.final_placements[t] >= 17])
                    self.final_placements[tid] = min(place, 32)
                    self.points_earned[tid] = 0
                
                # Get qualified teams from both groups
                qualified_a = self.swiss_group_a.get_qualified_seeded()
                qualified_b = self.swiss_group_b.get_qualified_seeded()
                
                # Combine for playoffs Swiss (interleave by seed)
                playoff_teams = []
                for i in range(8):
                    if i < len(qualified_a):
                        playoff_teams.append(qualified_a[i])
                    if i < len(qualified_b):
                        playoff_teams.append(qualified_b[i])
                
                self.swiss_playoffs = SwissBracket(playoff_teams, win_threshold=3, loss_threshold=3, best_of=5)
                self.current_stage = 'swiss_playoffs'
        
        elif self.current_stage == 'swiss_playoffs':
            if self.swiss_playoffs.is_complete:
                # Record 9th-16th placements
                eliminated = self.swiss_playoffs.eliminated
                for i, tid in enumerate(eliminated):
                    place = 16 - i  # 16th, 15th, 14th, etc.
                    self.final_placements[tid] = place
                    self.points_earned[tid] = REGIONAL_POINTS.get(place, 0)
                
                # Get top 8 for double elim
                qualified = self.swiss_playoffs.get_qualified_seeded()
                self.double_elim = DoubleEliminationBracket(qualified, best_of=7)
                self.current_stage = 'double_elim'
        
        elif self.current_stage == 'double_elim':
            if self.double_elim.is_complete:
                # Record 1st-8th placements
                for place, team_ids in self.double_elim.get_placements().items():
                    for tid in team_ids:
                        self.final_placements[tid] = place
                        self.points_earned[tid] = REGIONAL_POINTS.get(place, 0)
                
                self.current_stage = 'complete'
    
    def is_complete(self) -> bool:
        return self.current_stage == 'complete'
    
    def get_standings_summary(self) -> List[Dict]:
        """Get current standings/results summary."""
        standings = []
        for tid, place in sorted(self.final_placements.items(), key=lambda x: x[1]):
            standings.append({
                'team_id': tid,
                'placement': place,
                'points': self.points_earned.get(tid, 0)
            })
        return standings
