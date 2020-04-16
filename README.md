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
# Create the game directory and a template setup.py.
godfather init ~/mafia-game

# Edit setup.py to configure your game.
nano ~/mafia-game/setup.py

# Run the game. Game state is saved in game.pickle.
godfather run ~/mafia-game
```

Other commands:
```sh
# View the game log so far.
godfather log ~/mafia-game

# Resolve the current phase immediately.
godfather poke ~/mafia-game

# Restore the game state from a backup.
godfather restore ~/mafia-game --backup ~/mafia-game/backups/my_backup.pickle
```


## Contributing

Install dependencies:
```sh
sudo pip3 install --upgrade callee click flask jinja2 mafia pluginbase pytest pytz requests termcolor
```

Set up presubmit hooks:
```sh
scripts/install-git-hooks
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
