from setuptools import *

setup(
  # Metadata
  name="godfather",
  version="0.1",
  author="Calder Coalson",
  author_email="caldercoalson@gmail.com",
  url="https://github.com/calder/godfather",
  description="A CLI for running games of Mafia.",
  long_description="See https://github.com/calder/godfather for documentation.",

  # Contents
  packages=find_packages(exclude=["*.test"]),
  entry_points = {
    "console_scripts": ["godfather=godfather.main:main"],
  },

  # Dependencies
  install_requires=[
    "click",
    "mafia",
    "pluginbase",
    "pytz",
    "requests",
    "termcolor",
  ],
  setup_requires=[
    "nose",
  ],
  tests_require=[
    "nose-parameterized",
  ],

  # Settings
  test_suite="nose.collector",
  zip_safe=True,
)
