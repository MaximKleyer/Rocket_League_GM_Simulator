# Rocket League GM Simulator

A single-player esports management simulation game where you take control of a Rocket League team and guide them through competitive seasons in the RLCS.

## Features

### Core Gameplay
- **Roster Management** - Sign free agents, release players, manage your 3-player active roster + substitute
- **Contract System** - Negotiate salaries, contract lengths, and manage your budget
- **Season Simulation** - Play through regional splits with round-robin scheduling
- **Match Engine** - Weighted RNG simulation based on player attributes

### Player System
- **20 Attribute System** tailored to Rocket League:
  - Mechanical Skills: Aerial, Ground Control, Shooting, Advanced Mechanics, Recovery, Car Control
  - Game Sense: Positioning, Game Reading, Decision Making, Passing, Boost Management
  - Defense/Offense: Saving, Challenging, Finishing, Creativity
  - Meta: Speed, Consistency, Clutch, Mental, Teamwork

- **Player Development** - Young players improve, veterans decline
- **Hidden Attributes** - Potential, Ambition, Adaptability affect long-term growth

### Team Management
- **Team Chemistry** - Builds over time with stable rosters, drops with changes
- **Finances** - Balance budget with salary obligations, sponsorships, and prize money
- **Elo Rating** - Teams have competitive ratings that update after matches

### Statistics
- Full stat tracking: Goals, Assists, Saves, Shots, Demos
- Per-game averages
- Season and career statistics
- League stat leaders

## Project Structure

```
rl_manager/
├── core/                    # Game engine (no UI dependencies)
│   ├── models/
│   │   ├── player.py       # Player class with attributes
│   │   └── team.py         # Team, Contract, Finances
│   ├── simulation/
│   │   ├── match_engine.py # Weighted RNG match simulation
│   │   └── season.py       # League, Season management
│   ├── data/
│   │   └── generator.py    # Fictional player/team generation
│   └── game.py             # Main Game orchestrator, save/load
├── ui/                      # UI layer (future)
├── saves/                   # Save file directory
└── main.py                 # CLI interface
```

## Installation

```bash
# Clone/download the project
cd rl_manager

# No external dependencies required! Uses only Python standard library.
python main.py
```

## How to Play

1. **Start a new game** - Name your team and join the RLCS NA league
2. **Manage your roster** - View your players, their attributes and contracts
3. **Sign free agents** - Browse available players and offer contracts
4. **Advance through the season** - Simulate week by week, watch results come in
5. **Track standings** - See how your team ranks against the competition
6. **Save and continue** - Your progress is saved to JSON files

## Match Simulation Details

The match engine uses weighted RNG based on player attributes:

1. **Scoring Chances** - Generated based on team offensive vs defensive ratings
2. **Conversion Probability** - Calculated from attacker's Finishing/Shooting vs defender's Saving
3. **Consistency Variance** - High consistency = reliable performance, low = unpredictable
4. **Clutch Factor** - Affects performance in overtime and elimination scenarios
5. **Team Chemistry** - Stable rosters perform better together

## Future Development

### Phase 1 (Current) ✓
- Core game loop
- Player and team models
- Match simulation
- Basic CLI interface
- Save/Load system

### Phase 2 (Planned)
- AI team management (trades, signings)
- Transfer market with AI negotiations
- Player morale system
- Training and practice scheduling

### Phase 3 (Planned)
- Full RLCS format (Regionals → Major → Worlds)
- Multiple regions
- Draft/youth pipeline
- Scouting with imperfect information

### Phase 4 (Planned)
- PySide6 desktop GUI
- Rich data tables and visualizations
- Match replays with play-by-play

## Architecture Notes

The game follows strict separation between engine and UI:

- **Core package** has zero UI imports - can be tested headlessly
- **Game class** provides all game actions as methods
- **Save format** uses JSON for easy debugging and modding
- **Event system** logs all game events for news feeds

This architecture enables:
- Automated balance testing (simulate 1000 seasons)
- Swappable UIs (CLI → GUI → Web)
- Clean save/load without pickle security issues
- Future mod support via external JSON data

## Credits

Inspired by Football Manager, Out of the Park Baseball, and Basketball GM.

Built as a portfolio project demonstrating:
- Object-oriented Python design
- Statistical simulation
- Game state management
- Domain-driven architecture

## License

MIT License - Feel free to use, modify, and learn from this code!
