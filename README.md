# Godfather

A program for running games of [Mafia](http://wiki.mafiascum.net/).


## Installing

```sh
sudo easy_install3 godfather
```


## Usage

```sh
godfather init ~/mafia-game
nano ~/mafia-game/setup.py  # Edit to your heart's content
godfather run ~/mafia-game
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
