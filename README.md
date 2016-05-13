# Godfather

A program for running games of [Mafia](http://wiki.mafiascum.net/).


## Installing

```sh
sudo easy_install3 godfather
```


## Usage

```sh
# Create the game directory and a template setup.py.
godfather init ~/mafia-game

# Edit setup.py to configure your game.
nano ~/mafia-game/setup.py

# Run the game. Game state is saved in game.pickle.
godfather run ~/mafia-game

# View the game log so far.
godfather log ~/mafia-game
```


## Contributing

Install dependencies:
```sh
sudo easy_install3 install callee click mafia nose
```

Set up presubmit hooks:
```sh
scripts/install-git-hooks
```

Run tests:
```sh
nosetests
```


## TODO

- Add phase end emails
- Add get_emails unit tests
- Add send_emails unit tests
- Add full-game integration test
- Intercept interrupts
