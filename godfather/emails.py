import functools
import jinja2
import mafia
import os

def render_email(template, **kwargs):
  template_path = os.path.join(os.path.dirname(__file__), "emails", template)
  return jinja2.Template(open(template_path).read()).render(**kwargs)

@functools.singledispatch
def event_email(event):
  return event.message

@event_email.register(mafia.events.RoleAnnouncement)
def _(event):
  return render_email(
    "role_announcement.html",
    initial=(event.phase == mafia.START),
    role=event.role,
  )
