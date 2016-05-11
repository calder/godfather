# Godfather

A program for running games of [Mafia](http://wiki.mafiascum.net/).


## Installing

```sh
sudo easy_install3 godfather
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
