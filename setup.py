from setuptools import *

setup(
  # Metadata
  name="godfather",
  version="0.6",
  author="Calder Coalson",
  author_email="caldercoalson@gmail.com",
  url="https://github.com/calder/godfather",
  description="A CLI for running games of Mafia.",
  long_description="See https://github.com/calder/godfather for documentation.",

  # Contents
  packages=find_packages(exclude=["*.test"]),
  package_data={"godfather": [
    "emails/*",
    "static/*",
    "templates/*",
  ]},
  entry_points = {
    "console_scripts": ["godfather=godfather.main:main"],
  },

  # Dependencies
  install_requires=[
    "click",
    "flask",
    "jinja2",
    "mafia",
    "pluginbase",
    "pytz",
    "requests",
    "termcolor",
  ],
  tests_require=[
    "pytest",
  ],

  # Settings
  zip_safe=False,
)
