import functools
import jinja2
import mafia
import os

def render_email(template, **kwargs):
  env = jinja2.Environment(loader=jinja2.PackageLoader("godfather", "emails"),
                           trim_blocks=True, lstrip_blocks=True)
  template = env.get_template(template)
  return template.render(**kwargs).strip()

@functools.singledispatch
def event_email(event, *, parser):
  return event.message

@event_email.register(mafia.events.RoleAnnouncement)
def _(event, *, parser):
  player = event.to[0]
  abilities = player.role.descriptions
  commands = parser.get_help(player)
  objective = player.role.objective
  return render_email(
    "role_announcement.html",
    initial=(event.phase == mafia.START),
    role=event.role,
    abilities=abilities,
    commands=commands,
    objective=objective,
  )

def render_death_email(event, *, description):
  return render_email(
    "died.html",
    description=description,
    player=event.player,
    role=event.player.role,
    will=event.player.will,
  )

@event_email.register(mafia.events.Died)
def _(event, *, parser):
  return render_death_email(event, description="has died")

@event_email.register(mafia.events.Lynched)
def _(event, *, parser):
  return render_death_email(event, description="was lynched")
