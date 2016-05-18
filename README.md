# Godfather

A program for running games of [Mafia](http://wiki.mafiascum.net/).


## Installing

1. Install Godfather:
```sh
sudo easy_install3 godfather
```

2. Set up [Mailgun](https://www.mailgun.com).

3. Install your Mailgun API key:
```sh
echo MAILGUN_API_KEY > ~/.config/godfather/mailgun_key.txt
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

- Add full-game integration test
- Add public and private CC lists
- Add action cancelling
- Add wills
