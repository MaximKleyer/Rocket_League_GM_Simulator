#!/usr/bin/env python3
"""
Rocket League GM Simulator - CLI Interface
A text-based interface for testing and playing the game.
"""

import os
import sys

# Add the package to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.game import Game
from core.simulation.season import SeasonPhase, REGIONAL_PHASES


def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_subheader(text: str):
    """Print a formatted subheader."""
    print(f"\n--- {text} ---")


def format_money(amount: int) -> str:
    """Format money with commas."""
    return f"${amount:,}"


class CLI:
    """Command-line interface for the game."""
    
    def __init__(self):
        self.game: Game = None
        self.running = True
    
    def run(self):
        """Main game loop."""
        clear_screen()
        print_header("ROCKET LEAGUE GM SIMULATOR")
        print("\nWelcome to the Rocket League GM Simulator!")
        print("Manage your esports team to championship glory.\n")
        
        self.main_menu()
        
        while self.running:
            if self.game:
                self.game_menu()
            else:
                self.main_menu()
    
    def main_menu(self):
        """Display main menu."""
        print_subheader("MAIN MENU")
        print("1. New Game")
        print("2. Load Game")
        print("3. Quit")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == "1":
            self.new_game()
        elif choice == "2":
            self.load_game()
        elif choice == "3":
            self.running = False
            print("\nThanks for playing!")
        else:
            print("Invalid option.")
    
    def new_game(self):
        """Start a new game."""
        clear_screen()
        print_header("NEW GAME")
        
        team_name = input("Enter your team name: ").strip() or "My Team"
        team_abbrev = input("Enter team abbreviation (3-4 letters): ").strip().upper() or "MYT"
        team_abbrev = team_abbrev[:4]
        
        print("\nCreating new game...")
        
        self.game = Game()
        self.game.new_game(team_name, team_abbrev, region="NA")
        
        print(f"\n✓ Created team: {team_name} ({team_abbrev})")
        print(f"✓ Joined RLCS North America ({len(self.game.teams)} teams)")
        print(f"✓ Season {self.game.season_number} is ready to begin!")
        
        input("\nPress Enter to continue...")
    
    def load_game(self):
        """Load an existing game."""
        clear_screen()
        print_header("LOAD GAME")
        
        saves = Game.list_saves()
        
        if not saves:
            print("No save files found.")
            input("\nPress Enter to continue...")
            return
        
        print("\nAvailable saves:")
        for i, save in enumerate(saves, 1):
            print(f"  {i}. {save['save_name']} (Season {save.get('season', '?')})")
            print(f"      Last played: {save.get('last_played', 'Unknown')[:10]}")
        
        choice = input("\nSelect save number (or 0 to cancel): ").strip()
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(saves):
                self.game = Game.load_game(saves[idx]['filepath'])
                print(f"\n✓ Loaded: {self.game.save_name}")
                input("\nPress Enter to continue...")
            elif idx == -1:
                return
        except (ValueError, IndexError):
            print("Invalid selection.")
            input("\nPress Enter to continue...")
    
    def game_menu(self):
        """Display in-game menu."""
        clear_screen()
        
        team = self.game.player_team
        
        # Format phase name nicely
        phase_name = self.game.current_phase.value.replace('_', ' ').title()
        if 'Split1' in phase_name:
            phase_name = phase_name.replace('Split1 ', 'Split 1 - ')
        elif 'Split2' in phase_name:
            phase_name = phase_name.replace('Split2 ', 'Split 2 - ')
        
        # Streak display
        if team.streak > 0:
            streak_str = f"🔥 {team.streak}W"
        elif team.streak < 0:
            streak_str = f"❄️ {abs(team.streak)}L"
        else:
            streak_str = "—"
        
        # Training status
        train_status = "✓" if self.game.can_train() else "✗"
        
        print_header(f"{team.name} ({team.abbreviation})")
        print(f"Season {self.game.season_number} | {phase_name} | Week {self.game.current_week}")
        print(f"Record: {team.season_stats.series_record} | Streak: {streak_str} | Chem: {team.chemistry}/100")
        print(f"Balance: {format_money(team.finances.balance)} | Training: {train_status}")
        
        print_subheader("MENU")
        print("1. View Roster")
        print("2. View Standings")
        print("3. View Schedule")
        print("4. Free Agents")
        print("5. Stat Leaders")
        print("6. Other Teams")
        if self.game.can_train():
            print("7. Training 🏋️")
        else:
            print("7. Training")
        print("8. Advance Week")
        print("9. Save Game")
        print("0. Exit to Main Menu")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == "1":
            self.view_roster()
        elif choice == "2":
            self.view_standings()
        elif choice == "3":
            self.view_schedule()
        elif choice == "4":
            self.view_free_agents()
        elif choice == "5":
            self.view_stat_leaders()
        elif choice == "6":
            self.view_other_teams()
        elif choice == "7":
            self.view_training()
        elif choice == "8":
            self.advance_week()
        elif choice == "9":
            self.save_game()
        elif choice == "0":
            self.game = None
    
    def view_roster(self):
        """Display team roster."""
        clear_screen()
        print_header(f"{self.game.player_team.name} ROSTER")
        
        roster = self.game.get_team_roster(self.game.player_team_id)
        team = self.game.player_team
        
        print(f"\n{'#':<3} {'Name':<15} {'Age':<4} {'OVR':<4} {'Morale':<8} {'Role':<10} {'Salary':<10}")
        print("-" * 70)
        
        for i, player in enumerate(roster):
            contract = team.contracts.get(player.id)
            salary_str = format_money(contract.salary) if contract else "N/A"
            starter = "*" if i < 3 else " "
            morale_icon = self._get_morale_icon(player.morale)
            
            print(f"{starter}{i+1:<2} {player.name:<15} {player.age:<4} {player.overall:<4} "
                  f"{morale_icon:<8} {player.role:<10} {salary_str:<10}")
        
        print(f"\nTeam Chemistry: {team.chemistry}/100 | Streak: {team.streak:+d}")
        print(f"Monthly Payroll: {format_money(team.monthly_salary)}")
        print(f"Cap Space: {format_money(team.salary_cap_space)}")
        
        print_subheader("ACTIONS")
        print("1. View Player Details")
        print("2. Release Player")
        print("3. Swap Roster Order")
        print("0. Back")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == "1":
            self.view_player_details(roster)
        elif choice == "2":
            self.release_player(roster)
        elif choice == "3":
            self.swap_roster()
    
    def _get_morale_icon(self, morale: int) -> str:
        """Get simple morale icon."""
        if morale >= 85:
            return f"😄{morale}"
        elif morale >= 70:
            return f"🙂{morale}"
        elif morale >= 55:
            return f"😐{morale}"
        elif morale >= 45:
            return f"😕{morale}"
        else:
            return f"😢{morale}"
    
    def view_player_details(self, roster):
        """View detailed player stats."""
        idx = input("Enter player number: ").strip()
        try:
            player = roster[int(idx) - 1]
            
            clear_screen()
            print_header(f"PLAYER: {player.name}")
            
            print(f"\nAge: {player.age} | Nationality: {player.nationality}")
            print(f"Overall: {player.overall} | Role: {player.role}")
            print(f"Market Value: {format_money(player.market_value)}")
            
            # Morale and development
            morale_desc = self._get_morale_indicator(player.morale)
            potential_gap = player.hidden.potential - player.overall
            if potential_gap > 10:
                pot_desc = "High potential for growth"
            elif potential_gap > 5:
                pot_desc = "Room to develop"
            elif potential_gap > 0:
                pot_desc = "Near peak"
            else:
                pot_desc = "At maximum potential"
            
            print(f"\nMorale: {morale_desc}")
            print(f"Development: {pot_desc} (Ambition: {player.hidden.ambition})")
            
            print_subheader("ATTRIBUTES")
            attrs = player.attributes
            
            print(f"\nMechanical Skills:")
            print(f"  Aerial: {attrs.aerial}  Ground: {attrs.ground_control}  Shooting: {attrs.shooting}")
            print(f"  Advanced: {attrs.advanced_mechanics}  Recovery: {attrs.recovery}  Car Control: {attrs.car_control}")
            
            print(f"\nGame Sense:")
            print(f"  Positioning: {attrs.positioning}  Reading: {attrs.game_reading}  Decision: {attrs.decision_making}")
            print(f"  Passing: {attrs.passing}  Boost Mgmt: {attrs.boost_management}")
            
            print(f"\nDefense/Offense:")
            print(f"  Saving: {attrs.saving}  Challenging: {attrs.challenging}")
            print(f"  Finishing: {attrs.finishing}  Creativity: {attrs.creativity}")
            
            print(f"\nMeta:")
            print(f"  Speed: {attrs.speed}  Consistency: {attrs.consistency}  Clutch: {attrs.clutch}")
            print(f"  Mental: {attrs.mental}  Teamwork: {attrs.teamwork}")
            
            print_subheader("SEASON STATS")
            stats = player.season_stats
            print(f"Games: {stats.games_played} | Goals: {stats.goals} | Assists: {stats.assists} | Saves: {stats.saves}")
            if stats.games_played > 0:
                print(f"Per Game: {stats.goals_per_game:.2f} G | {stats.assists_per_game:.2f} A | {stats.saves_per_game:.2f} S")
            
            input("\nPress Enter to continue...")
        except (ValueError, IndexError):
            print("Invalid selection.")
    
    def release_player(self, roster):
        """Release a player from the roster."""
        if len(roster) <= 3:
            print("Cannot release: minimum 3 players required.")
            input("\nPress Enter to continue...")
            return
        
        idx = input("Enter player number to release (0 to cancel): ").strip()
        try:
            if idx == "0":
                return
            player = roster[int(idx) - 1]
            confirm = input(f"Release {player.name}? (y/n): ").strip().lower()
            if confirm == 'y':
                if self.game.release_player(player.id):
                    print(f"✓ {player.name} has been released.")
                else:
                    print("Failed to release player.")
            input("\nPress Enter to continue...")
        except (ValueError, IndexError):
            print("Invalid selection.")
    
    def swap_roster(self):
        """Swap two players in the roster order."""
        print("\nFirst 3 players are starters, 4th is substitute.")
        idx1 = input("First player position (1-4): ").strip()
        idx2 = input("Second player position (1-4): ").strip()
        
        try:
            if self.game.swap_roster_order(int(idx1) - 1, int(idx2) - 1):
                print("✓ Roster order updated.")
            else:
                print("Failed to swap.")
        except ValueError:
            print("Invalid positions.")
        
        input("\nPress Enter to continue...")
    
    def view_standings(self):
        """Display league standings."""
        clear_screen()
        print_header("LEAGUE STANDINGS")
        
        standings = self.game.get_standings()
        
        print(f"\n{'Rank':<5} {'Team':<20} {'Series':<10} {'Games':<12} {'Pts':<5}")
        print("-" * 55)
        
        for s in standings:
            marker = ">>>" if s['is_player_team'] else "   "
            series = f"{s['wins']}-{s['losses']}"
            games = f"{s['game_wins']}-{s['game_losses']}"
            print(f"{marker}{s['rank']:<2} {s['team_abbrev']:<20} {series:<10} {games:<12} {s['points']:<5}")
        
        input("\nPress Enter to continue...")
    
    def view_schedule(self):
        """Display match schedule."""
        clear_screen()
        print_header(f"SCHEDULE - {self.game.current_phase.value.replace('_', ' ').title()}")
        
        schedule = self.game.get_schedule()
        current_week = self.game.current_week
        
        # Group by week
        weeks = {}
        for match in schedule:
            if match['phase'] == self.game.current_phase.value:
                week = match['week']
                if week not in weeks:
                    weeks[week] = []
                weeks[week].append(match)
        
        for week in sorted(weeks.keys()):
            marker = " <-- Current" if week == current_week else ""
            print(f"\n Week {week}{marker}")
            print("-" * 40)
            
            for match in weeks[week]:
                if match['is_played']:
                    result = match['result']
                    status = f"  {result}"
                else:
                    status = "  vs"
                
                marker = "*" if match['involves_player'] else " "
                print(f"{marker} {match['home_team']}{status} {match['away_team']}")
        
        input("\nPress Enter to continue...")
    
    def view_free_agents(self):
        """Display and sign free agents with pagination."""
        page = 0
        per_page = 15
        
        while True:
            clear_screen()
            print_header("FREE AGENTS")
            
            free_agents = self.game.get_free_agents()
            team = self.game.player_team
            total_players = len(free_agents)
            total_pages = (total_players + per_page - 1) // per_page
            
            print(f"\nYour cap space: {format_money(team.salary_cap_space)}/mo")
            print(f"Roster spots: {team.roster_size}/5")
            print(f"Total Free Agents: {total_players}")
            
            # Get current page of players
            start_idx = page * per_page
            end_idx = min(start_idx + per_page, total_players)
            page_players = free_agents[start_idx:end_idx]
            
            print(f"\n--- Page {page + 1}/{max(1, total_pages)} ---\n")
            print(f"{'#':<3} {'Name':<15} {'Age':<4} {'OVR':<4} {'Pot':<5} {'Role':<12} {'Value':<12}")
            print("-" * 65)
            
            for i, player in enumerate(page_players, start_idx + 1):
                # Show potential indicator for young players
                pot_indicator = ""
                if player.age <= 19:
                    pot = player.hidden.potential
                    if pot >= 90:
                        pot_indicator = "★★★"
                    elif pot >= 80:
                        pot_indicator = "★★"
                    elif pot >= 70:
                        pot_indicator = "★"
                    else:
                        pot_indicator = "○"
                elif player.age <= 22:
                    pot_indicator = "?"
                else:
                    pot_indicator = "-"
                
                print(f"{i:<3} {player.name:<15} {player.age:<4} {player.overall:<4} "
                      f"{pot_indicator:<5} {player.role:<12} {format_money(player.market_value):<12}")
            
            print_subheader("OPTIONS")
            
            # Navigation options
            nav_options = []
            if page > 0:
                nav_options.append("[P]rev page")
            if page < total_pages - 1:
                nav_options.append("[N]ext page")
            
            if nav_options:
                print(" | ".join(nav_options))
            
            if team.roster_size < 5:
                print("Enter # to sign a player")
            else:
                print("(Roster full - cannot sign players)")
            print("[0] Back to menu")
            
            choice = input("\nSelect: ").strip().lower()
            
            if choice == "0":
                return
            elif choice == "n" and page < total_pages - 1:
                page += 1
            elif choice == "p" and page > 0:
                page -= 1
            elif choice.isdigit() and team.roster_size < 5:
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < total_players:
                        player = free_agents[idx]
                        self._sign_free_agent(player)
                except (ValueError, IndexError):
                    print("Invalid selection.")
                    input("\nPress Enter to continue...")
    
    def _sign_free_agent(self, player):
        """Handle signing a specific free agent."""
        team = self.game.player_team
        
        print(f"\nSigning {player.name} (Age: {player.age}, OVR: {player.overall})")
        
        # Show potential for young players
        if player.age <= 19:
            pot = player.hidden.potential
            if pot >= 90:
                print("⭐ ELITE POTENTIAL - Could be a superstar!")
            elif pot >= 80:
                print("⭐ High potential prospect")
            elif pot >= 70:
                print("Solid potential")
        
        suggested_salary = player.market_value // 20  # Rough monthly estimate
        
        salary = input(f"Offer monthly salary (suggested ~${suggested_salary:,}): $").strip()
        salary = int(salary) if salary else suggested_salary
        
        length = input("Contract length in months (6-24): ").strip()
        length = int(length) if length else 12
        length = max(6, min(24, length))
        
        if salary > team.salary_cap_space:
            print("Cannot afford this salary!")
        elif self.game.sign_free_agent(player.id, salary, length):
            print(f"\n✓ Signed {player.name} for {format_money(salary)}/mo, {length} months!")
        else:
            print("Failed to sign player.")
        
        input("\nPress Enter to continue...")
    
    def view_other_teams(self):
        """View other teams' rosters and info."""
        clear_screen()
        print_header("LEAGUE TEAMS")
        
        teams = [(tid, t) for tid, t in self.game.teams.items() 
                 if tid != self.game.player_team_id]
        teams.sort(key=lambda x: x[1].elo, reverse=True)
        
        print(f"\n{'#':<3} {'Team':<20} {'Record':<10} {'Elo':<6} {'Chemistry':<10}")
        print("-" * 55)
        
        for i, (tid, team) in enumerate(teams, 1):
            record = team.season_stats.series_record
            print(f"{i:<3} {team.name[:18]:<20} {record:<10} {team.elo:<6} {team.chemistry}/100")
        
        print_subheader("VIEW ROSTER")
        choice = input("Enter team number to view roster (0 to cancel): ").strip()
        
        try:
            if choice == "0":
                return
            idx = int(choice) - 1
            if 0 <= idx < len(teams):
                self.view_team_roster(teams[idx][0])
        except (ValueError, IndexError):
            print("Invalid selection.")
    
    def view_team_roster(self, team_id: str):
        """View a specific team's roster."""
        clear_screen()
        team = self.game.teams.get(team_id)
        if not team:
            return
        
        print_header(f"{team.name} ROSTER")
        
        roster = self.game.get_team_roster(team_id)
        
        # Get AI personality if available
        ai_personality = ""
        if self.game.league_ai:
            team_ai = self.game.league_ai.get_team_ai(team_id)
            if team_ai:
                ai_personality = f" (AI: {team_ai.personality})"
        
        print(f"\nTeam: {team.name}{ai_personality}")
        print(f"Record: {team.season_stats.series_record} | Elo: {team.elo}")
        print(f"Chemistry: {team.chemistry}/100")
        
        print(f"\n{'#':<3} {'Name':<15} {'Age':<4} {'OVR':<4} {'Role':<12} {'Form':<6}")
        print("-" * 50)
        
        for i, player in enumerate(roster):
            starter = "*" if i < 3 else " "
            form_indicator = "↑" if player.form > 60 else "↓" if player.form < 40 else "→"
            print(f"{starter}{i+1:<2} {player.name:<15} {player.age:<4} {player.overall:<4} "
                  f"{player.role:<12} {form_indicator}")
        
        print(f"\nTeam Average OVR: {sum(p.overall for p in roster) / len(roster):.1f}" if roster else "")
        
        input("\nPress Enter to continue...")
    
    def view_stat_leaders(self):
        """Display stat leaders."""
        clear_screen()
        print_header("SEASON STAT LEADERS")
        
        stats = ["goals", "assists", "saves", "goals_per_game", "assists_per_game"]
        
        for stat in stats:
            leaders = self.game.get_stat_leaders(stat, count=5)
            if leaders:
                print(f"\n{stat.replace('_', ' ').title()}:")
                for leader in leaders:
                    print(f"  {leader['rank']}. {leader['player_name']} ({leader['team_abbrev']}): {leader['value']}")
        
        input("\nPress Enter to continue...")
    
    def view_training(self):
        """View and manage training allocation."""
        clear_screen()
        print_header("TRAINING MANAGEMENT")
        
        allocation = self.game.get_training_allocation()
        can_train = self.game.can_train()
        team = self.game.player_team
        
        # Show roster with morale
        roster = self.game.get_team_roster(self.game.player_team_id)
        print("\n📊 ROSTER STATUS:")
        print(f"{'Name':<15} {'OVR':<4} {'Age':<4} {'Morale':<12} {'Potential':<5}")
        print("-" * 50)
        for player in roster[:3]:  # Active roster
            morale_desc = self._get_morale_indicator(player.morale)
            pot_indicator = "★" if player.overall < player.hidden.potential - 5 else "◆" if player.overall < player.hidden.potential else "●"
            print(f"{player.name:<15} {player.overall:<4} {player.age:<4} {morale_desc:<12} {pot_indicator}")
        
        print(f"\nTeam Chemistry: {team.chemistry}/100 | Streak: {team.streak:+d}")
        
        print_subheader("CURRENT TRAINING FOCUS")
        print(f"  Mechanical:  {allocation['mechanical']:>3}%  (Aerial, Shooting, Car Control, Recovery)")
        print(f"  Game Sense:  {allocation['game_sense']:>3}%  (Positioning, Decision Making, Passing)")
        print(f"  Mental:      {allocation['mental']:>3}%  (Consistency, Clutch, Teamwork)")
        
        print_subheader("OPTIONS")
        if can_train:
            print("1. 🏋️ DO TRAINING (available this week)")
        else:
            print("1. ⏳ Training already done this week")
        print("2. Set New Allocation")
        print("3. Quick Presets")
        print("4. Reset to Default (34/33/33)")
        print("0. Back")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == "1" and can_train:
            self.do_training()
        elif choice == "2":
            self.set_training_allocation()
        elif choice == "3":
            self.training_presets()
        elif choice == "4":
            self.game.reset_training_allocation()
            print("\n✓ Training reset to balanced allocation (34% / 33% / 33%)")
            input("\nPress Enter to continue...")
    
    def _get_morale_indicator(self, morale: int) -> str:
        """Get a visual indicator for morale level."""
        if morale >= 85:
            return f"😄 {morale} Ecstatic"
        elif morale >= 70:
            return f"🙂 {morale} Happy"
        elif morale >= 55:
            return f"😐 {morale} Content"
        elif morale >= 45:
            return f"😕 {morale} Unhappy"
        else:
            return f"😢 {morale} Miserable"
    
    def do_training(self):
        """Execute weekly training."""
        print("\n🏋️ Running training session...")
        
        results = self.game.do_training()
        
        if results:
            print("\n✅ Training Results:")
            print("-" * 40)
            
            for player_id, improvements in results.items():
                player = self.game.players.get(player_id)
                if player:
                    attrs = [f"{imp['attribute']} +{imp['change']}" for imp in improvements]
                    print(f"  {player.name}: {', '.join(attrs)}")
            
            total = sum(len(imps) for imps in results.values())
            print(f"\nTotal improvements: {total}")
        else:
            print("\n📊 No improvements this week. Keep training!")
            print("   (Young players with high morale train better)")
        
        input("\nPress Enter to continue...")
    
    def set_training_allocation(self):
        """Set custom training allocation."""
        print("\nEnter percentages for each category (must sum to 100):")
        
        try:
            mech = int(input("  Mechanical %: ").strip() or "0")
            game = int(input("  Game Sense %: ").strip() or "0")
            ment = int(input("  Mental %:     ").strip() or "0")
            
            total = mech + game + ment
            
            if total != 100:
                print(f"\n✗ Total is {total}%, must equal 100%")
            elif any(x < 0 or x > 100 for x in [mech, game, ment]):
                print("\n✗ Each value must be between 0 and 100")
            else:
                if self.game.set_training_allocation(mech, game, ment):
                    print(f"\n✓ Training allocation updated:")
                    print(f"  Mechanical: {mech}% | Game Sense: {game}% | Mental: {ment}%")
                else:
                    print("\n✗ Failed to set allocation")
        except ValueError:
            print("\n✗ Invalid input - enter numbers only")
        
        input("\nPress Enter to continue...")
    
    def training_presets(self):
        """Show training presets."""
        clear_screen()
        print_header("TRAINING PRESETS")
        
        presets = [
            ("1", "Balanced",      34, 33, 33, "Even development across all areas"),
            ("2", "Mechanical",    60, 25, 15, "Focus on mechanics and car control"),
            ("3", "Tactical",      25, 55, 20, "Focus on positioning and game sense"),
            ("4", "Mental",        20, 30, 50, "Focus on consistency and clutch plays"),
            ("5", "Offensive",     50, 35, 15, "Boost shooting and finishing"),
            ("6", "Defensive",     30, 50, 20, "Improve saves and positioning"),
        ]
        
        print(f"\n{'#':<3} {'Preset':<12} {'Mech':<6} {'Game':<6} {'Ment':<6} {'Description'}")
        print("-" * 65)
        
        for num, name, mech, game, ment, desc in presets:
            print(f"{num:<3} {name:<12} {mech:>4}%  {game:>4}%  {ment:>4}%  {desc}")
        
        print("\n0. Back")
        
        choice = input("\nSelect preset: ").strip()
        
        preset_map = {p[0]: (p[2], p[3], p[4]) for p in presets}
        
        if choice in preset_map:
            mech, game, ment = preset_map[choice]
            if self.game.set_training_allocation(mech, game, ment):
                print(f"\n✓ Applied preset: Mechanical {mech}% | Game Sense {game}% | Mental {ment}%")
            else:
                print("\n✗ Failed to apply preset")
            input("\nPress Enter to continue...")
    
    def advance_week(self):
        """Advance the game by one week."""
        clear_screen()
        print_header("ADVANCING WEEK...")
        
        phase_before = self.game.current_phase
        
        results = self.game.advance_week()
        
        if results:
            print(f"\nWeek {self.game.current_week - 1} Results:")
            print("-" * 40)
            
            for result in results:
                home_team = self.game.teams.get(result['home_team_id'])
                away_team = self.game.teams.get(result['away_team_id'])
                
                home_name = home_team.abbreviation if home_team else "???"
                away_name = away_team.abbreviation if away_team else "???"
                
                winner = home_name if result['home_wins'] > result['away_wins'] else away_name
                score = f"{result['home_wins']}-{result['away_wins']}"
                
                # Mark player's match
                is_player_match = (result['home_team_id'] == self.game.player_team_id or
                                  result['away_team_id'] == self.game.player_team_id)
                marker = ">>> " if is_player_match else "    "
                
                print(f"{marker}{home_name} {score} {away_name} (Winner: {winner})")
        
        # Check for phase change
        if self.game.current_phase != phase_before:
            # Format phase name nicely
            phase_name = self.game.current_phase.value.replace('_', ' ').title()
            if 'Split1' in phase_name:
                phase_name = phase_name.replace('Split1 ', 'Split 1 - ')
            elif 'Split2' in phase_name:
                phase_name = phase_name.replace('Split2 ', 'Split 2 - ')
            
            print(f"\n*** Phase Complete! ***")
            print(f"Moving to: {phase_name}")
            
            # Special messages for key phases
            if self.game.current_phase == SeasonPhase.SPLIT_BREAK:
                print("\n🏕️ SPLIT BREAK - Training Camp!")
                print("Teams are undergoing intensive training.")
                print("Chemistry bonuses applied based on roster stability.")
            
            elif self.game.current_phase == SeasonPhase.WORLDS:
                print("\n🏆 WORLD CHAMPIONSHIP!")
                print("The best teams compete for the world title!")
            
            elif self.game.current_phase == SeasonPhase.SEASON_END:
                print("\n=== SEASON COMPLETE ===")
                standings = self.game.get_standings()
                if standings:
                    champion = standings[0]
                    print(f"Champion: {champion['team_name']}")
                
                continue_choice = input("\nStart next season? (y/n): ").strip().lower()
                if continue_choice == 'y':
                    self.game.start_new_season()
                    print(f"\n✓ Season {self.game.season_number} begins!")
        
        # Show recent events (including AI activity and training)
        events = self.game.get_recent_events(10)
        if events:
            print("\nRecent News:")
            for event in events[-8:]:
                # Emoji prefixes for different event types
                if event['type'] in ['ai_signing', 'ai_release']:
                    prefix = "📰"
                elif event['type'] == 'match_result':
                    prefix = "🏆"
                elif event['type'] in ['signing', 'release']:
                    prefix = "✍️"
                elif event['type'] == 'training':
                    prefix = "📈"
                elif event['type'] in ['split_break_chemistry', 'split_break_training']:
                    prefix = "🏕️"
                elif event['type'] in ['phase_start', 'phase_end']:
                    prefix = "📅"
                elif event['type'] in ['progression_up', 'season_progression_up']:
                    prefix = "⬆️"
                elif event['type'] in ['progression_down', 'season_progression_down']:
                    prefix = "⬇️"
                elif event['type'] == 'chemistry_up':
                    prefix = "💚"
                elif event['type'] == 'chemistry_down':
                    prefix = "💔"
                else:
                    prefix = "•"
                print(f"  {prefix} {event['message']}")
        
        # Show training reminder if available
        if self.game.can_train() and self.game.current_phase in REGIONAL_PHASES:
            print("\n💡 TIP: Training available this week! Go to Training menu to train your team.")
        
        input("\nPress Enter to continue...")
    
    def save_game(self):
        """Save the current game."""
        filepath = self.game.save_game()
        print(f"\n✓ Game saved to: {filepath}")
        input("\nPress Enter to continue...")


def main():
    """Entry point."""
    try:
        cli = CLI()
        cli.run()
    except KeyboardInterrupt:
        print("\n\nGame interrupted. Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
