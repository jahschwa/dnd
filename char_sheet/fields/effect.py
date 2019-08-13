from collections import OrderedDict

from dnd.char_sheet.fields import Field
from dnd.duration import Duration

###############################################################################
# Effect class
#   - links a Duration to one or more bonuses
#   - the same Bonus object can be used by multiple Effects
#   - turning an Effect on/off intelligently turns on/off its Bonuses
###############################################################################

class Effect(Field):

  FIELDS = OrderedDict([
      ('name',str),
      ('bonuses',list),
      ('duration',Duration),
      ('text',str),
  ])

  # @param name (str)
  # @param bonuses (str,list of str) bonuses conferred by this Effect
  # @param duration (Duration) [None] defaults to infinite
  # @param text (str) [None]
  # @param active (bool) whether this Effect is active (toggles our bonuses)
  # @rasie TypeError on duration
  def __init__(self,name,bonuses,duration=None,text=None,active=True):

    self.name = name
    self.bonuses = bonuses if isinstance(bonuses,list) else [bonuses]
    self.duration = duration or Duration()
    self.text = text or ''

    self.last = self.duration.copy()
    self.char = None

    if not isinstance(self.duration,Duration):
      raise TypeError('duration must be Duration not "%s"'
          % self.duration.__class__.__name__)

  def _plug(self):

    for name in self.bonuses:
      self.char.bonuses[name].effects.add(self.name)

    self.calc(force=True)

  # @raise RuntimeError if plug() wasn't called first
  def _unplug(self):

    for name in self.bonuses:
      bonus = self.char.bonuses[name]
      bonus.effects.remove(self.name)
      bonus.off()

  # update our bonuses
  # @param force (bool) if False, only update if it looks like we changed
  def calc(self,force=False):

    if force or self.duration!=self.last:
      for name in self.bonuses:
        bonus = self.char.bonuses[name]
        if not bonus.condition:
          bonus.toggle(self.is_active())

  # advance our duration
  # @param dur (Duration,int,str) [1] the duration to advance forward
  # @return (bool) if we're expired after the advance
  def advance(self,dur=1):

    last = self.duration.copy()
    self.duration.advance(Duration(dur))
    self.last = last
    self.calc()
    return not self.is_active()

  # @return (bool) if our duration hasn't expired
  def is_active(self):
    return not self.duration.is_expired()

  # @return (bool) if we're permanent
  def is_permanent(self):
    return self.duration.rounds==Duration.INF

  # make our duration infinite (i.e. activate this effect)
  def make_permanent(self):

    self.last = self.duration.copy()
    self.duration = Duration()
    self.calc()

  # expire our duration
  def expire(self):

    self.last = self.duration.copy()
    self.duration.expire()
    self.calc()

  # return to our original duration
  def reset(self):
    self.last = self.duration.copy()
    self.duration.reset()
    self.calc()

  def revert(self):

    if self.duration==self.last:
      return
    (self.duration,self.last) = (self.last,self.duration)
    self.calc()

  # looks like: {+} NAME DURATION BONUSES
  # can also start with {-} or {?}
  # @return (str)
  def __str__(self):

    actives = [self.char.bonuses[b].active for b in self.bonuses]
    if all(actives):
      act = '+'
    elif any(actives):
      act = '?'
    else:
      act = '-'
    return '{%s} %s %s (%s)' % (act,self.name,self.duration,
        ','.join(self.bonuses))

  # @return (str)
  def str_all(self):

    l =      ['duration | %s' % self.duration]
    l.append( 'original | %s' % Duration(self.duration.original))
    if not self.duration.elapsed().is_expired():
      l.append( ' elapsed | %s' % self.duration.elapsed())
    bonuses = [self.char.bonuses[b] for b in self.bonuses]
    l.extend(['   bonus | %s' % b for b in bonuses])
    l.append( '  active | %s (%s/%s)' % (
        self.is_active(),
        len([b for b in bonuses if b.active]),
        len(bonuses)
    ))
    l.append( '    text | '+self.text)
    return '\n'.join(l)
