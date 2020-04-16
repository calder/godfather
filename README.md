# 🐴 Godfather

A tool for running games of [Mafia](http://wiki.mafiascum.net) over email. Uses the [`mafia`](https://github.com/calder/) package as its resolver.


## Installing

Install Godfather:
```sh
sudo apt-get install python3-pip
sudo pip3 install --upgrade godfather
```

Set up [Mailgun](https://www.mailgun.com), then install your Mailgun API key:
```sh
mkdir -p ~/.config/godfather
echo MAILGUN_API_KEY > ~/.config/godfather/mailgun_key.txt
```


## Usage

Normal usage:
```sh
# Create game directory.
mkdir my_game
cd my_game

# Create a template setup.py.
godfather init

# Edit setup.py to configure your game.
nano setup.py

# Run the game. Game state is saved in game.pickle.
godfather run
```

Other commands:
```sh
# View the game log so far.
godfather log

# Resolve the current phase immediately.
godfather resolve

# Restore the game state from a backup.
godfather restore --backup ~/mafia-game/backups/my_backup.pickle
```


## Contributing

Install dependencies:
```sh
sudo pip3 install --upgrade callee click flask jinja2 mafia pluginbase pytest pytz requests termcolor
```

Install pre-commit hooks:
```sh
scripts/install_git_hooks.sh
```

Run tests:
```sh
# Run all unit tests.
pytest

# Run Mailgun integration tests.
pytest -m mailgun
```


## TODO

- Add full-game integration test
- Add mail push
