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
from core.simulation.season import SeasonPhase


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
        
        print_header(f"{team.name} ({team.abbreviation})")
        print(f"Season {self.game.season_number} | {self.game.current_phase.value.replace('_', ' ').title()} | Week {self.game.current_week}")
        print(f"Record: {team.season_stats.series_record} | Elo: {team.elo}")
        print(f"Balance: {format_money(team.finances.balance)} | Salary: {format_money(team.monthly_salary)}/mo")
        
        print_subheader("MENU")
        print("1. View Roster")
        print("2. View Standings")
        print("3. View Schedule")
        print("4. Free Agents")
        print("5. Stat Leaders")
        print("6. Other Teams")
        print("7. Advance Week")
        print("8. Save Game")
        print("9. Exit to Main Menu")
        
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
            self.advance_week()
        elif choice == "8":
            self.save_game()
        elif choice == "9":
            self.game = None
    
    def view_roster(self):
        """Display team roster."""
        clear_screen()
        print_header(f"{self.game.player_team.name} ROSTER")
        
        roster = self.game.get_team_roster(self.game.player_team_id)
        team = self.game.player_team
        
        print(f"\n{'#':<3} {'Name':<15} {'Age':<4} {'OVR':<4} {'Role':<12} {'Salary':<10} {'Contract':<8}")
        print("-" * 70)
        
        for i, player in enumerate(roster):
            contract = team.contracts.get(player.id)
            salary_str = format_money(contract.salary) if contract else "N/A"
            length_str = f"{contract.length}mo" if contract else "N/A"
            starter = "*" if i < 3 else " "
            
            print(f"{starter}{i+1:<2} {player.name:<15} {player.age:<4} {player.overall:<4} "
                  f"{player.role:<12} {salary_str:<10} {length_str:<8}")
        
        print(f"\nTeam Chemistry: {team.chemistry}/100")
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
        """Display and sign free agents."""
        clear_screen()
        print_header("FREE AGENTS")
        
        free_agents = self.game.get_free_agents()
        team = self.game.player_team
        
        print(f"\nYour cap space: {format_money(team.salary_cap_space)}/mo")
        print(f"Roster spots: {team.roster_size}/5\n")
        
        print(f"{'#':<3} {'Name':<15} {'Age':<4} {'OVR':<4} {'Role':<12} {'Value':<12}")
        print("-" * 55)
        
        for i, player in enumerate(free_agents[:15], 1):
            print(f"{i:<3} {player.name:<15} {player.age:<4} {player.overall:<4} "
                  f"{player.role:<12} {format_money(player.market_value):<12}")
        
        if team.roster_size >= 5:
            print("\n(Roster full - cannot sign players)")
            input("\nPress Enter to continue...")
            return
        
        print_subheader("SIGN PLAYER")
        idx = input("Enter player number to sign (0 to cancel): ").strip()
        
        try:
            if idx == "0":
                return
            player = free_agents[int(idx) - 1]
            
            print(f"\nSigning {player.name} (OVR: {player.overall})")
            suggested_salary = player.market_value // 20  # Rough monthly estimate
            
            salary = input(f"Offer monthly salary (suggested ~${suggested_salary}): $").strip()
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
        except (ValueError, IndexError):
            print("Invalid selection.")
    
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
            print(f"\n*** Phase Complete! ***")
            print(f"Moving to: {self.game.current_phase.value.replace('_', ' ').title()}")
            
            if self.game.current_phase == SeasonPhase.SEASON_END:
                print("\n=== SEASON COMPLETE ===")
                standings = self.game.get_standings()
                if standings:
                    champion = standings[0]
                    print(f"Champion: {champion['team_name']}")
                
                continue_choice = input("\nStart next season? (y/n): ").strip().lower()
                if continue_choice == 'y':
                    self.game.start_new_season()
                    print(f"\n✓ Season {self.game.season_number} begins!")
        
        # Show recent events (including AI activity)
        events = self.game.get_recent_events(10)
        if events:
            print("\nRecent News:")
            for event in events[-8:]:
                # Color-code different event types
                if event['type'] in ['ai_signing', 'ai_release']:
                    prefix = "📰"
                elif event['type'] == 'match_result':
                    prefix = "🏆"
                elif event['type'] in ['signing', 'release']:
                    prefix = "✍️"
                else:
                    prefix = "•"
                print(f"  {prefix} {event['message']}")
        
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